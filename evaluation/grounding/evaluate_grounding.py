"""Evaluation runner for Phase 5 Answer Claim Grounding & Citation Verification.

Computes all 13 required research metrics:
1. Claim Support Precision
2. Claim Support Recall
3. Claim Support F1
4. Unsupported Claim Detection Rate
5. Contradiction Detection Rate
6. Citation Accuracy
7. Citation Completeness
8. Citation Entailment Accuracy
9. Grounding Score
10. High-Risk Claim Error Rate
11. Abstention / Qualification Appropriateness
12. False Unsupported Rate
13. Verification Latency

Also computes 95% Bootstrap Confidence Intervals (B=2000, seed=42).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
RAG_SERVICE_DIR = REPO_ROOT / "rag-service"
if str(RAG_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_SERVICE_DIR))

from evaluation.statistics.bootstrap_ci import compute_bootstrap_ci
from research.claim_grounding.engine import ClaimGroundingEngine
from research.claim_grounding.models import (
    CitationStatus,
    ClaimStatus,
    RiskLevel,
)


def evaluate_grounding_benchmark(
    benchmark_path: str = "evaluation/grounding/grounding_questions.json",
    ablation_mode: str = "full",
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run evaluation across benchmark and compute all 13 metrics and bootstrap CIs."""
    bench_p = Path(benchmark_path)
    if not bench_p.exists():
        raise FileNotFoundError(f"Benchmark file not found: {bench_p}")

    with open(bench_p, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])
    if not test_cases:
        raise ValueError("No test cases found in benchmark JSON.")

    engine = ClaimGroundingEngine(config_path=config_path)

    # Metric collection containers
    latencies: List[float] = []
    grounding_scores: List[float] = []
    support_precisions: List[float] = []
    support_recalls: List[float] = []
    support_f1s: List[float] = []

    # Counts
    total_annotated_claims = 0
    pred_supported_count = 0
    gt_supported_count = 0
    true_positive_supported = 0

    gt_unsupported_total = 0
    detected_unsupported = 0

    gt_contradiction_total = 0
    detected_contradictions = 0

    total_citations_evaluated = 0
    valid_citations_count = 0

    citation_entailment_evaluable = 0
    citation_entailment_correct = 0

    high_risk_claims_total = 0
    high_risk_errors_count = 0

    qual_needed_total = 0
    qual_correctly_applied = 0

    false_unsupported_count = 0
    gt_valid_claims_total = 0

    per_case_audit: List[Dict[str, Any]] = []

    for case in test_cases:
        c_id = case["case_id"]
        answer_text = case["generated_answer"]
        evidence = case.get("retrieved_evidence", [])
        ann_claims = case.get("annotated_claims", [])

        # Execute Engine Verification
        res = engine.verify_and_qualify_answer(
            answer=answer_text,
            evidence_chunks=evidence,
            ablation_mode=ablation_mode,
        )

        latencies.append(res.latency_ms)
        grounding_scores.append(res.grounding_score)

        # Align evaluated claims with ground-truth annotated claims
        case_tp_supp = 0
        case_pred_supp = 0
        case_gt_supp = 0

        # Map by nearest text match or sequential
        for idx, ann in enumerate(ann_claims):
            total_annotated_claims += 1
            gt_status = ann["expected_support_status"]
            gt_cit_status = ann["expected_citation_status"]

            # Find matching decision
            if idx < len(res.decisions):
                dec = res.decisions[idx]
                pred_status = dec.status.value
            else:
                pred_status = ClaimStatus.UNSUPPORTED.value

            if gt_status == ClaimStatus.SUPPORTED.value:
                gt_supported_count += 1
                case_gt_supp += 1
                gt_valid_claims_total += 1
                if pred_status == ClaimStatus.SUPPORTED.value:
                    true_positive_supported += 1
                    case_tp_supp += 1
                elif pred_status in [ClaimStatus.UNSUPPORTED.value, ClaimStatus.CONTRADICTED.value]:
                    false_unsupported_count += 1

            if pred_status == ClaimStatus.SUPPORTED.value:
                pred_supported_count += 1
                case_pred_supp += 1

            # Unsupported claim detection
            if gt_status in [ClaimStatus.UNSUPPORTED.value, ClaimStatus.INSUFFICIENT_EVIDENCE.value]:
                gt_unsupported_total += 1
                if pred_status in [ClaimStatus.UNSUPPORTED.value, ClaimStatus.INSUFFICIENT_EVIDENCE.value]:
                    detected_unsupported += 1

            # Contradiction detection
            if gt_status == ClaimStatus.CONTRADICTED.value:
                gt_contradiction_total += 1
                if pred_status == ClaimStatus.CONTRADICTED.value:
                    detected_contradictions += 1

            # High-risk claim error rate
            is_high_risk = (ann.get("expected_claim_type") in ["PUNISHMENT", "STATUTORY_PROVISION", "PROCEDURAL_REQUIREMENT", "TEMPORAL_CLAIM"])
            if is_high_risk:
                high_risk_claims_total += 1
                # If ground truth was unsupported/contradicted, but system marked supported -> error
                if gt_status in [ClaimStatus.UNSUPPORTED.value, ClaimStatus.CONTRADICTED.value]:
                    if pred_status == ClaimStatus.SUPPORTED.value:
                        high_risk_errors_count += 1

            # Qualification appropriateness
            needs_qualification = (gt_status in [ClaimStatus.UNSUPPORTED.value, ClaimStatus.PARTIALLY_SUPPORTED.value, ClaimStatus.CONTRADICTED.value])
            if needs_qualification:
                qual_needed_total += 1
                if res.modifications_made:
                    qual_correctly_applied += 1

            # Citation verification metrics
            for cit_res in (dec.citation_results if idx < len(res.decisions) else []):
                total_citations_evaluated += 1
                if cit_res.status.value == gt_cit_status:
                    citation_entailment_correct += 1
                citation_entailment_evaluable += 1
                if cit_res.status == CitationStatus.VALID_CITATION:
                    valid_citations_count += 1

        # Per-case Precision / Recall
        p = case_tp_supp / case_pred_supp if case_pred_supp > 0 else 1.0
        r = case_tp_supp / case_gt_supp if case_gt_supp > 0 else 1.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        support_precisions.append(p)
        support_recalls.append(r)
        support_f1s.append(f1)

        per_case_audit.append({
            "case_id": c_id,
            "category": case.get("category"),
            "grounding_score": res.grounding_score,
            "modifications_made": res.modifications_made,
            "latency_ms": res.latency_ms,
            "claims_count": len(res.claims),
            "unsupported_count": res.unsupported_claim_count,
            "contradicted_count": res.contradicted_claim_count,
        })

    # Metric Computations
    macro_precision = sum(support_precisions) / max(1, len(support_precisions))
    macro_recall = sum(support_recalls) / max(1, len(support_recalls))
    macro_f1 = sum(support_f1s) / max(1, len(support_f1s))

    unsupported_detection_rate = detected_unsupported / max(1, gt_unsupported_total)
    contradiction_detection_rate = detected_contradictions / max(1, gt_contradiction_total)

    cit_accuracy = valid_citations_count / max(1, total_citations_evaluated)
    cit_completeness = (
        sum(1 for c in per_case_audit if c["unsupported_count"] == 0) / max(1, len(per_case_audit))
    )
    cit_entailment_acc = citation_entailment_correct / max(1, citation_entailment_evaluable)

    avg_grounding_score = sum(grounding_scores) / max(1, len(grounding_scores))
    high_risk_error_rate = high_risk_errors_count / max(1, high_risk_claims_total)
    qual_appropriateness = qual_correctly_applied / max(1, qual_needed_total)
    false_unsupported_rate = false_unsupported_count / max(1, gt_valid_claims_total)
    avg_latency = sum(latencies) / max(1, len(latencies))

    # Bootstrap Confidence Intervals (B=2000, seed=42)
    ci_grounding_score = compute_bootstrap_ci(grounding_scores, metric_name="grounding_score", num_bootstraps=2000, random_seed=42)
    ci_support_precision = compute_bootstrap_ci(support_precisions, metric_name="claim_support_precision", num_bootstraps=2000, random_seed=42)
    ci_support_recall = compute_bootstrap_ci(support_recalls, metric_name="claim_support_recall", num_bootstraps=2000, random_seed=42)
    ci_support_f1 = compute_bootstrap_ci(support_f1s, metric_name="claim_support_f1", num_bootstraps=2000, random_seed=42)

    metrics = {
        "claim_support_precision": round(macro_precision, 4),
        "claim_support_recall": round(macro_recall, 4),
        "claim_support_f1": round(macro_f1, 4),
        "unsupported_claim_detection_rate": round(unsupported_detection_rate, 4),
        "contradiction_detection_rate": round(contradiction_detection_rate, 4),
        "citation_accuracy": round(cit_accuracy, 4),
        "citation_completeness": round(cit_completeness, 4),
        "citation_entailment_accuracy": round(cit_entailment_acc, 4),
        "grounding_score": round(avg_grounding_score, 4),
        "high_risk_claim_error_rate": round(high_risk_error_rate, 4),
        "qualification_appropriateness": round(qual_appropriateness, 4),
        "false_unsupported_rate": round(false_unsupported_rate, 4),
        "average_verification_latency_ms": round(avg_latency, 4),
    }

    return {
        "benchmark_file": benchmark_path,
        "total_cases": len(test_cases),
        "ablation_mode": ablation_mode,
        "metrics": metrics,
        "bootstrap_confidence_intervals": {
            "grounding_score": ci_grounding_score.to_dict(),
            "claim_support_precision": ci_support_precision.to_dict(),
            "claim_support_recall": ci_support_recall.to_dict(),
            "claim_support_f1": ci_support_f1.to_dict(),
        },
        "per_case_audit": per_case_audit,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate answer claim grounding benchmark.")
    parser.add_argument(
        "--benchmark",
        type=str,
        default="evaluation/grounding/grounding_questions.json",
        help="Path to grounding questions JSON",
    )
    parser.add_argument(
        "--ablation",
        type=str,
        default="full",
        choices=["citation_presence", "citation_verification", "claim_evidence", "full"],
        help="Ablation mode",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/grounding_evaluation_metrics.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results = evaluate_grounding_benchmark(
        benchmark_path=args.benchmark,
        ablation_mode=args.ablation,
    )

    print(json.dumps(results["metrics"], indent=2))

    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved results to {out_p}")


if __name__ == "__main__":
    main()
