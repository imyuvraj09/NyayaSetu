"""Confidence-Aware Legal Issue Router for Fact-First Retrieval.

Coordinates fact extraction, normalization, and legal issue identification to
produce traceable, confidence-aware routing decisions across statutory regimes.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from research.fact_extraction import ConservativeFactExtractor
from research.fact_normalization import FactNormalizer
from research.legal_issue_identifier import LegalIssueIdentifier
from research.schemas import (
    CandidateLegalRegime,
    IdentifiedLegalIssue,
    NormalizedFacts,
    RoutingDecision,
    RoutingMode,
)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "routing_config.yaml"


class FactFirstRouter:
    """Confidence-aware legal issue router implementing soft routing with fallback."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self.extractor = ConservativeFactExtractor()
        self.normalizer = FactNormalizer()
        self.issue_identifier = LegalIssueIdentifier()

    def _load_config(self) -> Dict[str, Any]:
        """Load routing configuration from YAML."""
        if not self.config_path.exists():
            # Fallback default configuration in case file is absent
            return {
                "regimes": {
                    "BNS_SUBSTANTIVE": {"name": "Bharatiya Nyaya Sanhita, 2023", "act_code": "BNS"},
                    "BNSS_PROCEDURAL": {"name": "Bharatiya Nagarik Suraksha Sanhita, 2023", "act_code": "BNSS"},
                    "BSA_EVIDENCE": {"name": "Bharatiya Sakshya Adhiniyam, 2023", "act_code": "BSA"},
                    "IT_ACT": {"name": "Information Technology Act", "act_code": "IT_ACT"},
                    "CONSTITUTION": {"name": "Constitution of India", "act_code": "CONSTITUTION"},
                    "GENERAL": {"name": "General Statutory Corpus", "act_code": "GENERAL"},
                },
                "issue_to_regime_map": {
                    "cyber_identity_theft_personation": "IT_ACT",
                    "substantive_theft_offence": "BNS_SUBSTANTIVE",
                    "procedural_police_arrest_powers": "BNSS_PROCEDURAL",
                    "evidentiary_electronic_records_admissibility": "BSA_EVIDENCE",
                    "constitutional_fundamental_rights": "CONSTITUTION",
                },
                "thresholds": {
                    "high_confidence": 0.70,
                    "medium_confidence": 0.40,
                    "fallback_threshold": 0.40,
                    "top_n_regimes": 3,
                },
                "strategy_parameters": {
                    "high_confidence": {"soft_boost_factor": 1.50, "global_fallback_slots": 6},
                    "medium_confidence": {"soft_boost_factor": 1.25, "global_fallback_slots": 10},
                    "low_confidence": {"soft_boost_factor": 1.00, "fallback_used": True},
                },
            }

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def route_query(self, query: str) -> RoutingDecision:
        """Execute full fact-first routing workflow for a natural language inquiry."""
        if not query or not query.strip():
            return RoutingDecision(
                selected_regimes=["GENERAL"],
                routing_mode=RoutingMode.AMBIGUOUS_FALLBACK,
                confidence=0.0,
                fallback_used=True,
                routing_reason=["Empty or whitespace query provided"],
                candidate_distribution={"GENERAL": 1.0},
            )

        # Step 1: Extract explicit facts
        facts = self.extractor.extract(query)

        # Step 2: Normalize facts
        normalized = self.normalizer.normalize(facts, query)

        # Step 3: Identify candidate legal issues
        issues = self.issue_identifier.identify_issues(normalized, query)

        # Step 4: Map issues to regimes and accumulate scores
        regimes_cfg = self.config.get("regimes", {})
        issue_map = self.config.get("issue_to_regime_map", {})
        thresholds = self.config.get("thresholds", {})
        high_thresh = thresholds.get("high_confidence", 0.70)
        med_thresh = thresholds.get("medium_confidence", 0.40)
        top_n = thresholds.get("top_n_regimes", 3)

        regime_scores: Dict[str, float] = {}
        regime_signals: Dict[str, List[str]] = {}

        for issue in issues:
            regime = issue_map.get(issue.issue_id, "GENERAL")
            curr_score = regime_scores.get(regime, 0.0)
            # Use max/noisy-OR accumulation
            combined = curr_score + issue.confidence * (1.0 - curr_score)
            regime_scores[regime] = combined
            if regime not in regime_signals:
                regime_signals[regime] = []
            regime_signals[regime].append(f"issue:{issue.issue_id} (conf={issue.confidence:.2f})")

        # Step 5: Direct statutory boost if query specifically cited an act
        for stat in facts.statutory_references:
            target_regime = None
            if stat == "BNS":
                target_regime = "BNS_SUBSTANTIVE"
            elif stat == "BNSS":
                target_regime = "BNSS_PROCEDURAL"
            elif stat == "BSA":
                target_regime = "BSA_EVIDENCE"
            elif stat == "IT_Act":
                target_regime = "IT_ACT"
            elif stat == "Constitution":
                target_regime = "CONSTITUTION"
            elif stat == "POSH":
                target_regime = "POSH_LABOUR"
            elif stat == "POCSO":
                target_regime = "POCSO_CHILD"
            elif stat == "Consumer_Protection":
                target_regime = "CONSUMER_PROTECTION"
            elif stat == "Motor_Vehicles":
                target_regime = "MOTOR_VEHICLES"

            if target_regime:
                curr = regime_scores.get(target_regime, 0.0)
                regime_scores[target_regime] = min(0.99, curr + 0.35 * (1.0 - curr))
                if target_regime not in regime_signals:
                    regime_signals[target_regime] = []
                regime_signals[target_regime].append(f"explicit_statute_citation:{stat}")

        # Step 6: Form candidate regimes
        candidate_regimes: List[CandidateLegalRegime] = []
        for reg_id, sc in sorted(regime_scores.items(), key=lambda x: x[1], reverse=True):
            reg_info = regimes_cfg.get(reg_id, {})
            reg_name = reg_info.get("name", reg_id)
            candidate_regimes.append(
                CandidateLegalRegime(
                    regime_id=reg_id,
                    regime_name=reg_name,
                    confidence=round(sc, 4),
                    supporting_signals=regime_signals.get(reg_id, []),
                    priority_boost=1.50 if sc >= high_thresh else (1.25 if sc >= med_thresh else 1.0),
                )
            )

        if not candidate_regimes:
            top_conf = 0.0
            selected = ["GENERAL"]
            mode = RoutingMode.LOW_CONFIDENCE_FALLBACK
            fallback_used = True
            reasons = ["No candidate legal regime identified"]
        else:
            top_cand = candidate_regimes[0]
            top_conf = top_cand.confidence

            # Determine mode
            if top_conf >= high_thresh and top_cand.regime_id != "GENERAL":
                mode = RoutingMode.HIGH_CONFIDENCE
                fallback_used = False
                selected = [c.regime_id for c in candidate_regimes[:top_n] if c.confidence >= med_thresh]
                reasons = [
                    f"High confidence ({top_conf:.2f} >= {high_thresh:.2f}) for regime {top_cand.regime_id}",
                    f"Primary issue: {issues[0].issue_name if issues else 'none'}",
                ]
            elif top_conf >= med_thresh and top_cand.regime_id != "GENERAL":
                mode = RoutingMode.MEDIUM_CONFIDENCE_SOFT_BOOST
                fallback_used = False
                selected = [c.regime_id for c in candidate_regimes[:top_n] if c.confidence >= (med_thresh * 0.8)]
                reasons = [
                    f"Medium confidence ({top_conf:.2f}) - soft boosting candidate regimes {selected}",
                ]
            else:
                mode = RoutingMode.LOW_CONFIDENCE_FALLBACK
                fallback_used = True
                selected = ["GENERAL"]
                reasons = [
                    f"Confidence ({top_conf:.2f}) below fallback threshold ({med_thresh:.2f}) - falling back to global retrieval",
                ]

        return RoutingDecision(
            selected_regimes=selected,
            routing_mode=mode,
            confidence=round(top_conf, 4),
            fallback_used=fallback_used,
            routing_reason=reasons,
            candidate_distribution={c.regime_id: c.confidence for c in candidate_regimes},
            candidate_regimes=candidate_regimes,
            identified_issues=issues,
            normalized_facts=normalized,
        )


_ROUTER_SINGLETON: Optional[FactFirstRouter] = None


def get_fact_first_router(config_path: Optional[str] = None) -> FactFirstRouter:
    """Obtain shared singleton instance of FactFirstRouter."""
    global _ROUTER_SINGLETON
    if _ROUTER_SINGLETON is None or config_path is not None:
        _ROUTER_SINGLETON = FactFirstRouter(config_path=config_path)
    return _ROUTER_SINGLETON
