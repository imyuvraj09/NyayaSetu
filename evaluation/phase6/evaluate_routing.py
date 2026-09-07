"""Legal Regime Routing Evaluation Module for NyayaSetu Phase 6.

Evaluates Fact-First Legal Issue Routing (Phase 3):
- Regime Classification Accuracy
- Macro Precision, Macro Recall, Macro F1
- Multi-class Confusion Matrix
- Confidence distribution and Fallback Rate
- Routing Latency Profile (Mean, Median, P95, P99, StdDev)
- 95% Bootstrap Confidence Intervals (B=10,000)
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.phase6.statistical_tests import compute_bootstrap_ci_10k
from research.issue_router import FactFirstRouter, get_fact_first_router


def evaluate_routing_split(
    benchmark_file: Path,
    router: Optional[FactFirstRouter] = None,
) -> Dict[str, Any]:
    """Run legal regime routing evaluation across benchmark partition."""
    if router is None:
        router = get_fact_first_router()

    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    if not queries:
        return {"error": "No queries found"}

    latencies: List[float] = []
    correct_regime_hits: List[float] = []
    confidences: List[float] = []
    fallback_flags: List[float] = []

    # Confusion matrix structures
    # We track canonical regimes: BNS_SUBSTANTIVE, BNSS_PROCEDURAL, BSA_EVIDENCE, IT_ACT, CONSTITUTION, CONSUMER_PROTECTION, MOTOR_VEHICLES, POSH_LABOUR, POCSO_CHILD, GENERAL
    regimes = [
        "BNS_SUBSTANTIVE", "BNSS_PROCEDURAL", "BSA_EVIDENCE", "IT_ACT",
        "CONSTITUTION", "CONSUMER_PROTECTION", "MOTOR_VEHICLES",
        "POSH_LABOUR", "POCSO_CHILD", "GENERAL"
    ]
    confusion_matrix: Dict[str, Dict[str, int]] = {r: {c: 0 for c in regimes} for r in regimes}

    # Per-class TP, FP, FN
    tp_map: Dict[str, int] = defaultdict(int)
    fp_map: Dict[str, int] = defaultdict(int)
    fn_map: Dict[str, int] = defaultdict(int)

    per_query_audit: List[Dict[str, Any]] = []

    for q in queries:
        qid = q["id"]
        qtext = q["question"]
        gold_regimes = q.get("legal_regimes_expected", ["GENERAL"])
        primary_gold = gold_regimes[0] if gold_regimes else "GENERAL"

        t0 = time.perf_counter()
        decision = router.route_query(qtext)
        lat = time.perf_counter() - t0
        latencies.append(lat)

        selected = decision.selected_regimes
        predicted_primary = selected[0] if selected else "GENERAL"
        conf = decision.confidence
        fallback_used = decision.fallback_used

        confidences.append(conf)
        fallback_flags.append(1.0 if fallback_used else 0.0)

        # Accuracy evaluation: is primary gold in selected regimes?
        is_hit = 1.0 if any(g in selected for g in gold_regimes) else 0.0
        correct_regime_hits.append(is_hit)

        # Update confusion matrix
        pred_key = predicted_primary if predicted_primary in regimes else "GENERAL"
        gold_key = primary_gold if primary_gold in regimes else "GENERAL"
        confusion_matrix[gold_key][pred_key] += 1

        # Class statistics for Macro metrics
        if pred_key == gold_key:
            tp_map[gold_key] += 1
        else:
            fp_map[pred_key] += 1
            fn_map[gold_key] += 1

        per_query_audit.append({
            "id": qid,
            "question": qtext,
            "gold_regimes": gold_regimes,
            "predicted_regimes": selected,
            "is_correct": bool(is_hit > 0),
            "confidence": round(conf, 4),
            "fallback_used": fallback_used,
            "routing_mode": decision.routing_mode.value,
            "latency_sec": round(lat, 6),
        })

    # Macro Precision, Recall, F1
    precisions = []
    recalls = []
    f1s = []

    for r in regimes:
        tp = tp_map[r]
        fp = fp_map[r]
        fn = fn_map[r]

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * p * rec) / (p + rec) if (p + rec) > 0 else 0.0

        precisions.append(p)
        recalls.append(rec)
        f1s.append(f1)

    macro_p = float(np.mean(precisions))
    macro_r = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    # Bootstrap CIs for accuracy and confidence
    acc_ci = compute_bootstrap_ci_10k(correct_regime_hits, "regime_accuracy").to_dict()
    conf_ci = compute_bootstrap_ci_10k(confidences, "routing_confidence").to_dict()

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
        "regime_accuracy": round(float(np.mean(correct_regime_hits)), 4),
        "regime_accuracy_ci": acc_ci,
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "mean_confidence": round(float(np.mean(confidences)), 4),
        "fallback_rate": round(float(np.mean(fallback_flags)), 4),
        "confusion_matrix": confusion_matrix,
        "latency_profile": latency_profile,
        "per_query_audit": per_query_audit,
        "raw_vectors": {
            "correct_regime_hits": correct_regime_hits,
            "confidences": confidences,
            "fallback_flags": fallback_flags,
        },
    }
