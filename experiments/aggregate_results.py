"""Aggregate and synthesize baseline experiment results into structured comparative tables.

Reads results from `results/experiments/` directories, generates:
- results/baseline_comparison.csv
- results/baseline_comparison.json
- Markdown summary table for documentation.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def aggregate_experiments(
    experiments_dir: str = "results/experiments",
    output_csv: str = "results/baseline_comparison.csv",
    output_json: str = "results/baseline_comparison.json",
) -> List[Dict[str, Any]]:
    exp_path = Path(experiments_dir)
    if not exp_path.exists():
        print(f"Directory not found: {experiments_dir}")
        return []

    # Find all manifest.json files
    manifests = sorted(list(exp_path.glob("*/manifest.json")))
    if not manifests:
        print(f"No experiment manifests found under {experiments_dir}")
        return []

    # Map to latest run per experiment_id
    latest_by_exp: Dict[str, Dict[str, Any]] = {}
    for mf in manifests:
        try:
            with open(mf, "r", encoding="utf-8") as f:
                data = json.load(f)
            exp_id = data.get("experiment_id", "")
            # Later folders have newer timestamp
            latest_by_exp[exp_id] = data
        except Exception:
            continue

    rows: List[Dict[str, Any]] = []
    fieldnames = [
        "Configuration",
        "Number of Questions",
        "Hit@1",
        "Hit@3",
        "Hit@5",
        "Precision@5",
        "Recall@5",
        "MRR",
        "nDCG@5",
        "Average Retrieval Latency (s)",
        "Average Total Latency (s)",
    ]

    for exp_id, m in latest_by_exp.items():
        summary = m.get("summary_metrics", {})
        row = {
            "Configuration": exp_id,
            "Number of Questions": m.get("queries_evaluated_count", summary.get("total_queries", 0)),
            "Hit@1": summary.get("document_hit_at_1", 0.0),
            "Hit@3": summary.get("document_hit_at_3", 0.0),
            "Hit@5": summary.get("document_hit_at_5", 0.0),
            "Precision@5": summary.get("average_precision_at_5", 0.0),
            "Recall@5": summary.get("average_recall_at_5", 0.0),
            "MRR": summary.get("mean_reciprocal_rank", 0.0),
            "nDCG@5": summary.get("mean_ndcg_at_5", 0.0),
            "Average Retrieval Latency (s)": summary.get("average_retrieval_latency_sec", 0.0),
            "Average Total Latency (s)": summary.get("average_total_latency_sec", 0.0),
        }
        rows.append(row)

    # Sort in baseline order: direct_llm -> dense_rag -> hybrid_rag -> reranked_rag
    order = {"baseline_direct_llm": 1, "baseline_dense_rag": 2, "baseline_hybrid_rag": 3, "baseline_reranked_rag": 4}
    rows.sort(key=lambda r: order.get(r["Configuration"], 99))

    # Save CSV
    out_csv_path = Path(output_csv)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Save JSON
    out_json_path = Path(output_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    # Print markdown table
    print("\n" + "=" * 80)
    print("NYAYASETU BASELINE EXPERIMENT COMPARISON TABLE")
    print("=" * 80)
    print(f"| {'Configuration':<24} | {'N':<3} | {'Hit@1':<6} | {'Hit@5':<6} | {'Prec@5':<6} | {'Recall@5':<8} | {'MRR':<6} | {'nDCG@5':<6} | {'Retr. Lat.':<10} |")
    print("|" + "-" * 26 + "|" + "-" * 5 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 12 + "|")
    for r in rows:
        print(f"| {r['Configuration']:<24} | {r['Number of Questions']:<3} | {r['Hit@1']:<6.4f} | {r['Hit@5']:<6.4f} | {r['Precision@5']:<6.4f} | {r['Recall@5']:<8.4f} | {r['MRR']:<6.4f} | {r['nDCG@5']:<6.4f} | {r['Average Retrieval Latency (s)']:<10.4f} |")
    print("=" * 80 + "\n")

    return rows


def main():
    parser = argparse.ArgumentParser(description="Aggregate NyayaSetu baseline results into CSV and JSON.")
    parser.add_argument("--experiments_dir", default="results/experiments")
    parser.add_argument("--output_csv", default="results/baseline_comparison.csv")
    parser.add_argument("--output_json", default="results/baseline_comparison.json")
    args = parser.parse_args()

    aggregate_experiments(
        experiments_dir=args.experiments_dir,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
