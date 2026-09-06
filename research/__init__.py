"""Fact-First Legal Issue Routing Research Package.

Components:
- Schemas: ExtractedFacts, NormalizedFacts, IdentifiedLegalIssue, CandidateLegalRegime, RoutingDecision, RoutingMode
- Fact Extraction: ConservativeFactExtractor
- Fact Normalization: FactNormalizer
- Issue Identification: LegalIssueIdentifier
- Issue Routing: FactFirstRouter, get_fact_first_router
"""

from research.fact_extraction import ConservativeFactExtractor
from research.fact_normalization import FactNormalizer
from research.issue_router import FactFirstRouter, get_fact_first_router
from research.legal_issue_identifier import LegalIssueIdentifier
from research.schemas import (
    CandidateLegalRegime,
    ExtractedFacts,
    IdentifiedLegalIssue,
    NormalizedFactItem,
    NormalizedFacts,
    RoutingDecision,
    RoutingMode,
)

__all__ = [
    "ConservativeFactExtractor",
    "FactNormalizer",
    "LegalIssueIdentifier",
    "FactFirstRouter",
    "get_fact_first_router",
    "ExtractedFacts",
    "NormalizedFactItem",
    "NormalizedFacts",
    "IdentifiedLegalIssue",
    "CandidateLegalRegime",
    "RoutingDecision",
    "RoutingMode",
]
