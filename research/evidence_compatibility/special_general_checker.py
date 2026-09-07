"""Special Law vs General Law (Lex Specialis) Compatibility Checker.

Evaluates whether specialized statutory enactments (e.g. IT Act, POSH, POCSO)
possess superior doctrinal specificity over generic enactments (e.g. BNS, IPC).

CRITICAL RULE:
DO NOT hard-code a universal "special law always wins" rule.
Instead, generate a reasoned compatibility signal that prioritizes specific provisions
while preserving general provisions as complementary alternatives where legally viable.
"""

from typing import Any, Dict, List, Optional, Tuple

from research.evidence_compatibility.models import (
    CompatibilityStatus,
    CompatibilityViolation,
)
from research.evidence_compatibility.rules import (
    SPECIAL_LAW_PREFERENCES,
    STATUTE_REGISTRY,
    resolve_statute_key,
)
from research.schemas import RoutingDecision


class SpecialGeneralCompatibilityChecker:
    """Evaluates doctrinal precedence and specificity between special and general statutes."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.general_penalty = self.config.get("general_law_discount_when_special_applies", 0.25)

    def check_special_general_compatibility(
        self,
        document_name: str,
        source_filename: str,
        routing_decision: Optional[RoutingDecision],
    ) -> Tuple[float, CompatibilityStatus, List[CompatibilityViolation], List[str], List[str]]:
        """Evaluate whether retrieved evidence is appropriately specific for the inquiry."""
        violations: List[CompatibilityViolation] = []
        supporting_signals: List[str] = []
        rejected_signals: List[str] = []

        statute_key = resolve_statute_key(document_name, source_filename)
        if not statute_key:
            return 1.0, CompatibilityStatus.UNCERTAIN, violations, ["Unknown statute; neutral specificity score"], []

        if not routing_decision or routing_decision.fallback_used or not routing_decision.selected_regimes:
            supporting_signals.append("No specific legal regime routed; neutral special/general balance")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        selected_regimes = routing_decision.selected_regimes
        evidence_regime = STATUTE_REGISTRY.get(statute_key, {}).get("regime_id", "")

        # Check if any selected regime is a recognized Special Law
        active_special_regimes = [r for r in selected_regimes if r in SPECIAL_LAW_PREFERENCES]

        if not active_special_regimes:
            # Query is not governed by a specialized statute
            supporting_signals.append("Inquiry governed by general or procedural statutory framework")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        # If evidence belongs to the active special regime -> strong positive compatibility
        if evidence_regime in active_special_regimes:
            supporting_signals.append(
                f"Evidence from specialized enactment {statute_key} directly matches specialized legal regime"
            )
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        # If evidence is a general statute when a special statute is primarily routed
        # (e.g. general BNS cheating retrieved for an IT Act cyber identity theft query)
        for spec_reg in active_special_regimes:
            pref_map = SPECIAL_LAW_PREFERENCES.get(spec_reg, {})
            if evidence_regime in pref_map or statute_key in pref_map:
                reason = pref_map.get(evidence_regime) or pref_map.get(statute_key, "Special law takes precedence")
                penalty = self.general_penalty * routing_decision.confidence
                score = max(0.40, 1.0 - penalty)
                msg = (
                    f"Specialized enactment preferred over general statute: {reason}. "
                    f"Applying soft discount ({penalty:.2f}) while preserving general law as fallback."
                )
                rejected_signals.append(msg)
                violations.append(
                    CompatibilityViolation(
                        dimension="special_general",
                        severity="MEDIUM",
                        rule_name="SPECIAL_LAW_PRECEDENCE_DISCOUNT",
                        message=msg,
                        penalty=penalty,
                    )
                )
                return score, CompatibilityStatus.PARTIALLY_COMPATIBLE, violations, supporting_signals, rejected_signals

        supporting_signals.append(f"Statute {statute_key} accepted as complementary to specialized legal regime")
        return 0.90, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals
