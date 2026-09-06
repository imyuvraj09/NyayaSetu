"""Reciprocal Rank (RR) and Mean Reciprocal Rank (MRR) metrics for NyayaSetu.

Definition:
    Reciprocal Rank (RR) = 1 / rank_first_relevant
    where rank_first_relevant is the 1-indexed position of the FIRST relevant item in the retrieved list.
    If no relevant items appear in the retrieved results (or within cutoff K), RR = 0.0.

    Mean Reciprocal Rank (MRR) = (1 / N) * sum(RR_i) across N queries.

Example:
    Retrieved: [A, B, C, D]
    Relevant:  [C, D]

    First relevant is 'C' at rank 3 -> RR = 1 / 3 = 0.3333
"""

from typing import Any, Iterable, Optional, Sequence, Set, Union


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


def calculate_reciprocal_rank(
    retrieved: Sequence[Any],
    relevant: Union[Iterable[Any], Any],
    k: Optional[int] = None,
    partial_match: bool = False,
) -> float:
    """Calculate Reciprocal Rank (RR) for a single query.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevant: Set, sequence, or single string of relevant IDs/names.
        k: Optional cutoff threshold. If provided, only results up to rank k are evaluated.
        partial_match: If True, uses substring inclusion.

    Returns:
        1.0 / rank of first relevant item, or 0.0 if not found.
    """
    if not retrieved:
        return 0.0

    targets = _normalize_to_set(relevant)
    if not targets:
        return 0.0

    candidates = retrieved[:k] if (k is not None and k > 0) else retrieved

    for rank, item in enumerate(candidates, start=1):
        if item is None:
            continue
        item_str = str(item).strip().lower()
        if not item_str:
            continue

        if partial_match:
            if any(t in item_str or item_str in t for t in targets):
                return round(1.0 / rank, 4)
        else:
            if item_str in targets:
                return round(1.0 / rank, 4)

    return 0.0


def calculate_mrr(
    all_retrieved: Sequence[Sequence[Any]],
    all_relevant: Sequence[Union[Iterable[Any], Any]],
    k: Optional[int] = None,
    partial_match: bool = False,
) -> float:
    """Calculate Mean Reciprocal Rank (MRR) across multiple queries.

    Args:
        all_retrieved: Sequence of retrieved sequences for each query.
        all_relevant: Sequence of relevant target sets for each query.
        k: Optional cutoff threshold.
        partial_match: Substring match flag.

    Returns:
        Arithmetic mean of Reciprocal Ranks in [0.0, 1.0].
    """
    if not all_retrieved or not all_relevant:
        return 0.0

    count = min(len(all_retrieved), len(all_relevant))
    if count == 0:
        return 0.0

    total_rr = sum(
        calculate_reciprocal_rank(
            all_retrieved[i],
            all_relevant[i],
            k=k,
            partial_match=partial_match,
        )
        for i in range(count)
    )
    return round(total_rr / count, 4)
