"""Authority-Aware Precedent Re-Ranker with Explainable Multipliers.

Reranks candidate judicial precedents using:
1. Semantic / retrieval score
2. Constitutional authority score (Supreme Court Article 141, High Court)
3. Jurisdictional alignment score
4. Statute-precedent compatibility score
5. Temporal validity multiplier
6. Passage role weighting (Holding/Ratio > Factual narrative)

Strictly bounded to avoid catastrophic elimination, preserving explainability audit trails.
"""

from typing import Any, Dict, List, Optional, Tuple

from research.precedent_reasoning.models import (
    AuthorityAssessment,
    JudicialPrecedent,
    JurisdictionAssessment,
    PrecedentRankingDecision,
    PrecedentTemporalStatus,
)


class AuthorityAwareRanker:
    """Computes soft, explainable ranking scores combining retrieval and legal authority."""

    PASSAGE_WEIGHTS = {
        "HOLDING": 1.15,
        "RATIO": 1.12,
        "LEGAL_TEST": 1.10,
        "STATUTORY_INTERPRETATION": 1.08,
        "CONCLUSION": 1.02,
        "GENERAL": 1.0,
        "FACTUAL_BACKGROUND": 0.90,
        "PROCEDURAL_HISTORY": 0.85,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.authority_weight = self.config.get("authority_weight", 1.0)
        self.jurisdiction_weight = self.config.get("jurisdiction_weight", 1.0)
        self.compatibility_weight = self.config.get("compatibility_weight", 1.0)
        self.temporal_weight = self.config.get("temporal_weight", 1.0)
        self.min_score_floor = self.config.get("min_score_floor", 0.10)

    def rank_precedents(
        self,
        precedents: List[JudicialPrecedent],
        authority_assessments: Dict[str, AuthorityAssessment],
        jurisdiction_assessments: Dict[str, JurisdictionAssessment],
        temporal_assessments: Dict[str, Tuple[PrecedentTemporalStatus, float, str]],
        compatibility_assessments: Dict[str, Tuple[float, str]],
        citation_boosts: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[JudicialPrecedent], List[PrecedentRankingDecision]]:
        """Re-rank candidate precedents using authority-aware adjustments.

        Returns:
            Tuple of (sorted_precedents, list_of_ranking_decisions).
        """
        scored_candidates: List[Tuple[float, JudicialPrecedent, PrecedentRankingDecision]] = []

        for idx, p in enumerate(precedents, start=1):
            cid = p.chunk_id
            orig_score = p.retrieval_score

            # 1. Authority factor
            auth = authority_assessments.get(cid)
            auth_mult = auth.authority_score if auth else 1.0

            # 2. Jurisdiction factor
            jur = jurisdiction_assessments.get(cid)
            jur_mult = jur.relevance_multiplier if jur else 1.0

            # 3. Compatibility factor
            comp_mult, comp_reason = compatibility_assessments.get(cid, (1.0, "Neutral"))

            # 4. Temporal factor
            temp_status, temp_mult, temp_reason = temporal_assessments.get(
                cid, (PrecedentTemporalStatus.APPLICABLE, 1.0, "Default")
            )

            # 5. Passage role factor
            p_type = str(p.passage_type).upper()
            passage_mult = self.PASSAGE_WEIGHTS.get(p_type, 1.0)

            # 6. Citation centrality factor
            cite_mult = citation_boosts.get(cid, 1.0) if citation_boosts else 1.0

            # Combined soft multiplier
            combined_multiplier = (
                (auth_mult ** self.authority_weight)
                * (jur_mult ** self.jurisdiction_weight)
                * (comp_mult ** self.compatibility_weight)
                * (temp_mult ** self.temporal_weight)
                * passage_mult
                * cite_mult
            )

            final_score = max(self.min_score_floor, orig_score * combined_multiplier)

            # Compile audit explanations
            reasons = []
            if auth_mult > 1.0:
                reasons.append(f"Authority boost ({auth.authority_status.value}): {auth.reasoning}")
            elif auth_mult < 1.0:
                reasons.append(f"Authority penalty: {auth.reasoning if auth else 'Subordinate court'}")

            if jur_mult != 1.0:
                reasons.append(f"Jurisdiction adjustment ({jur.jurisdiction_relevance.value}): {jur.reasoning if jur else ''}")

            if comp_mult != 1.0:
                reasons.append(f"Statutory compatibility ({comp_mult:.2f}x): {comp_reason}")

            if temp_mult != 1.0:
                reasons.append(f"Temporal status ({temp_status.value}): {temp_reason}")

            dec = PrecedentRankingDecision(
                chunk_id=cid,
                case_name=p.case_name,
                original_score=round(orig_score, 4),
                authority_multiplier=round(auth_mult, 4),
                jurisdiction_multiplier=round(jur_mult, 4),
                compatibility_multiplier=round(comp_mult, 4),
                temporal_multiplier=round(temp_mult, 4),
                passage_multiplier=round(passage_mult, 4),
                final_score=round(final_score, 4),
                rank_before=idx,
                rank_after=idx,  # Updated after sorting
                adjustment_reasons=reasons,
            )

            scored_candidates.append((final_score, p, dec))

        # Sort descending by final score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        ranked_precedents: List[JudicialPrecedent] = []
        ranking_decisions: List[PrecedentRankingDecision] = []

        for new_rank, (f_score, prec, dec) in enumerate(scored_candidates, start=1):
            prec.retrieval_score = f_score
            dec.rank_after = new_rank
            ranked_precedents.append(prec)
            ranking_decisions.append(dec)

        return ranked_precedents, ranking_decisions
