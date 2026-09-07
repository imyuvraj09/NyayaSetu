"""Comprehensive Statistical Testing & Validation Engine for NyayaSetu Phase 6.

Implements rigorous inferential statistics for comparative legal evaluation:
1. Percentile Bootstrap Confidence Intervals (B = 10,000, seed = 42).
2. Paired Wilcoxon Signed-Rank Test (non-parametric comparison of paired continuous distributions).
3. Paired McNemar's Test with continuity correction (for binary success/failure outcomes like Hit@1, Hit@5).
4. Paired Student's t-Test with Shapiro-Wilk normality checking.
5. Multiple Comparison Corrections:
   - Holm-Bonferroni step-down adjustment.
   - Benjamini-Hochberg False Discovery Rate (FDR) control.
6. Effect Size Estimation:
   - Cohen's d (paired standard deviation normalized).
   - Cliff's delta (non-parametric dominance metric).
   - Rank-biserial correlation (derived from signed-rank sum).
"""

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import scipy.stats as stats


@dataclass
class BootstrapCI:
    metric: str
    mean: float
    std_dev: float
    median: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    num_samples: int
    bootstrap_iterations: int
    random_seed: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def formatted_summary(self) -> str:
        return f"{self.mean:.4f} ± {self.std_dev:.4f} (95% CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}])"


def compute_bootstrap_ci_10k(
    values: Sequence[float],
    metric_name: str = "metric",
    num_bootstraps: int = 10000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> BootstrapCI:
    """Compute percentile bootstrap confidence interval with B=10,000 resamples."""
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)

    if n == 0:
        return BootstrapCI(
            metric=metric_name, mean=0.0, std_dev=0.0, median=0.0,
            ci_lower=0.0, ci_upper=0.0, confidence_level=confidence_level,
            num_samples=0, bootstrap_iterations=num_bootstraps, random_seed=random_seed
        )

    point_mean = float(np.mean(arr))
    point_std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    point_median = float(np.median(arr))

    if n == 1 or np.all(arr == arr[0]):
        return BootstrapCI(
            metric=metric_name, mean=point_mean, std_dev=point_std, median=point_median,
            ci_lower=point_mean, ci_upper=point_mean, confidence_level=confidence_level,
            num_samples=n, bootstrap_iterations=num_bootstraps, random_seed=random_seed
        )

    rng = np.random.default_rng(random_seed)
    resamples = rng.choice(arr, size=(num_bootstraps, n), replace=True)
    resample_means = np.mean(resamples, axis=1)

    alpha = 1.0 - confidence_level
    lower_pct = (alpha / 2.0) * 100.0
    upper_pct = (1.0 - (alpha / 2.0)) * 100.0

    ci_lower = float(np.percentile(resample_means, lower_pct))
    ci_upper = float(np.percentile(resample_means, upper_pct))

    return BootstrapCI(
        metric=metric_name,
        mean=round(point_mean, 4),
        std_dev=round(point_std, 4),
        median=round(point_median, 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
        confidence_level=confidence_level,
        num_samples=n,
        bootstrap_iterations=num_bootstraps,
        random_seed=random_seed,
    )


def compute_paired_mcnemar_test(
    baseline_outcomes: Sequence[int],
    experimental_outcomes: Sequence[int],
    continuity_correction: bool = True,
) -> Dict[str, Any]:
    """Execute paired McNemar's test for binary paired retrieval outcomes (e.g. Hit@1).
    
    Contingency table:
                     Exp Success (1)   Exp Failure (0)
    Base Success (1)        a                 b
    Base Failure (0)        c                 d
    
    Discordant pairs:
    b = Base success, Exp failure
    c = Base failure, Exp success
    """
    assert len(baseline_outcomes) == len(experimental_outcomes), "Sample sizes must match"
    n = len(baseline_outcomes)

    a = b = c = d = 0
    for base, exp in zip(baseline_outcomes, experimental_outcomes):
        b_bool = bool(base > 0)
        e_bool = bool(exp > 0)
        if b_bool and e_bool:
            a += 1
        elif b_bool and not e_bool:
            b += 1
        elif not b_bool and e_bool:
            c += 1
        else:
            d += 1

    discordant = b + c
    if discordant == 0:
        stat = 0.0
        p_val = 1.0
    else:
        if continuity_correction:
            stat = ((abs(b - c) - 1.0) ** 2) / float(discordant)
        else:
            stat = ((b - c) ** 2) / float(discordant)
        p_val = float(stats.chi2.sf(stat, df=1))

    # Odds ratio
    odds_ratio = (float(c) / float(b)) if b > 0 else (float("inf") if c > 0 else 1.0)

    return {
        "test": "mcnemar",
        "contingency_table": {"a_both_success": a, "b_base_only": b, "c_exp_only": c, "d_both_fail": d},
        "test_statistic": round(float(stat), 4),
        "p_value": round(float(p_val), 6),
        "odds_ratio": round(odds_ratio, 4) if not math.isinf(odds_ratio) else "inf",
        "is_significant": p_val < 0.05,
        "sample_size": n,
    }


def compute_paired_wilcoxon_test(
    baseline_scores: Sequence[float],
    experimental_scores: Sequence[float],
) -> Dict[str, Any]:
    """Execute paired Wilcoxon signed-rank test on per-query paired continuous metrics."""
    assert len(baseline_scores) == len(experimental_scores), "Sample sizes must match"
    b_arr = np.asarray(baseline_scores, dtype=np.float64)
    e_arr = np.asarray(experimental_scores, dtype=np.float64)
    diffs = e_arr - b_arr
    non_zero = diffs[diffs != 0.0]

    n_total = len(diffs)
    n_effective = len(non_zero)

    if n_effective == 0:
        return {
            "test": "wilcoxon_signed_rank",
            "test_statistic": 0.0,
            "p_value": 1.0,
            "rank_biserial_correlation": 0.0,
            "is_significant": False,
            "effective_n": 0,
        }

    # Use scipy wilcoxon
    res = stats.wilcoxon(diffs, alternative="two-sided", zero_method="wilcox")
    stat = float(res.statistic)
    p_val = float(res.pvalue)

    # Calculate Rank-Biserial Correlation (r_rb)
    # W+ = sum of ranks for positive differences, W- = sum of ranks for negative
    ranks = stats.rankdata(np.abs(non_zero))
    w_pos = float(np.sum(ranks[non_zero > 0]))
    w_neg = float(np.sum(ranks[non_zero < 0]))
    total_rank_sum = w_pos + w_neg
    r_rb = (w_pos - w_neg) / total_rank_sum if total_rank_sum > 0 else 0.0

    return {
        "test": "wilcoxon_signed_rank",
        "test_statistic": round(stat, 4),
        "p_value": round(p_val, 6),
        "rank_biserial_correlation": round(r_rb, 4),
        "is_significant": p_val < 0.05,
        "effective_n": n_effective,
        "w_plus": round(w_pos, 2),
        "w_minus": round(w_neg, 2),
    }


def compute_paired_ttest(
    baseline_scores: Sequence[float],
    experimental_scores: Sequence[float],
) -> Dict[str, Any]:
    """Execute paired Student's t-test with Shapiro-Wilk normality testing of differences."""
    b_arr = np.asarray(baseline_scores, dtype=np.float64)
    e_arr = np.asarray(experimental_scores, dtype=np.float64)
    diffs = e_arr - b_arr

    if np.all(diffs == 0.0):
        return {
            "test": "paired_ttest",
            "test_statistic": 0.0,
            "p_value": 1.0,
            "cohen_d": 0.0,
            "normality_p_value": 1.0,
            "is_normal": True,
            "is_significant": False,
        }

    # Shapiro-Wilk test for normality
    if len(diffs) >= 3:
        shapiro_stat, shapiro_p = stats.shapiro(diffs)
    else:
        shapiro_stat, shapiro_p = 1.0, 1.0

    res = stats.ttest_rel(e_arr, b_arr)
    t_stat = float(res.statistic)
    p_val = float(res.pvalue)

    # Cohen's d for paired samples: mean(diff) / std(diff)
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
    cohen_d = (mean_diff / std_diff) if std_diff > 0 else 0.0

    return {
        "test": "paired_ttest",
        "test_statistic": round(t_stat, 4),
        "p_value": round(p_val, 6),
        "mean_difference": round(mean_diff, 4),
        "cohen_d": round(cohen_d, 4),
        "shapiro_normality_p": round(float(shapiro_p), 6),
        "is_normal": bool(shapiro_p >= 0.05),
        "is_significant": bool(p_val < 0.05),
    }


def compute_cliffs_delta(
    baseline_scores: Sequence[float],
    experimental_scores: Sequence[float],
) -> float:
    """Compute Cliff's delta (d), non-parametric effect size in [-1.0, 1.0].
    
    Interpretation thresholds (Romano et al.):
    |delta| < 0.147 : negligible
    0.147 <= |delta| < 0.33 : small
    0.33 <= |delta| < 0.474 : medium
    |delta| >= 0.474 : large
    """
    b = np.asarray(baseline_scores, dtype=np.float64)
    e = np.asarray(experimental_scores, dtype=np.float64)
    n_b = len(b)
    n_e = len(e)

    if n_b == 0 or n_e == 0:
        return 0.0

    greater = 0
    less = 0
    for x in e:
        greater += np.sum(x > b)
        less += np.sum(x < b)

    delta = (greater - less) / (n_b * n_e)
    return round(float(delta), 4)


def apply_multiple_comparison_corrections(
    p_values: List[float],
) -> Dict[str, List[float]]:
    """Compute Holm-Bonferroni and Benjamini-Hochberg corrected p-values."""
    m = len(p_values)
    if m == 0:
        return {"holm_bonferroni": [], "benjamini_hochberg": []}

    # 1. Holm-Bonferroni (Step-Down FWER)
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    holm_adjusted = [0.0] * m
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed_p):
        multiplier = m - rank
        adjusted = min(1.0, p * multiplier)
        running_max = max(running_max, adjusted)
        holm_adjusted[orig_idx] = round(running_max, 6)

    # 2. Benjamini-Hochberg (Step-Up FDR)
    bh_adjusted = [0.0] * m
    running_min = 1.0
    # Process from highest rank down to 1
    for rank in range(m - 1, -1, -1):
        orig_idx, p = indexed_p[rank]
        i = rank + 1  # 1-indexed
        adjusted = min(1.0, (p * m) / i)
        running_min = min(running_min, adjusted)
        bh_adjusted[orig_idx] = round(running_min, 6)

    return {
        "holm_bonferroni": holm_adjusted,
        "benjamini_hochberg": bh_adjusted,
    }


def analyze_paired_metrics(
    baseline_scores: Sequence[float],
    experimental_scores: Sequence[float],
    metric_name: str,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Complete paired comparative statistical analysis between two systems for one metric."""
    b_arr = np.asarray(baseline_scores, dtype=np.float64)
    e_arr = np.asarray(experimental_scores, dtype=np.float64)

    mean_b = float(np.mean(b_arr))
    mean_e = float(np.mean(e_arr))
    diff = mean_e - mean_b

    # Bootstrap CIs for both
    ci_b = compute_bootstrap_ci_10k(b_arr, f"{metric_name}_baseline")
    ci_e = compute_bootstrap_ci_10k(e_arr, f"{metric_name}_experimental")
    ci_diff = compute_bootstrap_ci_10k(e_arr - b_arr, f"{metric_name}_difference")

    # Wilcoxon signed-rank
    wilcox = compute_paired_wilcoxon_test(b_arr, e_arr)

    # Paired t-test
    ttest = compute_paired_ttest(b_arr, e_arr)

    # Cliff's delta
    c_delta = compute_cliffs_delta(b_arr, e_arr)

    # Binary outcome check for McNemar
    mcnemar = None
    if np.all(np.isin(b_arr, [0.0, 1.0])) and np.all(np.isin(e_arr, [0.0, 1.0])):
        mcnemar = compute_paired_mcnemar_test([int(x) for x in b_arr], [int(x) for x in e_arr])

    p_val_primary = wilcox["p_value"]
    is_sig = p_val_primary < alpha

    # Qualitative Effect Size interpretation (Cohen's d)
    d_abs = abs(ttest["cohen_d"])
    if d_abs < 0.20:
        effect_label = "negligible"
    elif d_abs < 0.50:
        effect_label = "small"
    elif d_abs < 0.80:
        effect_label = "medium"
    else:
        effect_label = "large"

    return {
        "metric": metric_name,
        "baseline_mean": round(mean_b, 4),
        "baseline_ci": ci_b.formatted_summary,
        "experimental_mean": round(mean_e, 4),
        "experimental_ci": ci_e.formatted_summary,
        "difference": round(diff, 4),
        "difference_ci": ci_diff.formatted_summary,
        "wilcoxon_test": wilcox,
        "paired_ttest": ttest,
        "mcnemar_test": mcnemar,
        "cliffs_delta": c_delta,
        "cohen_d": ttest["cohen_d"],
        "effect_size_magnitude": effect_label,
        "is_statistically_significant": is_sig,
        "conclusion": "Statistically significant improvement" if (is_sig and diff > 0) else (
            "Statistically significant degradation" if (is_sig and diff < 0) else "No statistically significant difference"
        ),
    }
