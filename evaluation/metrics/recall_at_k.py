"""True Multi-Target Recall@K retrieval metric for NyayaSetu.

Definition:
    Recall@K = (Number of unique relevant items retrieved in top K) / (Total number of unique relevant items)

Mathematically:
    Recall@K = |Top_K ∩ Relevant| / |Relevant|

Critical Rule:
    This is true multi-target recall over the set of known ground-truth items.
    It MUST NOT be conflated with binary Hit@K.

Example:
    Retrieved: [A, B, C, D]
    Relevant:  [B, D, E]

    Recall@1 = 0 / 3 = 0.0
    Recall@2 = 1 / 3 = 0.3333   (item B retrieved)
    Recall@4 = 2 / 3 = 0.6667   (items B, D retrieved out of {B, D, E})
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


def calculate_recall_at_k(
    retrieved: Sequence[Any],
    relevant: Union[Iterable[Any], Any],
    k: int,
    partial_match: bool = False,
) -> float:
    """Calculate true multi-target Recall@K for a single query.

    Args:
        retrieved: Sequence of retrieved document IDs or names.
        relevant: Set, sequence, or single string of relevant IDs/names.
        k: Ranking cutoff threshold (1-indexed).
        partial_match: If True, checks substring inclusion.
                       If False (default), enforces exact equality.

    Returns:
        Fraction of total relevant items retrieved in top K (in [0.0, 1.0]).
        Returns 0.0 if relevant target set is empty.
    """
    if k <= 0 or not retrieved:
        return 0.0

    targets = _normalize_to_set(relevant)
    if not targets:
        return 0.0

    total_relevant = len(targets)
    top_k = retrieved[:k]
    matched_targets: Set[str] = set()

    for item in top_k:
        if item is None:
            continue
        item_str = str(item).strip().lower()
        if not item_str:
            continue

        if partial_match:
            for t in targets:
                if t in item_str or item_str in t:
                    matched_targets.add(t)
        else:
            if item_str in targets:
                matched_targets.add(item_str)

    return round(len(matched_targets) / total_relevant, 4)


def calculate_mean_recall_at_k(
    all_retrieved: Sequence[Sequence[Any]],
    all_relevant: Sequence[Union[Iterable[Any], Any]],
    k: int,
    partial_match: bool = False,
) -> float:
    """Calculate Mean Recall@K across multiple queries."""
    if not all_retrieved or not all_relevant:
        return 0.0

    count = min(len(all_retrieved), len(all_relevant))
    if count == 0:
        return 0.0

    total_recall = sum(
        calculate_recall_at_k(all_retrieved[i], all_relevant[i], k, partial_match=partial_match)
        for i in range(count)
    )
    return round(total_recall / count, 4)
