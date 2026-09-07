"""Answer-level grounding scorer aggregating atomic claim support and citation accuracy.

Computes weighted grounding scores, high-risk error counts, and citation metrics
with transparent calculation and full intermediate value exports.
"""

from typing import Dict, List, Tuple

from research.claim_grounding.models import (
    CitationStatus,
    ClaimGroundingDecision,
    ClaimStatus,
    RiskLevel,
)

DEFAULT_SUPPORT_SCORES: Dict[ClaimStatus, float] = {
    ClaimStatus.SUPPORTED: 1.00,
    ClaimStatus.PARTIALLY_SUPPORTED: 0.50,
    ClaimStatus.INSUFFICIENT_EVIDENCE: 0.25,
    ClaimStatus.UNSUPPORTED: 0.00,
    ClaimStatus.CONTRADICTED: -0.50,
}


class GroundingScorer:
    """Computes weighted answer-level grounding and citation metrics."""

    def __init__(self, support_score_map: Dict[ClaimStatus, float] = None):
        self.score_map = dict(DEFAULT_SUPPORT_SCORES)
        if support_score_map:
            self.score_map.update(support_score_map)

    def calculate_grounding_score(
        self,
        decisions: List[ClaimGroundingDecision],
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate weighted answer-level grounding score and intermediate totals.

        Returns:
            (final_grounding_score [0.0 - 1.0], intermediate_values_dict)
        """
        if not decisions:
            return 1.0, {"total_weight": 0.0, "weighted_support_sum": 0.0}

        weighted_support_sum = 0.0
        total_weight = 0.0

        for d in decisions:
            weight = d.claim.importance_weight
            s_val = self.score_map.get(d.status, 0.0)
            weighted_support_sum += weight * s_val
            total_weight += weight

        if total_weight <= 0.0:
            raw_score = 1.0
        else:
            raw_score = weighted_support_sum / total_weight

        # Bound score between 0.0 and 1.0
        bounded_score = max(0.0, min(1.0, raw_score))

        intermediates = {
            "total_weight": round(total_weight, 4),
            "weighted_support_sum": round(weighted_support_sum, 4),
            "raw_score": round(raw_score, 4),
            "bounded_score": round(bounded_score, 4),
        }

        return round(bounded_score, 4), intermediates

    def compute_citation_metrics(
        self,
        decisions: List[ClaimGroundingDecision],
    ) -> Tuple[float, float]:
        """Compute citation accuracy and citation completeness across all decisions.

        Returns:
            (citation_accuracy [0.0 - 1.0], citation_completeness [0.0 - 1.0])
        """
        all_citation_results = []
        for d in decisions:
            all_citation_results.extend(d.citation_results)

        if not all_citation_results:
            return 1.0, 1.0

        valid_count = sum(1 for c in all_citation_results if c.status == CitationStatus.VALID_CITATION)
        total_citations = len(all_citation_results)
        accuracy = valid_count / total_citations if total_citations > 0 else 1.0

        # Completeness: fraction of claims requiring citations that actually have valid citations
        claims_needing_citations = [
            d for d in decisions
            if d.claim.risk_level == RiskLevel.HIGH
        ]
        if not claims_needing_citations:
            completeness = 1.0
        else:
            claims_with_valid_cits = sum(
                1 for d in claims_needing_citations
                if any(c.status == CitationStatus.VALID_CITATION for c in d.citation_results)
            )
            completeness = claims_with_valid_cits / len(claims_needing_citations)

        return round(accuracy, 4), round(completeness, 4)
