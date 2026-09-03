"""
Query preprocessing module for NyayaSetu Legal Knowledge Assistant.

Performs deterministic, non-destructive query normalization while preserving
all exact legal terms, citations, sections, case names, and wording.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessedQuery:
    """Normalized query representation with provenance tracking."""

    original_query: str
    normalized_query: str
    char_count: int
    word_count: int


# Canonical Indian statutory and legal acronym expansions
LEGAL_ACRONYM_EXPANSIONS = [
    (re.compile(r"\b(?:POCSO(?:\s+Act)?)\b", re.IGNORECASE), "POCSO (Protection of Children from Sexual Offences Act)"),
    (re.compile(r"\b(?:POSH(?:\s+Act)?)\b", re.IGNORECASE), "POSH (Sexual Harassment of Women at Workplace Act)"),
    (re.compile(r"\b(?:RTE(?:\s+Act)?)\b", re.IGNORECASE), "RTE (Right of Children to Free and Compulsory Education Act)"),
    (re.compile(r"\b(?:RTI(?:\s+Act)?)\b", re.IGNORECASE), "RTI (Right to Information Act)"),
    (re.compile(r"\b(?:GST(?:\s+Act)?)\b", re.IGNORECASE), "GST (Goods and Services Tax Act)"),
    (re.compile(r"\b(?:IBC|IBC\s+Code)\b", re.IGNORECASE), "IBC (Insolvency and Bankruptcy Code)"),
    (re.compile(r"\b(?:CIRP)\b", re.IGNORECASE), "CIRP (Corporate Insolvency Resolution Process)"),
    (re.compile(r"\b(?:ICC)\b", re.IGNORECASE), "ICC (Internal Complaints Committee)"),
    (re.compile(r"\b(?:CSR)\b", re.IGNORECASE), "CSR (Corporate Social Responsibility)"),
]


def process_query(query: str) -> ProcessedQuery:
    """Validate and conservatively clean a natural language legal query.

    Operations:
    1. Reject empty or whitespace-only queries with ValueError.
    2. Normalize redundant horizontal and vertical whitespaces to single spaces.
    3. Strip outer whitespace.
    4. Expand well-known Indian statutory acronyms (POCSO, POSH, RTI, etc.) to their canonical titles
       for enhanced semantic vector retrieval recall against statutory bare acts.
    5. Preserve all original terminology, citations, sections, and casing.

    Args:
        query: Raw user query string.

    Returns:
        ProcessedQuery object with original and normalized forms.

    Raises:
        ValueError: If the query is empty or contains only whitespace.
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query string cannot be empty or null.")

    # Collapse any sequence of whitespace characters (spaces, tabs, newlines) to a single space
    cleaned = re.sub(r"\s+", " ", query).strip()

    if not cleaned:
        raise ValueError("Query cannot be blank or whitespace-only.")

    # Expand known Indian legal acronyms if not already spelled out
    expanded = cleaned
    for pattern, replacement in LEGAL_ACRONYM_EXPANSIONS:
        # Check if abbreviation exists and the full phrase is not already present
        core_expansion = replacement.split("(")[-1].rstrip(")")
        if pattern.search(expanded) and core_expansion.lower() not in expanded.lower():
            expanded = pattern.sub(replacement, expanded)

    return ProcessedQuery(
        original_query=query,
        normalized_query=expanded,
        char_count=len(expanded),
        word_count=len(expanded.split()),
    )
