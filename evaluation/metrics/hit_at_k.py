"""Hit@K retrieval metric for NyayaSetu.

Definition:
    Hit@K = 1.0 if at least one relevant document appears in the top K retrieved results,
            0.0 otherwise.

Mathematically:
    Hit@K = 1 if |Top_K ∩ Relevant| >= 1 else 0
"""

from typing import Any, Iterable, List, Optional, Sequence, Set, Union


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


def calculate_hit_at_k(
    retrieved: Sequence[Any],
    relevant: Union[Iterable[Any], Any],
    k: int,
    partial_match: bool = False,
) -> float:
    """Calculate Hit@K for a single query.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevant: Set, sequence, or single string of relevant IDs/names.
        k: Ranking cutoff threshold (1-indexed).
        partial_match: If True, checks substring inclusion (useful for legacy full document names).
                       If False (default, recommended), enforces exact string equality.

    Returns:
        1.0 if at least one relevant item appears in top K, else 0.0.
    """
    if k <= 0 or not retrieved:
        return 0.0

    targets = _normalize_to_set(relevant)
    if not targets:
        return 0.0

    top_k = retrieved[:k]
    for item in top_k:
        if item is None:
            continue
        item_str = str(item).strip().lower()
        if not item_str:
            continue

        if partial_match:
            if any(t in item_str or item_str in t for t in targets):
                return 1.0
        else:
            if item_str in targets:
                return 1.0

    return 0.0


def calculate_mean_hit_at_k(
    all_retrieved: Sequence[Sequence[Any]],
    all_relevant: Sequence[Union[Iterable[Any], Any]],
    k: int,
    partial_match: bool = False,
) -> float:
    """Calculate Mean Hit@K across multiple queries.

    Args:
        all_retrieved: Sequence of retrieved sequences for each query.
        all_relevant: Sequence of relevant sets/lists for each query.
        k: Ranking cutoff threshold.
        partial_match: Substring matching flag.

    Returns:
        Mean Hit@K score in [0.0, 1.0].
    """
    if not all_retrieved or not all_relevant:
        return 0.0

    count = min(len(all_retrieved), len(all_relevant))
    if count == 0:
        return 0.0

    total_hits = sum(
        calculate_hit_at_k(all_retrieved[i], all_relevant[i], k, partial_match=partial_match)
        for i in range(count)
    )
    return round(total_hits / count, 4)
