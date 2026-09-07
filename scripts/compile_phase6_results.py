"""Phase 6 Results Compilation and Cross-Table Verification Script.

Reads results/phase6_summary.json, results/phase6_summary.csv, and results/phase6_statistical_tests.json,
verifying formatting consistency and printing summary tables.
"""

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"


def compile_and_verify_results():
    sum_json = RESULTS_DIR / "phase6_summary.json"
    sum_csv = RESULTS_DIR / "phase6_summary.csv"
    stat_json = RESULTS_DIR / "phase6_statistical_tests.json"
    rob_json = RESULTS_DIR / "phase6_robustness.json"
    abl_csv = RESULTS_DIR / "phase6_ablation_results.csv"

    for p in [sum_json, sum_csv, stat_json, rob_json, abl_csv]:
        if not p.exists():
            print(f"[MISSING] Required result file not found: {p}")
            return False

    with open(sum_json, "r", encoding="utf-8") as f:
        master = json.load(f)

    print("Phase 6 Master Summary Verification:")
    print(f"  Timestamp UTC: {master.get('timestamp_utc')}")
    print(f"  Test Queries : {master.get('total_test_queries')}")
    print(f"  Configs Run  : {len(master.get('configurations_evaluated', []))}")

    # Display Ablation CSV
    print("\n--- Ablation Results (CSV) ---")
    with open(abl_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            print("  " + " | ".join(f"{col:<25}" for col in row))

    # Display Statistical Significance
    with open(stat_json, "r", encoding="utf-8") as f:
        stats = json.load(f)

    print("\n--- Primary Statistical Hypothesis Tests (Wilcoxon Signed-Rank + Holm-Bonferroni) ---")
    for metric_name, comparisons in stats.items():
        print(f"\nMetric: {metric_name.upper()}")
        for c in comparisons:
            b_sys = c.get("baseline_system", "")
            e_sys = c.get("experimental_system", "")
            diff = c.get("difference", 0.0)
            p_val = c.get("wilcoxon_test", {}).get("p_value", 1.0)
            p_adj = c.get("adjusted_p_value_holm", 1.0)
            cohen = c.get("cohen_d", 0.0)
            cdelta = c.get("cliffs_delta", 0.0)
            concl = c.get("conclusion", "")
            print(f"  {b_sys:<24} -> {e_sys:<24}: Diff = {diff:+.4f} | p = {p_val:.4f} (Holm adj: {p_adj:.4f}) | Cohen d = {cohen:+.4f} | Cliff delta = {cdelta:+.4f} | {concl}")

    return True


if __name__ == "__main__":
    compile_and_verify_results()
