"""Non-parametric bootstrap confidence interval estimation for NyayaSetu retrieval evaluation.

Computes percentile bootstrap confidence intervals (e.g. 95% CI) across per-query
retrieval and generation metrics. Uses a deterministic random seed to guarantee
reproducibility across experimental runs.

NOTE ON INTERPRETATION:
In small evaluation benchmarks (e.g., N=39 evaluable queries), confidence intervals
provide essential visibility into sampling variability. However, non-overlapping
confidence intervals do NOT automatically establish formal statistical significance.
Paired testing (e.g., Wilcoxon signed-rank test or paired permutation testing) is required
to claim statistically significant superiority between paired models.
"""

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


@dataclass
class BootstrapResult:
    """Container for bootstrap confidence interval estimation."""

    metric: str
    mean: float
    ci_lower: float
    ci_upper: float
    num_queries: int
    bootstrap_samples: int
    random_seed: int
    confidence_level: float = 0.95
    standard_error: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def formatted_ci(self) -> str:
        return f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}]"

    @property
    def formatted_summary(self) -> str:
        return f"{self.mean:.4f} (95% CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}])"


def compute_bootstrap_ci(
    values: Sequence[float],
    metric_name: str = "metric",
    num_bootstraps: int = 2000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> BootstrapResult:
    """Compute non-parametric percentile bootstrap confidence interval for a sequence of metric values.

    Args:
        values: Sequence of per-query metric observations (floats).
        metric_name: Identifier for the metric (e.g., 'Hit@1', 'MRR').
        num_bootstraps: Number of resamples with replacement (default: 2000).
        confidence_level: Desired two-sided coverage probability (default: 0.95).
        random_seed: Deterministic integer seed for NumPy RNG (default: 42).

    Returns:
        BootstrapResult with mean, ci_lower, ci_upper, standard_error, and metadata.
    """
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)

    if n == 0:
        return BootstrapResult(
            metric=metric_name,
            mean=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            num_queries=0,
            bootstrap_samples=num_bootstraps,
            random_seed=random_seed,
            confidence_level=confidence_level,
            standard_error=0.0,
        )

    point_mean = float(np.mean(arr))

    if n == 1 or np.all(arr == arr[0]):
        # Degenerate zero-variance case
        return BootstrapResult(
            metric=metric_name,
            mean=point_mean,
            ci_lower=point_mean,
            ci_upper=point_mean,
            num_queries=n,
            bootstrap_samples=num_bootstraps,
            random_seed=random_seed,
            confidence_level=confidence_level,
            standard_error=0.0,
        )

    # Deterministic RNG
    rng = np.random.default_rng(random_seed)

    # Generate bootstrap indices: shape (num_bootstraps, n)
    indices = rng.integers(0, n, size=(num_bootstraps, n))
    bootstrap_samples = arr[indices]
    bootstrap_means = np.mean(bootstrap_samples, axis=1)

    # Percentile confidence interval
    alpha = 1.0 - confidence_level
    lower_percentile = (alpha / 2.0) * 100.0
    upper_percentile = (1.0 - (alpha / 2.0)) * 100.0

    ci_lower = float(np.percentile(bootstrap_means, lower_percentile))
    ci_upper = float(np.percentile(bootstrap_means, upper_percentile))
    se = float(np.std(bootstrap_means, ddof=1))

    return BootstrapResult(
        metric=metric_name,
        mean=round(point_mean, 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
        num_queries=n,
        bootstrap_samples=num_bootstraps,
        random_seed=random_seed,
        confidence_level=confidence_level,
        standard_error=round(se, 4),
    )


METRIC_KEY_MAP = {
    "hit_at_1": "Hit@1",
    "hit_at_3": "Hit@3",
    "hit_at_5": "Hit@5",
    "reciprocal_rank": "MRR",
    "precision_at_5": "Precision@5",
    "recall_at_5": "Recall@5",
    "ndcg_at_5": "nDCG@5",
    "keyword_coverage": "KeywordCoverage",
}


def compute_experiment_bootstrap_cis(
    predictions: List[Dict[str, Any]],
    target_metrics: Optional[List[str]] = None,
    num_bootstraps: int = 2000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
    statutory_only: bool = True,
) -> Dict[str, BootstrapResult]:
    """Compute bootstrap confidence intervals across per-query prediction records.

    Filters out non-statutory / negative queries when statutory_only is True.
    """
    if statutory_only:
        evaluable = [
            p for p in predictions
            if p.get("expected_document")
            and str(p.get("expected_document")).lower() != "none"
            and not p.get("is_negative_or_out_of_scope", False)
        ]
    else:
        evaluable = predictions

    if target_metrics is None:
        target_metrics = ["hit_at_1", "hit_at_5", "reciprocal_rank", "ndcg_at_5"]

    results: Dict[str, BootstrapResult] = {}

    for key in target_metrics:
        display_name = METRIC_KEY_MAP.get(key, key)
        values = [float(p.get(key, 0.0)) for p in evaluable if key in p]
        res = compute_bootstrap_ci(
            values=values,
            metric_name=display_name,
            num_bootstraps=num_bootstraps,
            confidence_level=confidence_level,
            random_seed=random_seed,
        )
        results[display_name] = res

    return results


def format_bootstrap_table(results: Dict[str, BootstrapResult]) -> str:
    """Format dictionary of bootstrap results into a readable markdown table."""
    lines = [
        "| Metric | N (Queries) | Mean | 95% Confidence Interval | Std Error | Bootstrap Resamples | Random Seed |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for name, r in results.items():
        lines.append(
            f"| **{r.metric}** | {r.num_queries} | {r.mean:.4f} | [{r.ci_lower:.4f}, {r.ci_upper:.4f}] | {r.standard_error:.4f} | {r.bootstrap_samples} | {r.random_seed} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compute bootstrap confidence intervals for NyayaSetu metrics.")
    parser.add_argument("--predictions", required=True, help="Path to predictions.jsonl file")
    parser.add_argument("--bootstraps", type=int, default=2000, help="Number of bootstrap resamples")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--output_json", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    if not pred_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {pred_path}")

    predictions = []
    with open(pred_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                predictions.append(json.loads(line))

    results = compute_experiment_bootstrap_cis(
        predictions=predictions,
        num_bootstraps=args.bootstraps,
        random_seed=args.seed,
    )

    print("\n" + "=" * 80)
    print(f"BOOTSTRAP CONFIDENCE INTERVALS (N = {len(predictions)} queries)")
    print("=" * 80)
    print(format_bootstrap_table(results))
    print("=" * 80 + "\n")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in results.items()}, f, indent=2)
        print(f"Saved bootstrap statistics to {out_path}")


if __name__ == "__main__":
    main()
