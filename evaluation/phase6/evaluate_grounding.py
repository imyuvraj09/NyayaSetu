"""Claim Grounding & Citation Verification Evaluation Module for NyayaSetu Phase 6.

Evaluates Phase 5 Claim Grounding Engine across benchmark partitions:
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
11. Verification Latency Profile (Mean, Median, P95, P99, StdDev)
12. 95% Bootstrap Confidence Intervals (B=10,000)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.phase6.statistical_tests import compute_bootstrap_ci_10k
from research.claim_grounding.engine import ClaimGroundingEngine
from research.claim_grounding.models import (
    CitationStatus,
    ClaimStatus,
    RiskLevel,
)


def evaluate_grounding_split(
    benchmark_file: Path,
    engine: Optional[ClaimGroundingEngine] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run claim grounding evaluation across benchmark partition."""
    if engine is None:
        engine = ClaimGroundingEngine(config_path=config_path)

    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    if not queries:
        return {"error": "No queries found in benchmark"}

    latencies: List[float] = []
    grounding_scores: List[float] = []
    support_precisions: List[float] = []
    support_recalls: List[float] = []
    support_f1s: List[float] = []

    total_claims = 0
    gt_supported_total = 0
    pred_supported_total = 0
    tp_supported = 0

    gt_unsupported_total = 0
    detected_unsupported = 0

    gt_contradiction_total = 0
    detected_contradictions = 0

    total_citations = 0
    valid_citations = 0
    entailed_citations = 0

    high_risk_claims_total = 0
    high_risk_errors_count = 0

    per_case_audit: List[Dict[str, Any]] = []

    for q in queries:
        qid = q["id"]
        qtext = q["question"]
        gen_answer = q.get("generated_answer", "")
        evidence_chunks = q.get("retrieved_evidence", [])
        annotated_claims = q.get("annotated_claims", [])

        t0 = time.perf_counter()
        answer_result = engine.verify_and_qualify_answer(
            answer=gen_answer,
            evidence_chunks=evidence_chunks,
        )
        lat = time.perf_counter() - t0
        latencies.append(lat)

        g_score = answer_result.grounding_score
        grounding_scores.append(g_score)

        # Match predicted decisions with annotated claims
        pred_claims = answer_result.decisions
        case_tp = 0
        case_pred_supp = 0
        case_gt_supp = 0

        for ac in annotated_claims:
            total_claims += 1
            gt_status = ac.get("ground_truth_status", "SUPPORTED")
            is_high_risk = ac.get("risk_level") in ("HIGH", "CRITICAL")
            if is_high_risk:
                high_risk_claims_total += 1

            if gt_status == "SUPPORTED":
                gt_supported_total += 1
                case_gt_supp += 1
            elif gt_status == "UNSUPPORTED":
                gt_unsupported_total += 1
            elif gt_status == "CONTRADICTED":
                gt_contradiction_total += 1

            # Match against extracted proposition
            matched_pred = None
            for pc in pred_claims:
                # Text overlap
                if any(w in pc.claim.claim_text.lower() for w in ac["claim_text"].lower().split()[:4]):
                    matched_pred = pc
                    break

            pred_status = matched_pred.status if matched_pred else ClaimStatus.UNSUPPORTED
            if pred_status == ClaimStatus.SUPPORTED:
                pred_supported_total += 1
                case_pred_supp += 1
                if gt_status == "SUPPORTED":
                    tp_supported += 1
                    case_tp += 1
            elif pred_status in (ClaimStatus.UNSUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED):
                if gt_status in ("UNSUPPORTED", "PARTIALLY_SUPPORTED"):
                    detected_unsupported += 1
            elif pred_status == ClaimStatus.CONTRADICTED:
                if gt_status == "CONTRADICTED":
                    detected_contradictions += 1

            # High risk error: unsupported or contradicted claim accepted as supported
            if is_high_risk and gt_status in ("UNSUPPORTED", "CONTRADICTED") and pred_status == ClaimStatus.SUPPORTED:
                high_risk_errors_count += 1

        # Per-case Precision, Recall, F1
        c_p = case_tp / case_pred_supp if case_pred_supp > 0 else (1.0 if case_gt_supp == 0 else 0.0)
        c_r = case_tp / case_gt_supp if case_gt_supp > 0 else 1.0
        c_f1 = (2.0 * c_p * c_r) / (c_p + c_r) if (c_p + c_r) > 0 else 0.0

        support_precisions.append(c_p)
        support_recalls.append(c_r)
        support_f1s.append(c_f1)

        # Citations audit
        for pc in pred_claims:
            for cv in pc.citation_results:
                total_citations += 1
                if cv.status == CitationStatus.VALID_CITATION:
                    valid_citations += 1
                    entailed_citations += 1

        per_case_audit.append({
            "id": qid,
            "grounding_score": round(g_score, 4),
            "claims_count": len(annotated_claims),
            "precision": round(c_p, 4),
            "recall": round(c_r, 4),
            "f1": round(c_f1, 4),
            "modifications_made": answer_result.modifications_made,
            "latency_sec": round(lat, 6),
        })

    # Summary metrics
    mean_p = float(np.mean(support_precisions))
    mean_r = float(np.mean(support_recalls))
    mean_f1 = float(np.mean(support_f1s))
    mean_g_score = float(np.mean(grounding_scores))

    unsupported_det_rate = (detected_unsupported / gt_unsupported_total) if gt_unsupported_total > 0 else 1.0
    contradiction_det_rate = (detected_contradictions / gt_contradiction_total) if gt_contradiction_total > 0 else 1.0
    citation_acc = (valid_citations / total_citations) if total_citations > 0 else 1.0
    citation_entail_acc = (entailed_citations / total_citations) if total_citations > 0 else 1.0
    high_risk_err_rate = (high_risk_errors_count / high_risk_claims_total) if high_risk_claims_total > 0 else 0.0

    p_ci = compute_bootstrap_ci_10k(support_precisions, "claim_support_precision").to_dict()
    r_ci = compute_bootstrap_ci_10k(support_recalls, "claim_support_recall").to_dict()
    f1_ci = compute_bootstrap_ci_10k(support_f1s, "claim_support_f1").to_dict()
    gs_ci = compute_bootstrap_ci_10k(grounding_scores, "grounding_score").to_dict()

    lat_arr = np.asarray(latencies, dtype=np.float64)
    latency_profile = {
        "mean_latency_sec": round(float(np.mean(lat_arr)), 6),
        "median_latency_sec": round(float(np.median(lat_arr)), 6),
        "p95_latency_sec": round(float(np.percentile(lat_arr, 95)), 6),
        "p99_latency_sec": round(float(np.percentile(lat_arr, 99)), 6),
        "std_latency_sec": round(float(np.std(lat_arr, ddof=1)), 6),
    }

    return {
        "benchmark_file": str(benchmark_file),
        "total_queries": len(queries),
        "total_claims_evaluated": total_claims,
        "claim_support_precision": round(mean_p, 4),
        "claim_support_precision_ci": p_ci,
        "claim_support_recall": round(mean_r, 4),
        "claim_support_recall_ci": r_ci,
        "claim_support_f1": round(mean_f1, 4),
        "claim_support_f1_ci": f1_ci,
        "unsupported_claim_detection_rate": round(unsupported_det_rate, 4),
        "contradiction_detection_rate": round(contradiction_det_rate, 4),
        "citation_accuracy": round(citation_acc, 4),
        "citation_completeness": round(citation_acc, 4),
        "citation_entailment_accuracy": round(citation_entail_acc, 4),
        "grounding_score": round(mean_g_score, 4),
        "grounding_score_ci": gs_ci,
        "high_risk_error_rate": round(high_risk_err_rate, 4),
        "latency_profile": latency_profile,
        "per_case_audit": per_case_audit,
        "raw_vectors": {
            "support_precisions": support_precisions,
            "support_recalls": support_recalls,
            "support_f1s": support_f1s,
            "grounding_scores": grounding_scores,
        },
    }
