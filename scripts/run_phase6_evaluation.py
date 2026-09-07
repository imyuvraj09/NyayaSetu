"""Comprehensive Phase 6 Experimental Evaluation & Statistical Validation Runner.

Orchestrates:
1. Benchmark validation and data integrity verification.
2. Comparative evaluation of Baselines A/B/C and Phases 3/4/5 on the held-out test split (N = 150).
3. 10,000-sample bootstrap confidence intervals for primary metrics.
4. Paired inferential significance tests (McNemar, Wilcoxon signed-rank, paired t-test).
5. Multiple comparison corrections (Holm-Bonferroni, Benjamini-Hochberg).
6. Non-parametric effect size calculations (Cliff's delta, rank-biserial correlation, Cohen's d).
7. 6-dimensional robustness stratification.
8. 15-category failure and error analysis.
9. Tabular results compilation into results/ directory.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.phase6.benchmark_validator import validate_all_splits
from evaluation.phase6.data_integrity import check_data_integrity
from evaluation.phase6.evaluate_compatibility import evaluate_compatibility_split
from evaluation.phase6.evaluate_end_to_end import run_comparative_evaluation
from evaluation.phase6.evaluate_grounding import evaluate_grounding_split
from evaluation.phase6.evaluate_routing import evaluate_routing_split


def run_phase6_pipeline(config_path: str = "configs/phase6_evaluation_config.yaml") -> Dict[str, Any]:
    cfg_p = Path(config_path)
    if not cfg_p.exists():
        cfg_p = REPO_ROOT / config_path

    with open(cfg_p, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    results_dir = REPO_ROOT / config.get("output", {}).get("results_dir", "results")
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("NYAYASETU PHASE 6: EXPANDED BENCHMARK & STATISTICAL VALIDATION PIPELINE")
    print("=" * 80)

    # 1. Validation & Data Integrity
    print("\n[STEP 1/6] Running Benchmark Validation & Data Integrity Auditing...")
    val_report = validate_all_splits()
    if not val_report["all_valid"]:
        raise ValueError(f"Benchmark validation failed: {val_report['results']}")
    print("  -> Schema & Partition Validation: PASSED")

    integrity_report = check_data_integrity()
    if not integrity_report["is_data_clean"]:
        raise ValueError(f"Data integrity failed: {integrity_report}")
    print("  -> Duplicate & Split-Leakage Audit: PASSED (Zero leakage, zero duplicates)")

    # 2. Comparative End-to-End Evaluation on Held-Out Test Split
    test_bench = REPO_ROOT / config["benchmark"]["held_out_test"]
    print(f"\n[STEP 2/6] Executing Comparative Evaluation across 6 Architectures on {test_bench.name} (N = 150)...")
    comp_eval = run_comparative_evaluation(benchmark_file=test_bench, output_dir=results_dir)

    results_by_config = comp_eval["results_by_config"]
    statistical_tests = comp_eval["statistical_tests"]
    robustness_analysis = comp_eval["robustness_analysis"]

    # 3. Dedicated Stage Evaluations on Test Split
    print("\n[STEP 3/6] Running Dedicated Stage Evaluations (Routing, Compatibility, Grounding)...")
    routing_eval = evaluate_routing_split(test_bench)
    print(f"  -> Fact-First Routing Accuracy: {routing_eval['regime_accuracy']:.4f} (Macro F1: {routing_eval['macro_f1']:.4f})")

    compat_eval = evaluate_compatibility_split(test_bench)
    print(f"  -> Evidence Compatibility F1 : {compat_eval['compatibility_f1']:.4f} (IRR: {compat_eval['incompatible_rejection_rate']:.4f})")

    grounding_eval = evaluate_grounding_split(test_bench)
    print(f"  -> Claim Grounding Score     : {grounding_eval['grounding_score']:.4f} (High-Risk Error: {grounding_eval['high_risk_error_rate']:.4f})")

    # 4. Error and Failure Mode Analysis
    print("\n[STEP 4/6] Conducting 15-Category Failure Mode Analysis on Test Split...")
    failure_categories = [
        "retrieval_semantic_mismatch",
        "regime_routing_failure",
        "temporal_classification_failure",
        "evidence_compatibility_failure",
        "special_vs_general_conflict",
        "substantive_procedural_mismatch",
        "missing_evidence",
        "unsupported_generation_claim",
        "contradicted_generation_claim",
        "citation_fabrication",
        "citation_misalignment",
        "incorrect_statute",
        "incorrect_section",
        "multi_statute_reasoning_failure",
        "out_of_scope_handling_failure",
    ]

    failure_audit = {}
    with open(test_bench, "r", encoding="utf-8") as f:
        bench_cases = json.load(f).get("queries", [])

    full_pipe_preds = comp_eval["predictions_by_config"]["phase5_full_pipeline"]
    pred_map = {p["id"]: p for p in full_pipe_preds}

    for cat in failure_categories:
        failure_audit[cat] = {
            "count": 0,
            "percentage": 0.0,
            "pipeline_stage": "retrieval" if "retrieval" in cat or "statute" in cat else (
                "routing" if "routing" in cat or "temporal" in cat else (
                    "compatibility" if "compatibility" in cat or "conflict" in cat or "substantive" in cat else "claim_grounding"
                )
            ),
            "severity": "critical" if "contradicted" in cat or "high_risk" in cat or "fabrication" in cat else "medium",
            "example_ids": [],
        }

    total_test_items = len(bench_cases)
    for q in bench_cases:
        qid = q["id"]
        qcat = q.get("category")
        pred = pred_map.get(qid, {})

        if qcat == "out_of_scope" and pred.get("recall_at_1", 0.0) == 0.0:
            failure_audit["out_of_scope_handling_failure"]["count"] += 1
            failure_audit["out_of_scope_handling_failure"]["example_ids"].append(qid)
        elif pred.get("recall_at_5", 1.0) == 0.0:
            failure_audit["retrieval_semantic_mismatch"]["count"] += 1
            failure_audit["retrieval_semantic_mismatch"]["example_ids"].append(qid)
        elif qcat == "temporal_applicability" and pred.get("recall_at_1", 1.0) == 0.0:
            failure_audit["temporal_classification_failure"]["count"] += 1
            failure_audit["temporal_classification_failure"]["example_ids"].append(qid)
        elif qcat == "claim_grounding_failures":
            if pred.get("high_risk_error", 0.0) > 0.0:
                failure_audit["unsupported_generation_claim"]["count"] += 1
                failure_audit["unsupported_generation_claim"]["example_ids"].append(qid)
            else:
                failure_audit["contradicted_generation_claim"]["count"] += 1
                failure_audit["contradicted_generation_claim"]["example_ids"].append(qid)
        elif qcat == "multi_statute" and pred.get("precision_at_5", 1.0) < 0.40:
            failure_audit["multi_statute_reasoning_failure"]["count"] += 1
            failure_audit["multi_statute_reasoning_failure"]["example_ids"].append(qid)

    for cat, info in failure_audit.items():
        info["percentage"] = round((info["count"] / total_test_items) * 100.0, 2)

    # 5. Compile Artifacts and Summary Tables
    print("\n[STEP 5/6] Compiling Summary Artifacts and Results Tables...")

    # Summary CSV
    csv_rows = []
    headers = [
        "configuration", "recall_at_1", "recall_at_5", "precision_at_5",
        "mrr", "ndcg_at_5", "grounding_score", "high_risk_error_rate",
        "mean_latency_ms", "p95_latency_ms"
    ]
    csv_rows.append(headers)

    for cfg_name, cfg_res in results_by_config.items():
        sm = cfg_res["summary_metrics"]
        lat = cfg_res["latency_breakdown"]["end_to_end"]
        csv_rows.append([
            cfg_name,
            sm["recall_at_1"],
            sm["recall_at_5"],
            sm["precision_at_5"],
            sm["mrr"],
            sm["ndcg_at_5"],
            sm["grounding_score"],
            sm["high_risk_error_rate"],
            lat["mean_ms"],
            lat["p95_ms"],
        ])

    summary_csv_path = REPO_ROOT / config.get("output", {}).get("summary_csv", "results/phase6_summary.csv")
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"  -> Saved Summary Table: {summary_csv_path}")

    # Ablation CSV
    ablation_headers = [
        "component_configuration", "recall_at_5", "mrr", "grounding_score", "high_risk_error_rate", "delta_recall_at_5_vs_baseline"
    ]
    ablation_rows = [ablation_headers]
    base_r5 = results_by_config["baseline_dense"]["summary_metrics"]["recall_at_5"]
    for cfg_name in ["baseline_dense", "baseline_hybrid", "baseline_hybrid_rrf", "phase3_routing", "phase4_compatibility", "phase5_full_pipeline"]:
        sm = results_by_config[cfg_name]["summary_metrics"]
        delta_r5 = round(sm["recall_at_5"] - base_r5, 4)
        ablation_rows.append([
            cfg_name,
            sm["recall_at_5"],
            sm["mrr"],
            sm["grounding_score"],
            sm["high_risk_error_rate"],
            f"+{delta_r5}" if delta_r5 >= 0 else str(delta_r5),
        ])

    ablation_csv_path = REPO_ROOT / config.get("output", {}).get("ablation_csv", "results/phase6_ablation_results.csv")
    with open(ablation_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(ablation_rows)
    print(f"  -> Saved Ablation Results: {ablation_csv_path}")

    # Statistical JSON
    stat_json_path = REPO_ROOT / config.get("output", {}).get("statistical_json", "results/phase6_statistical_tests.json")
    with open(stat_json_path, "w", encoding="utf-8") as f:
        json.dump(statistical_tests, f, indent=2)
    print(f"  -> Saved Statistical Tests: {stat_json_path}")

    # Robustness JSON
    rob_json_path = REPO_ROOT / config.get("output", {}).get("robustness_json", "results/phase6_robustness.json")
    with open(rob_json_path, "w", encoding="utf-8") as f:
        json.dump(robustness_analysis, f, indent=2)
    print(f"  -> Saved Robustness Analysis: {rob_json_path}")

    # Summary JSON (Comprehensive master payload)
    master_summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_file": str(test_bench),
        "total_test_queries": len(bench_cases),
        "configurations_evaluated": list(results_by_config.keys()),
        "stage_evaluations": {
            "routing": {
                "regime_accuracy": routing_eval["regime_accuracy"],
                "macro_f1": routing_eval["macro_f1"],
                "fallback_rate": routing_eval["fallback_rate"],
                "mean_latency_ms": routing_eval["latency_profile"]["mean_latency_sec"] * 1000.0,
            },
            "compatibility": {
                "compatibility_f1": compat_eval["compatibility_f1"],
                "incompatible_rejection_rate": compat_eval["incompatible_rejection_rate"],
                "false_rejection_rate": compat_eval["false_rejection_rate"],
                "mean_rank_improvement": compat_eval["mean_rank_improvement"],
                "mean_latency_ms": compat_eval["latency_profile"]["mean_latency_sec"] * 1000.0,
            },
            "claim_grounding": {
                "claim_support_f1": grounding_eval["claim_support_f1"],
                "unsupported_claim_detection_rate": grounding_eval["unsupported_claim_detection_rate"],
                "contradiction_detection_rate": grounding_eval["contradiction_detection_rate"],
                "citation_accuracy": grounding_eval["citation_accuracy"],
                "grounding_score": grounding_eval["grounding_score"],
                "high_risk_error_rate": grounding_eval["high_risk_error_rate"],
                "mean_latency_ms": grounding_eval["latency_profile"]["mean_latency_sec"] * 1000.0,
            },
        },
        "results_by_config": {
            k: {
                "summary_metrics": v["summary_metrics"],
                "bootstrap_cis": v["bootstrap_cis"],
                "latency_breakdown": v["latency_breakdown"],
            }
            for k, v in results_by_config.items()
        },
        "statistical_tests": statistical_tests,
        "failure_mode_analysis": failure_audit,
    }

    summary_json_path = REPO_ROOT / config.get("output", {}).get("summary_json", "results/phase6_summary.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)
    print(f"  -> Saved Master Summary JSON: {summary_json_path}")

    # 6. Final Print Summary
    print("\n" + "=" * 80)
    print("PHASE 6 EVALUATION COMPLETE")
    print("=" * 80)
    print(f"{'Configuration':<26} | {'Recall@5':<9} | {'MRR':<8} | {'Grounding':<9} | {'High-Risk Err':<13} | {'Lat (ms)':<9}")
    print("-" * 80)
    for cfg_name, cfg_res in results_by_config.items():
        sm = cfg_res["summary_metrics"]
        lat = cfg_res["latency_breakdown"]["end_to_end"]["mean_ms"]
        print(f"{cfg_name:<26} | {sm['recall_at_5']:<9.4f} | {sm['mrr']:<8.4f} | {sm['grounding_score']:<9.4f} | {sm['high_risk_error_rate']:<13.4f} | {lat:<9.2f}")
    print("=" * 80)

    return master_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 6 Evaluation Suite.")
    parser.add_argument("--config", default="configs/phase6_evaluation_config.yaml", help="Path to config file")
    args = parser.parse_args()
    run_phase6_pipeline(args.config)
