"""Compatibility Scoring Engine for Transparent, Auditable Evidence Evaluation.

Calculates multi-dimensional compatibility scores with configurable weights:
Total Score = w_regime * S_regime
            + w_issue * S_issue
            + w_role * S_role
            + w_temporal * S_temporal
            + w_special_general * S_special_general
            + w_relationship * S_relationship

Computes soft re-ranking multipliers without dropping documents catastrophically.
"""

from typing import Any, Dict, List, Optional, Tuple

from research.evidence_compatibility.models import (
    CompatibilityScore,
    CompatibilityStatus,
    CompatibilityViolation,
)


class CompatibilityScorer:
    """Computes transparent, weighted compatibility scores and soft multipliers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        weights = self.config.get("weights", {})
        self.w_regime = weights.get("regime", 0.25)
        self.w_issue = weights.get("issue", 0.25)
        self.w_role = weights.get("legal_role", 0.20)
        self.w_temporal = weights.get("temporal", 0.15)
        self.w_special_general = weights.get("special_general", 0.10)
        self.w_relationship = weights.get("relationship", 0.05)

        thresholds = self.config.get("thresholds", {})
        self.thresh_compatible = thresholds.get("compatible", 0.80)
        self.thresh_partially = thresholds.get("partially_compatible", 0.55)
        self.thresh_hard_exclusion = thresholds.get("hard_exclusion", 0.25)

        soft_cfg = self.config.get("soft_ranking", {})
        self.min_multiplier = soft_cfg.get("min_multiplier", 0.35)
        self.max_multiplier = soft_cfg.get("max_multiplier", 1.20)

    def calculate_score(
        self,
        regime_score: float,
        issue_score: float,
        legal_role_score: float,
        temporal_score: float,
        special_general_score: float,
        relationship_score: float,
        violations: List[CompatibilityViolation],
    ) -> Tuple[CompatibilityScore, CompatibilityStatus]:
        """Compute the composite compatibility score and status."""
        total_weight = (
            self.w_regime
            + self.w_issue
            + self.w_role
            + self.w_temporal
            + self.w_special_general
            + self.w_relationship
        )
        if total_weight <= 0:
            total_weight = 1.0

        raw_sum = (
            self.w_regime * regime_score
            + self.w_issue * issue_score
            + self.w_role * legal_role_score
            + self.w_temporal * temporal_score
            + self.w_special_general * special_general_score
            + self.w_relationship * relationship_score
        )
        normalized_score = max(0.0, min(1.0, raw_sum / total_weight))

        # Soft multiplier maps [0.0, 1.0] -> [min_multiplier, max_multiplier]
        # preserving relative candidate scores without zeroing out evidence
        soft_mult = self.min_multiplier + (self.max_multiplier - self.min_multiplier) * (normalized_score ** 1.2)

        # Status determination
        has_critical = any(v.severity == "CRITICAL" for v in violations)
        has_high = any(v.severity == "HIGH" for v in violations)

        if normalized_score >= self.thresh_compatible and not has_critical and not has_high:
            status = CompatibilityStatus.COMPATIBLE
        elif normalized_score >= self.thresh_partially:
            status = CompatibilityStatus.PARTIALLY_COMPATIBLE
        elif has_critical or (has_high and normalized_score < 0.50):
            status = CompatibilityStatus.INCOMPATIBLE
        else:
            status = CompatibilityStatus.UNCERTAIN

        score_obj = CompatibilityScore(
            regime_score=regime_score,
            issue_score=issue_score,
            legal_role_score=legal_role_score,
            temporal_score=temporal_score,
            special_general_score=special_general_score,
            relationship_score=relationship_score,
            total_score=normalized_score,
            soft_multiplier=soft_mult,
        )

        return score_obj, status
