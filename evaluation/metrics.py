"""
Evaluation metrics module for NyayaSetu Legal RAG Quality Assurance.

Defines exact mathematical formulas and limitations for:
- Document Hit@K
- Mean Reciprocal Rank (MRR)
- Precision@K
- Recall@K (pseudo-recall based on known expected enactment)
- Keyword Coverage
"""

from typing import List, Optional


def calculate_hit_at_k(retrieved_docs: List[str], expected_doc: str, k: int) -> bool:
    """Determine if the expected legal document appears within the top-k retrieved results.

    Definition:
        Hit@K = 1 if any retrieved_docs[0:k] matches expected_doc else 0.

    Limitations:
        Measures document-level presence only. Does not guarantee section-level precision.
    """
    if not expected_doc or expected_doc.lower() == "none":
        return False
    target = expected_doc.lower()
    return any(target in doc.lower() for doc in retrieved_docs[:k])


def calculate_reciprocal_rank(retrieved_docs: List[str], expected_doc: str) -> float:
    """Calculate the Reciprocal Rank (RR) of the first retrieved chunk matching expected_doc.

    Definition:
        RR = 1 / rank_first_match, or 0.0 if expected_doc is not in retrieved_docs.
        MRR = (1 / N) * sum(RR_i) across all queries.
    """
    if not expected_doc or expected_doc.lower() == "none":
        return 0.0
    target = expected_doc.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if target in doc.lower():
            return 1.0 / rank
    return 0.0


def calculate_precision_at_k(retrieved_docs: List[str], expected_doc: str, k: int) -> float:
    """Calculate the proportion of retrieved chunks in top-k that belong to expected_doc.

    Definition:
        Precision@K = (count of chunks in top-k matching expected_doc) / k
    """
    if not expected_doc or expected_doc.lower() == "none" or k <= 0:
        return 0.0
    target = expected_doc.lower()
    matches = sum(1 for doc in retrieved_docs[:k] if target in doc.lower())
    return round(matches / k, 4)


def calculate_recall_at_k(retrieved_docs: List[str], expected_doc: str, k: int) -> float:
    """Calculate pseudo-recall for document-level retrieval.

    Definition:
        1.0 if expected_doc is retrieved at least once in top-k, else 0.0.

    Limitations:
        Because exhaustive binary relevance annotations across all 4,184 chunks
        are not feasible without a judicial bench, this represents single-target
        discovery recall rather than complete passage recall.
    """
    return 1.0 if calculate_hit_at_k(retrieved_docs, expected_doc, k) else 0.0


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
