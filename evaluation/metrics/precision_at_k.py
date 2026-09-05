"""Precision@K retrieval metric for NyayaSetu.

Definition:
    Precision@K = (Number of unique relevant items retrieved in top K) / (Evaluated retrieved positions)

Convention:
    When fewer than K items are returned by the retriever (|retrieved| < K), the denominator is
    set to min(K, |retrieved|). This ensures that a system returning 2 perfect results for K=5
    is evaluated on the positions it produced, rather than artificially penalizing small candidate
    sets when small corpora or strict relevance filters apply.
    Alternatively, if strict_k=True, the denominator is strictly K (classical TREC definition).

Example:
    Retrieved: [A, B, C]
    Relevant:  [B, C, D]

    Precision@1 = 0 / 1 = 0.0
    Precision@2 = 1 / 2 = 0.5
    Precision@3 = 2 / 3 = 0.6667
"""

from typing import Any, Iterable, Sequence, Set, Union


def _normalize_to_set(items: Union[Iterable[Any], Any]) -> Set[str]:
    """Convert items into a normalized set of non-empty lowercased strings."""
    if items is None:
        return set()
    if isinstance(items, str):
        cleaned = items.strip().lower()
        return {cleaned} if cleaned and cleaned != "none" else set()

    result: Set[str] = set()
    for item in items:
        if item is not None:
            cleaned = str(item).strip().lower()
            if cleaned and cleaned != "none":
                result.add(cleaned)
    return result


def calculate_precision_at_k(
    retrieved: Sequence[Any],
    relevant: Union[Iterable[Any], Any],
    k: int,
    partial_match: bool = False,
    strict_k: bool = False,
) -> float:
    """Calculate Precision@K for a single query.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevant: Set, sequence, or single string of relevant IDs/names.
        k: Ranking cutoff threshold (1-indexed).
        partial_match: If True, uses substring inclusion.
        strict_k: If True, denominator is always k (traditional TREC formulation).
                  If False (default), denominator is min(k, len(retrieved)) to avoid
                  penalizing systems where fewer than k candidates were returned.

    Returns:
        Precision@K score in [0.0, 1.0].
    """
    if k <= 0 or not retrieved:
        return 0.0

    targets = _normalize_to_set(relevant)
    if not targets:
        return 0.0

    evaluated_positions = k if strict_k else min(k, len(retrieved))
    if evaluated_positions <= 0:
        return 0.0

    top_k = retrieved[:k]
    matched_relevant: Set[str] = set()
    relevant_count = 0

    for item in top_k:
        if item is None:
            continue
        item_str = str(item).strip().lower()
        if not item_str:
            continue

        if partial_match:
            matching = [t for t in targets if t in item_str or item_str in t]
            if matching:
                relevant_count += 1
        else:
            if item_str in targets:
                # Count relevant occurrence
                relevant_count += 1

    return round(relevant_count / evaluated_positions, 4)


def calculate_mean_precision_at_k(
    all_retrieved: Sequence[Sequence[Any]],
    all_relevant: Sequence[Union[Iterable[Any], Any]],
    k: int,
    partial_match: bool = False,
    strict_k: bool = False,
) -> float:
    """Calculate Mean Precision@K across multiple queries."""
    if not all_retrieved or not all_relevant:
        return 0.0

    count = min(len(all_retrieved), len(all_relevant))
    if count == 0:
        return 0.0

    total_precision = sum(
        calculate_precision_at_k(
            all_retrieved[i],
            all_relevant[i],
            k,
            partial_match=partial_match,
            strict_k=strict_k,
        )
        for i in range(count)
    )
    return round(total_precision / count, 4)
