"""Deterministic Court Authority Classifier under Article 141 and Judicial Precedence.

Analyzes:
1. Constitutional binding force:
   - Supreme Court of India ratio is BINDING nationwide under Article 141.
   - High Court ratio is BINDING within its territorial jurisdiction, PERSUASIVE elsewhere.
   - Tribunals have BINDING authority on respective specialized subjects, subject to High Court/Supreme Court judicial review.
2. Bench composition:
   - Larger benches carry higher authoritative weight than smaller coordinate benches.
3. Passage role:
   - Holdings, ratios, and legal tests carry primary authority.
   - Factual narrative or procedural background carries limited precedential value.
"""

from typing import Optional

from research.precedent_reasoning.court_hierarchy import CourtHierarchyEngine
from research.precedent_reasoning.models import (
    AuthorityAssessment,
    AuthorityStatus,
    CourtLevel,
    JudicialPrecedent,
)


class PrecedentAuthorityClassifier:
    """Classifies the precedential authority of judicial decisions."""

    @classmethod
    def evaluate_authority(
        cls,
        precedent: JudicialPrecedent,
        target_jurisdiction: Optional[str] = None,
    ) -> AuthorityAssessment:
        """Evaluate binding and persuasive authority of a retrieved precedent.

        Args:
            precedent: The judicial precedent candidate.
            target_jurisdiction: State or territorial scope of the query (if specified).

        Returns:
            AuthorityAssessment detailing binding status, score multiplier, and legal basis.
        """
        court_level = precedent.court_level
        meta = precedent.metadata
        bench_weight = CourtHierarchyEngine.get_bench_multiplier(meta.bench_strength)
        p_type = str(precedent.passage_type).upper()

        # 1. Supreme Court of India
        if court_level == CourtLevel.SUPREME_COURT:
            is_art_141 = p_type in ("HOLDING", "RATIO", "LEGAL_TEST", "STATUTORY_INTERPRETATION") or precedent.is_holding_or_ratio

            if is_art_141:
                auth_status = AuthorityStatus.BINDING
                base_score = 1.15
                reasoning = (
                    f"Supreme Court of India decision in '{precedent.case_name}' is BINDING across all courts "
                    f"in India under Article 141 of the Constitution. Passage contains operative {p_type}."
                )
            else:
                auth_status = AuthorityStatus.HIGHLY_PERSUASIVE
                base_score = 1.05
                reasoning = (
                    f"Supreme Court of India decision in '{precedent.case_name}' carries high persuasive authority, "
                    f"though passage is classified as {p_type} rather than direct ratio decidendi."
                )

            final_auth_score = min(1.55, base_score * bench_weight)
            return AuthorityAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                court_level=court_level,
                authority_status=auth_status,
                authority_score=round(final_auth_score, 4),
                bench_weight=bench_weight,
                binding_jurisdiction="National (All India)",
                reasoning=reasoning,
                confidence=0.95,
                article_141_binding=is_art_141,
            )

        # 2. High Court
        if court_level == CourtLevel.HIGH_COURT:
            hc_key = CourtHierarchyEngine.identify_high_court_state(precedent.court)
            hc_display = hc_key.title() if hc_key else "State"
            from research.precedent_reasoning.court_hierarchy import HIGH_COURT_TERRITORIES
            territories = HIGH_COURT_TERRITORIES.get(hc_key, []) if hc_key else []
            is_target_match = False
            if target_jurisdiction:
                tj = target_jurisdiction.lower().strip()
                if hc_key and (tj in hc_key or hc_key in tj):
                    is_target_match = True
                elif any(tj in terr or terr in tj for terr in territories):
                    is_target_match = True
                elif meta and meta.jurisdiction and (tj in meta.jurisdiction.lower() or meta.jurisdiction.lower() in tj):
                    is_target_match = True

            if is_target_match:
                auth_status = AuthorityStatus.BINDING
                base_score = 1.15
                reasoning = (
                    f"{precedent.court} decision is BINDING within {hc_display} jurisdiction for subordinate courts."
                )
            else:
                auth_status = AuthorityStatus.PERSUASIVE
                base_score = 1.05
                reasoning = (
                    f"{precedent.court} decision carries PERSUASIVE value across other states and coordinate High Courts."
                )

            final_auth_score = min(1.20, base_score * bench_weight)
            return AuthorityAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                court_level=court_level,
                authority_status=auth_status,
                authority_score=round(final_auth_score, 4),
                bench_weight=bench_weight,
                binding_jurisdiction=hc_display,
                reasoning=reasoning,
                confidence=0.85,
                article_141_binding=False,
            )

        # 3. Tribunal
        if court_level == CourtLevel.TRIBUNAL:
            return AuthorityAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                court_level=court_level,
                authority_status=AuthorityStatus.PERSUASIVE,
                authority_score=1.0,
                bench_weight=1.0,
                binding_jurisdiction="Subject-matter Tribunal Scope",
                reasoning=f"{precedent.court} decision provides specialized subject-matter authority.",
                confidence=0.75,
                article_141_binding=False,
            )

        # 4. District / Subordinate Court
        if court_level == CourtLevel.DISTRICT_COURT:
            return AuthorityAssessment(
                precedent_id=precedent.chunk_id,
                case_name=precedent.case_name,
                court_level=court_level,
                authority_status=AuthorityStatus.LIMITED_AUTHORITY,
                authority_score=0.90,
                bench_weight=1.0,
                binding_jurisdiction="Local District",
                reasoning=f"{precedent.court} decision has limited precedential value; non-binding on superior courts.",
                confidence=0.70,
                article_141_binding=False,
            )

        # 5. Unknown Court
        return AuthorityAssessment(
            precedent_id=precedent.chunk_id,
            case_name=precedent.case_name,
            court_level=CourtLevel.UNKNOWN,
            authority_status=AuthorityStatus.UNKNOWN,
            authority_score=0.80,
            bench_weight=1.0,
            binding_jurisdiction="UNKNOWN",
            reasoning="Court hierarchy could not be verified from available metadata; authority remains UNKNOWN.",
            confidence=0.50,
            article_141_binding=False,
        )
