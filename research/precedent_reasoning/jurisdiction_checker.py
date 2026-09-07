"""Jurisdictional Relevance Evaluator for Judicial Precedents.

Assesses territorial and statutory jurisdiction:
1. National Jurisdiction (Supreme Court of India):
   - Always DIRECTLY_RELEVANT across all Indian legal questions.
2. State / Territorial Jurisdiction (High Courts):
   - DIRECTLY_RELEVANT if target state matches High Court's territory.
   - GENERALLY_RELEVANT if interpreting a Central Act applicable across India.
   - PERSUASIVE if interpreting state-specific legislation from another state.
3. Unknown or Unspecified Jurisdiction:
   - Preserves UNKNOWN when user query does not provide a geographic context.
"""

from typing import Optional

from research.precedent_reasoning.court_hierarchy import (
    HIGH_COURT_TERRITORIES,
    CourtHierarchyEngine,
)
from research.precedent_reasoning.models import (
    CourtLevel,
    JudicialPrecedent,
    JurisdictionAssessment,
    JurisdictionRelevance,
)


class JurisdictionChecker:
    """Evaluates whether a precedent appears jurisdictionally relevant."""

    @classmethod
    def check_jurisdiction(
        cls,
        precedent: JudicialPrecedent,
        target_state_or_territory: Optional[str] = None,
        is_central_statute: bool = True,
    ) -> JurisdictionAssessment:
        """Evaluate jurisdictional alignment between precedent and target query.

        Args:
            precedent: Judicial precedent candidate.
            target_state_or_territory: Explicit location/state from query (or None).
            is_central_statute: Whether the legal question concerns an all-India Central enactment.

        Returns:
            JurisdictionAssessment with relevance rating and bounded multiplier.
        """
        court_level = precedent.court_level

        # 1. Supreme Court of India is national
        if court_level == CourtLevel.SUPREME_COURT:
            return JurisdictionAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                target_jurisdiction=target_state_or_territory or "India (National)",
                precedent_jurisdiction="India (National)",
                jurisdiction_relevance=JurisdictionRelevance.DIRECTLY_RELEVANT,
                relevance_multiplier=1.10,
                reasoning="Supreme Court of India possesses nationwide territorial jurisdiction.",
            )

        # 2. High Court jurisdiction
        if court_level == CourtLevel.HIGH_COURT:
            hc_state = CourtHierarchyEngine.identify_high_court_state(precedent.court)
            precedent_jur = hc_state.title() if hc_state else precedent.court

            if target_state_or_territory and hc_state:
                target_clean = target_state_or_territory.lower().strip()
                # Check if target state in HC territories
                territory_list = HIGH_COURT_TERRITORIES.get(hc_state, [hc_state])
                if any(t in target_clean or target_clean in t for t in territory_list):
                    return JurisdictionAssessment(
                        precedent_id=precedent.chunk_id,
                        case_name=precedent.case_name,
                        target_jurisdiction=target_state_or_territory,
                        precedent_jurisdiction=precedent_jur,
                        jurisdiction_relevance=JurisdictionRelevance.DIRECTLY_RELEVANT,
                        relevance_multiplier=1.10,
                        reasoning=f"{precedent.court} possesses direct territorial jurisdiction over {target_state_or_territory}.",
                    )
                else:
                    return JurisdictionAssessment(
                        precedent_id=precedent.chunk_id,
                        case_name=precedent.case_name,
                        target_jurisdiction=target_state_or_territory,
                        precedent_jurisdiction=precedent_jur,
                        jurisdiction_relevance=JurisdictionRelevance.PERSUASIVE,
                        relevance_multiplier=0.95,
                        reasoning=f"{precedent.court} is outside primary territorial jurisdiction ({target_state_or_territory}); persuasive value only.",
                    )

            # If no target territory specified, but Central statute
            if is_central_statute:
                return JurisdictionAssessment(
                    precedent_id=precedent.chunk_id,
                    case_name=precedent.case_name,
                    target_jurisdiction="Unspecified (Central Law)",
                    precedent_jurisdiction=precedent_jur,
                    jurisdiction_relevance=JurisdictionRelevance.GENERALLY_RELEVANT,
                    relevance_multiplier=1.02,
                    reasoning=f"{precedent.court} decision interpreting Central Act is generally relevant across India.",
                )

            return JurisdictionAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                target_jurisdiction="UNKNOWN",
                precedent_jurisdiction=precedent_jur,
                jurisdiction_relevance=JurisdictionRelevance.UNKNOWN,
                relevance_multiplier=1.0,
                reasoning="Target jurisdiction unspecified; jurisdictional alignment remains UNKNOWN.",
            )

        # 3. Tribunals and District Courts
        return JurisdictionAssessment(
            precedent_id=precedent.chunk_id,
            case_name=precedent.case_name,
            target_jurisdiction=target_state_or_territory or "UNKNOWN",
            precedent_jurisdiction=precedent.metadata.jurisdiction,
            jurisdiction_relevance=JurisdictionRelevance.PERSUASIVE if is_central_statute else JurisdictionRelevance.UNKNOWN,
            relevance_multiplier=0.90,
            reasoning=f"Precedent from {precedent.court} evaluated as persuasive/local jurisdiction.",
        )
