"""Backward-compatible evaluation metrics module for NyayaSetu.

Refactored in Phase 1 to provide a clean compatibility layer forwarding to the
new modular package in `evaluation.metrics`:
- evaluation.metrics.hit_at_k
- evaluation.metrics.precision_at_k
- evaluation.metrics.recall_at_k
- evaluation.metrics.mrr
- evaluation.metrics.ndcg

Preserves exact legacy signatures while correcting the previously defective
pseudo-recall definition to true multi-target recall.
"""

from typing import Any, Iterable, List, Optional, Sequence, Union

from evaluation.metrics.hit_at_k import (
    calculate_hit_at_k as _new_calculate_hit_at_k,
    calculate_mean_hit_at_k,
)
from evaluation.metrics.mrr import (
    calculate_mrr,
    calculate_reciprocal_rank as _new_calculate_reciprocal_rank,
)
from evaluation.metrics.ndcg import (
    calculate_dcg_at_k,
    calculate_idcg_at_k,
    calculate_mean_ndcg_at_k,
    calculate_ndcg_at_k,
)
from evaluation.metrics.precision_at_k import (
    calculate_mean_precision_at_k,
    calculate_precision_at_k as _new_calculate_precision_at_k,
)
from evaluation.metrics.recall_at_k import (
    calculate_mean_recall_at_k,
    calculate_recall_at_k as _new_calculate_recall_at_k,
)


def calculate_hit_at_k(
    retrieved_docs: Sequence[str],
    expected_doc: Union[str, Iterable[str]],
    k: int,
) -> bool:
    """Determine if the expected legal document appears within the top-k retrieved results.

    Backward-compatible wrapper returning bool. Uses substring inclusion for document names.
    """
    score = _new_calculate_hit_at_k(retrieved_docs, expected_doc, k, partial_match=True)
    return bool(score > 0.0)


def calculate_reciprocal_rank(
    retrieved_docs: Sequence[str],
    expected_doc: Union[str, Iterable[str]],
) -> float:
    """Calculate the Reciprocal Rank (RR) of the first retrieved chunk matching expected_doc.

    Backward-compatible wrapper.
    """
    return _new_calculate_reciprocal_rank(retrieved_docs, expected_doc, partial_match=True)


def calculate_precision_at_k(
    retrieved_docs: Sequence[str],
    expected_doc: Union[str, Iterable[str]],
    k: int,
) -> float:
    """Calculate the proportion of retrieved chunks in top-k that belong to expected_doc.

    Backward-compatible wrapper.
    """
    return _new_calculate_precision_at_k(retrieved_docs, expected_doc, k, partial_match=True)


def calculate_recall_at_k(
    retrieved_docs: Sequence[str],
    expected_doc: Union[str, Iterable[str]],
    k: int,
) -> float:
    """Calculate true Recall@K for retrieved documents against relevant target(s).

    NOTE (Phase 1 Fix):
        The legacy implementation returned Hit@K (1.0 if any match else 0.0).
        This function now computes mathematically true multi-target recall:
        |Retrieved_K ∩ Relevant| / |Relevant|.
    """
    return _new_calculate_recall_at_k(retrieved_docs, expected_doc, k, partial_match=True)


def calculate_keyword_coverage(text: str, expected_keywords: List[str]) -> float:
    """Calculate the fraction of expected legal terms present in the retrieved text.

    Definition:
        Coverage = (count of keywords found in text) / (total expected keywords)
    """
    if not expected_keywords:
        return 1.0
    text_lower = text.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    return round(found / len(expected_keywords), 4)


__all__ = [
    "calculate_hit_at_k",
    "calculate_mean_hit_at_k",
    "calculate_reciprocal_rank",
    "calculate_mrr",
    "calculate_precision_at_k",
    "calculate_mean_precision_at_k",
    "calculate_recall_at_k",
    "calculate_mean_recall_at_k",
    "calculate_keyword_coverage",
    "calculate_dcg_at_k",
    "calculate_idcg_at_k",
    "calculate_ndcg_at_k",
    "calculate_mean_ndcg_at_k",
]
