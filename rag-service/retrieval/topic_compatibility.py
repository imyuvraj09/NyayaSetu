"""
Topic Compatibility & Evidence Budgeting Layer for NyayaSetu Legal Assistant.

Re-exports universal evidence relevance filtering from retrieval.evidence_relevance_filter
for backward compatibility while ensuring zero hardcoded rules.
"""

from retrieval.evidence_relevance_filter import (
    EvidenceCompatibility as TopicCompatibility,
    EvidenceEvaluationResult,
    TopicCompatibilityEngine,
    UniversalEvidenceFilter,
)

__all__ = [
    "TopicCompatibility",
    "EvidenceEvaluationResult",
    "TopicCompatibilityEngine",
    "UniversalEvidenceFilter",
]
