"""Discounted Cumulative Gain (DCG) and Normalized DCG (nDCG@K) for NyayaSetu.

Supports graded relevance:
    0 = irrelevant
    1 = marginally relevant
    2 = relevant
    3 = highly relevant

Standard Formulations:
    Exponential (TREC / Burges et al., default):
        DCG@K = sum_{i=1}^{min(K, |retrieved|)} (2^{rel_i} - 1) / log2(i + 1)
        IDCG@K = sum_{i=1}^{min(K, |relevant|)} (2^{rel^*_i} - 1) / log2(i + 1)
        where rel^* is the sequence of ideal relevance gains sorted in descending order.

    Linear:
        DCG@K = sum_{i=1}^{min(K, |retrieved|)} rel_i / log2(i + 1)

    nDCG@K = DCG@K / IDCG@K if IDCG@K > 0 else 0.0

Design Rules:
    - Zero division safety: IDCG = 0 yields 0.0.
    - Gracefully handles K larger than retrieved count or relevant count.
    - Fully independent of specific legal benchmark schema.
"""

import math
from typing import Any, Dict, Iterable, Optional, Sequence, Union


def _get_gain(rel_value: float, formulation: str = "exponential") -> float:
    """Calculate numerator gain from relevance score."""
    if formulation == "exponential":
        return (2.0 ** float(rel_value)) - 1.0
    return float(rel_value)


def calculate_dcg_at_k(
    retrieved: Sequence[Any],
    relevance_scores: Dict[str, float],
    k: int,
    formulation: str = "exponential",
) -> float:
    """Calculate Discounted Cumulative Gain at rank K.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevance_scores: Mapping from item ID/name (lowercased) to numeric relevance score.
        k: Ranking cutoff threshold.
        formulation: 'exponential' (default, (2^r - 1)/log2(i+1)) or 'linear' (r/log2(i+1)).

    Returns:
        DCG@K float value.
    """
    if k <= 0 or not retrieved:
        return 0.0

    dcg = 0.0
    for rank, item in enumerate(retrieved[:k], start=1):
        if item is None:
            continue
        item_key = str(item).strip().lower()
        rel = float(relevance_scores.get(item_key, 0.0))
        if rel <= 0.0:
            continue
        gain = _get_gain(rel, formulation=formulation)
        discount = math.log2(rank + 1)  # log2(2) = 1 for rank 1
        dcg += gain / discount

    return round(dcg, 6)


def calculate_idcg_at_k(
    relevance_scores: Union[Dict[str, float], Sequence[float]],
    k: int,
    formulation: str = "exponential",
) -> float:
    """Calculate Ideal Discounted Cumulative Gain at rank K.

    Args:
        relevance_scores: Dict of item->score or sequence of relevance scores.
        k: Ranking cutoff threshold.
        formulation: 'exponential' or 'linear'.

    Returns:
        IDCG@K float value.
    """
    if k <= 0 or not relevance_scores:
        return 0.0

    if isinstance(relevance_scores, dict):
        scores = list(relevance_scores.values())
    else:
        scores = list(relevance_scores)

    sorted_scores = sorted([float(s) for s in scores if float(s) > 0.0], reverse=True)
    if not sorted_scores:
        return 0.0

    idcg = 0.0
    for rank, rel in enumerate(sorted_scores[:k], start=1):
        gain = _get_gain(rel, formulation=formulation)
        discount = math.log2(rank + 1)
        idcg += gain / discount

    return round(idcg, 6)


def calculate_ndcg_at_k(
    retrieved: Sequence[Any],
    relevance: Union[Dict[str, float], Iterable[str]],
    k: int,
    formulation: str = "exponential",
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at rank K.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevance: Either:
                   - Dict[str, float] mapping item ID/name to graded relevance score (e.g. 0 to 3)
                   - Iterable[str] of binary relevant target IDs (each assigned score = 1.0)
        k: Ranking cutoff threshold.
        formulation: 'exponential' (default) or 'linear'.

    Returns:
        nDCG@K in [0.0, 1.0].
    """
    if k <= 0 or not retrieved or not relevance:
        return 0.0

    # Normalize relevance mapping
    rel_map: Dict[str, float] = {}
    if isinstance(relevance, dict):
        for k_item, score in relevance.items():
            if k_item is not None and score > 0:
                rel_map[str(k_item).strip().lower()] = float(score)
    else:
        for item in relevance:
            if item is not None:
                cleaned = str(item).strip().lower()
                if cleaned and cleaned != "none":
                    rel_map[cleaned] = 1.0

    if not rel_map:
        return 0.0

    idcg = calculate_idcg_at_k(rel_map, k=k, formulation=formulation)
    if idcg <= 0.0:
        return 0.0

    dcg = calculate_dcg_at_k(retrieved, rel_map, k=k, formulation=formulation)
    return round(min(1.0, max(0.0, dcg / idcg)), 4)


def calculate_mean_ndcg_at_k(
    all_retrieved: Sequence[Sequence[Any]],
    all_relevance: Sequence[Union[Dict[str, float], Iterable[str]]],
    k: int,
    formulation: str = "exponential",
) -> float:
    """Calculate Mean nDCG@K across multiple queries."""
    if not all_retrieved or not all_relevance:
        return 0.0

    count = min(len(all_retrieved), len(all_relevance))
    if count == 0:
        return 0.0

    total_ndcg = sum(
        calculate_ndcg_at_k(all_retrieved[i], all_relevance[i], k=k, formulation=formulation)
        for i in range(count)
    )
    return round(total_ndcg / count, 4)
