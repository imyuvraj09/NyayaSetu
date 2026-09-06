"""Routing evaluation runner computing comprehensive legal regime routing metrics.

Metrics implemented:
1. Top-1 Regime Accuracy
2. Top-3 Regime Coverage
3. Macro Precision
4. Macro Recall
5. Macro F1
6. Per-Regime Metrics (Precision, Recall, F1, Support)
7. Confusion Matrix
8. Multi-label Regime Recall
9. Fallback Rate
10. Incorrect High-Confidence Routing Rate (Critical safety metric)
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.issue_router import FactFirstRouter, get_fact_first_router
from research.schemas import RoutingMode


def evaluate_routing_dataset(
    dataset_path: str,
    router: Optional[FactFirstRouter] = None,
) -> Dict[str, Any]:
    """Execute routing evaluation across a benchmark dataset and compute all 10 metrics."""
    data_file = Path(dataset_path)
    if not data_file.exists():
        raise FileNotFoundError(f"Routing benchmark dataset not found: {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("routing_queries", [])
    if not queries:
        return {"error": "No routing queries found in dataset"}

    if router is None:
        router = get_fact_first_router()

    total_queries = len(queries)
    top1_correct = 0
    top3_covered = 0
    fallback_count = 0
    high_conf_total = 0
    high_conf_incorrect = 0

    multilabel_recall_sum = 0.0
    multilabel_evaluable = 0

    all_regimes: Set[str] = set()
    per_regime_tp: Dict[str, int] = defaultdict(int)
    per_regime_fp: Dict[str, int] = defaultdict(int)
    per_regime_fn: Dict[str, int] = defaultdict(int)
    per_regime_support: Dict[str, int] = defaultdict(int)

    confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_query_results: List[Dict[str, Any]] = []

    for q in queries:
        qid = q["query_id"]
        qtext = q["question"]
        gold_primary = q["gold_primary_regime"]
        gold_candidates = q.get("gold_candidate_regimes", [gold_primary] if gold_primary else [])

        all_regimes.add(gold_primary)

        # Route query
        decision = router.route_query(qtext)
        predicted_regimes = decision.selected_regimes
        predicted_primary = predicted_regimes[0] if predicted_regimes else "GENERAL"
        top3_predicted = predicted_regimes[:3]

        all_regimes.add(predicted_primary)
        confusion_matrix[gold_primary][predicted_primary] += 1
        per_regime_support[gold_primary] += 1

        # Metric 1: Top-1 Accuracy
        is_top1_correct = (predicted_primary == gold_primary) or (predicted_primary in gold_candidates)
        if is_top1_correct:
            top1_correct += 1

        # Metric 2: Top-3 Coverage
        is_top3_covered = any(r in gold_candidates or r == gold_primary for r in top3_predicted)
        if is_top3_covered:
            top3_covered += 1

        # Metric 9: Fallback Rate
        if decision.fallback_used or decision.routing_mode in (RoutingMode.LOW_CONFIDENCE_FALLBACK, RoutingMode.AMBIGUOUS_FALLBACK):
            fallback_count += 1

        # Metric 10: Incorrect High-Confidence Routing Rate
        if decision.routing_mode == RoutingMode.HIGH_CONFIDENCE:
            high_conf_total += 1
            # Check if any selected regime matches gold
            if not any(r in gold_candidates or r == gold_primary for r in decision.selected_regimes):
                high_conf_incorrect += 1

        # Metric 8: Multi-label Recall
        if gold_candidates:
            multilabel_evaluable += 1
            hits = sum(1 for g in gold_candidates if g in predicted_regimes)
            multilabel_recall_sum += hits / len(gold_candidates)

        # Precision / Recall per regime
        for r in all_regimes:
            pred_r = r in predicted_regimes
            gold_r = r == gold_primary or r in gold_candidates
            if pred_r and gold_r:
                per_regime_tp[r] += 1
            elif pred_r and not gold_r:
                per_regime_fp[r] += 1
            elif not pred_r and gold_r:
                per_regime_fn[r] += 1

        per_query_results.append({
            "query_id": qid,
            "question": qtext,
            "gold_primary": gold_primary,
            "gold_candidates": gold_candidates,
            "predicted_primary": predicted_primary,
            "predicted_regimes": predicted_regimes,
            "confidence": decision.confidence,
            "routing_mode": decision.routing_mode.value,
            "fallback_used": decision.fallback_used,
            "top1_correct": is_top1_correct,
            "top3_covered": is_top3_covered,
        })

    # Summary Calculations
    top1_accuracy = top1_correct / total_queries if total_queries else 0.0
    top3_coverage = top3_covered / total_queries if total_queries else 0.0
    fallback_rate = fallback_count / total_queries if total_queries else 0.0
    incorrect_high_conf_rate = (high_conf_incorrect / high_conf_total) if high_conf_total else 0.0
    multilabel_recall = (multilabel_recall_sum / multilabel_evaluable) if multilabel_evaluable else 0.0

    # Per-regime and Macro Metrics
    per_regime_stats = {}
    macro_p_list, macro_r_list, macro_f1_list = [], [], []

    for reg in sorted(list(all_regimes)):
        tp = per_regime_tp[reg]
        fp = per_regime_fp[reg]
        fn = per_regime_fn[reg]
        supp = per_regime_support[reg]

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        per_regime_stats[reg] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": supp,
        }
        if supp > 0:
            macro_p_list.append(prec)
            macro_r_list.append(rec)
            macro_f1_list.append(f1)

    macro_precision = sum(macro_p_list) / len(macro_p_list) if macro_p_list else 0.0
    macro_recall = sum(macro_r_list) / len(macro_r_list) if macro_r_list else 0.0
    macro_f1 = sum(macro_f1_list) / len(macro_f1_list) if macro_f1_list else 0.0

    metrics = {
        "dataset_evaluated": str(data_file),
        "total_queries": total_queries,
        "top1_regime_accuracy": round(top1_accuracy, 4),
        "top3_regime_coverage": round(top3_coverage, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "multilabel_regime_recall": round(multilabel_recall, 4),
        "fallback_rate": round(fallback_rate, 4),
        "high_confidence_total_count": high_conf_total,
        "high_confidence_incorrect_count": high_conf_incorrect,
        "incorrect_high_confidence_routing_rate": round(incorrect_high_conf_rate, 4),
        "per_regime_metrics": per_regime_stats,
        "confusion_matrix": {k: dict(v) for k, v in confusion_matrix.items()},
        "per_query_results": per_query_results,
    }

    return metrics


def format_routing_report(metrics: Dict[str, Any]) -> str:
    """Format evaluation metrics into readable text report."""
    lines = [
        "=" * 85,
        "FACT-FIRST LEGAL ISSUE ROUTING EVALUATION REPORT",
        "=" * 85,
        f"Dataset Evaluated                     : {metrics['dataset_evaluated']}",
        f"Total Queries Evaluated               : {metrics['total_queries']}",
        "-" * 85,
        f"Top-1 Regime Accuracy                 : {metrics['top1_regime_accuracy'] * 100:.2f}%",
        f"Top-3 Regime Coverage                 : {metrics['top3_regime_coverage'] * 100:.2f}%",
        f"Macro Precision                       : {metrics['macro_precision']:.4f}",
        f"Macro Recall                          : {metrics['macro_recall']:.4f}",
        f"Macro F1                              : {metrics['macro_f1']:.4f}",
        f"Multi-Label Regime Recall             : {metrics['multilabel_regime_recall']:.4f}",
        f"Fallback Rate                         : {metrics['fallback_rate'] * 100:.2f}%",
        "-" * 85,
        "SAFETY & HIGH-CONFIDENCE METRIC:",
        f"High-Confidence Decisions Total       : {metrics['high_confidence_total_count']}",
        f"High-Confidence Incorrect Decisions   : {metrics['high_confidence_incorrect_count']}",
        f"Incorrect High-Confidence Routing Rate: {metrics['incorrect_high_confidence_routing_rate'] * 100:.2f}% (Target: < 5.0%)",
        "-" * 85,
        "PER-REGIME BREAKDOWN:",
        f"{'Regime':<24} | {'Prec':<7} | {'Recall':<7} | {'F1':<7} | {'Support':<7}",
        "-" * 85,
    ]
    for reg, s in metrics["per_regime_metrics"].items():
        if s["support"] > 0:
            lines.append(f"{reg:<24} | {s['precision']:<7.4f} | {s['recall']:<7.4f} | {s['f1']:<7.4f} | {s['support']:<7}")
    lines.append("=" * 85)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Fact-First Legal Issue Routing against gold benchmark.")
    parser.add_argument("--dataset", default="evaluation/routing/routing_questions_template.json", help="Path to routing benchmark JSON")
    parser.add_argument("--output_json", default="results/routing_evaluation_metrics.json", help="Output JSON metrics path")
    args = parser.parse_args()

    metrics = evaluate_routing_dataset(args.dataset)
    print(format_routing_report(metrics))

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"\nWrote structured routing metrics to {out_p}")


if __name__ == "__main__":
    main()
