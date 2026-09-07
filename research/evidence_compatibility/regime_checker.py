"""Regime Compatibility Checker for NyayaSetu Evidence Compatibility Filtering.

Evaluates whether retrieved legal evidence belongs to:
1. The selected target legal regime(s)
2. A legitimately related regime (e.g., procedural bridge)
3. An unrelated competing regime

Generates structured audit violations and confidence-aware soft penalties rather than
catastrophic hard boolean exclusion.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from research.evidence_compatibility.models import (
    CompatibilityStatus,
    CompatibilityViolation,
)
from research.evidence_compatibility.rules import (
    COHERENT_REGIME_BRIDGES,
    STATUTE_REGISTRY,
    resolve_statute_key,
)
from research.schemas import RoutingDecision


class RegimeCompatibilityChecker:
    """Verifies statutory regime alignment between query routing and retrieved evidence."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.competing_penalty = self.config.get("competing_regime_penalty", 0.50)
        self.related_bonus = self.config.get("related_regime_weight", 0.85)

    def check_regime_compatibility(
        self,
        document_name: str,
        source_filename: str,
        routing_decision: Optional[RoutingDecision],
    ) -> Tuple[float, CompatibilityStatus, List[CompatibilityViolation], List[str], List[str]]:
        """Evaluate regime compatibility score and structured violations.

        Returns:
            Tuple of (score, status, violations, supporting_signals, rejected_signals)
        """
        supporting_signals: List[str] = []
        rejected_signals: List[str] = []
        violations: List[CompatibilityViolation] = []

        statute_key = resolve_statute_key(document_name, source_filename)
        if not statute_key:
            return 0.70, CompatibilityStatus.UNCERTAIN, violations, ["Unknown statute; unpenalized neutral score"], []

        evidence_regime = STATUTE_REGISTRY[statute_key].get("regime_id", "GENERAL")

        # If no routing decision or fallback used, return neutral score
        if routing_decision is None or routing_decision.fallback_used or not routing_decision.selected_regimes:
            supporting_signals.append(f"Routing in fallback/neutral mode; regime {evidence_regime} accepted neutrally")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        selected_regimes = routing_decision.selected_regimes
        confidence = routing_decision.confidence

        # 1. Direct match with primary or selected regimes
        if evidence_regime in selected_regimes:
            supporting_signals.append(f"Direct regime alignment: {evidence_regime} in selected {selected_regimes}")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        # 2. Check if evidence_regime is a recognized coherent bridge
        is_coherent_bridge = False
        for s_reg in selected_regimes:
            bridge_set = COHERENT_REGIME_BRIDGES.get(s_reg, set())
            if evidence_regime in bridge_set:
                is_coherent_bridge = True
                supporting_signals.append(
                    f"Evidence regime {evidence_regime} is a legitimate procedural/evidentiary bridge for {s_reg}"
                )
                break

        if is_coherent_bridge:
            score = max(0.80, min(1.0, self.related_bonus + 0.1 * (1.0 - confidence)))
            return score, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        # 3. Competing unrelated regime detected
        penalty = self.competing_penalty * max(0.5, confidence)
        score = max(0.15, 1.0 - penalty)
        severity = "HIGH" if confidence > 0.70 else "MEDIUM"

        msg = (
            f"Evidence from regime '{evidence_regime}' ({document_name}) does not match routed regimes "
            f"{selected_regimes} and is not an established procedural/evidentiary companion."
        )
        rejected_signals.append(msg)
        violations.append(
            CompatibilityViolation(
                dimension="regime",
                severity=severity,
                rule_name="UNRELATED_COMPETING_REGIME",
                message=msg,
                penalty=penalty,
            )
        )

        status = CompatibilityStatus.INCOMPATIBLE if score < 0.40 else CompatibilityStatus.PARTIALLY_COMPATIBLE
        return score, status, violations, supporting_signals, rejected_signals
