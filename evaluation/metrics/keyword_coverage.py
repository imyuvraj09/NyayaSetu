"""Keyword coverage metric for NyayaSetu legal retrieval evaluation."""

from typing import List, Sequence


def calculate_keyword_coverage(text: str, expected_keywords: Sequence[str]) -> float:
    """Calculate the fraction of expected legal terms present in the retrieved text.

    Definition:
        Coverage = (count of keywords found in text) / (total expected keywords)
    """
    if not expected_keywords:
        return 1.0
    if not text:
        return 0.0

    text_lower = text.lower()
    found = sum(1 for kw in expected_keywords if kw and str(kw).lower() in text_lower)
    return round(found / len(expected_keywords), 4)
