"""Unified Precedent Reasoning Engine Orchestrator.

Integrates all Phase 7 judicial reasoning subsystems:
1. Retrieval (PrecedentRetriever)
2. Authority Classification (PrecedentAuthorityClassifier)
3. Jurisdictional Relevance (JurisdictionChecker)
4. Temporal Validation (PrecedentTemporalValidator)
5. Relationship Analysis (PrecedentRelationshipAnalyzer)
6. In-Memory Citation Graph (PrecedentCitationGraph)
7. Conflict Detection (PrecedentConflictDetector)
8. Statute-Precedent Compatibility (StatutePrecedentChecker)
9. Authority-Aware Re-ranking (AuthorityAwareRanker)
10. Tiered Precedent Synthesis (PrecedentSynthesizer)
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import yaml

from research.precedent_reasoning.authority_classifier import (
    PrecedentAuthorityClassifier,
)
from research.precedent_reasoning.authority_ranker import AuthorityAwareRanker
from research.precedent_reasoning.case_retriever import PrecedentRetriever
from research.precedent_reasoning.citation_graph import PrecedentCitationGraph
from research.precedent_reasoning.conflict_detector import (
    PrecedentConflictDetector,
)
from research.precedent_reasoning.jurisdiction_checker import (
    JurisdictionChecker,
)
from research.precedent_reasoning.models import (
    AuthorityAssessment,
    JudicialPrecedent,
    JurisdictionAssessment,
    PrecedentReasoningResult,
    PrecedentRelationshipType,
    PrecedentTemporalStatus,
)
from research.precedent_reasoning.precedent_relationship_analyzer import (
    PrecedentRelationshipAnalyzer,
)
from research.precedent_reasoning.precedent_synthesizer import (
    PrecedentSynthesizer,
)
from research.precedent_reasoning.statute_precedent_checker import (
    StatutePrecedentChecker,
)
from research.precedent_reasoning.temporal_validator import (
    PrecedentTemporalValidator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class PrecedentReasoningEngine:
    """Orchestrates evidence-grounded judicial precedent retrieval and authority reasoning."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config = self._load_config(config_path)
        self.retriever = PrecedentRetriever(
            collection_name=self.config.get("retrieval", {}).get("collection_name", "nyayasetu_case_law"),
            top_k=self.config.get("retrieval", {}).get("top_k", 5),
        )
        self.ranker = AuthorityAwareRanker(config=self.config.get("ranking", {}))

    @staticmethod
    def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or fallback to default."""
        cfg_file = Path(config_path) if config_path else (REPO_ROOT / "configs" / "precedent_reasoning_config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def reason_over_precedents(
        self,
        query: str,
        candidates: Optional[List[JudicialPrecedent]] = None,
        target_sections: Optional[List[str]] = None,
        target_statutes: Optional[List[str]] = None,
        target_jurisdiction: Optional[str] = None,
        routed_regime: Optional[str] = None,
        top_k: int = 5,
    ) -> PrecedentReasoningResult:
        """Execute complete authority-aware precedent reasoning on a query.

        Args:
            query: User's legal inquiry.
            candidates: Optional pre-retrieved precedent candidates (if None, retrieved automatically).
            target_sections: Target sections from routing or query analysis.
            target_statutes: Target statutes from routing or query analysis.
            target_jurisdiction: Geographic jurisdiction (state) if specified.
            routed_regime: Routed legal regime from Phase 3.
            top_k: Number of final precedents to retain.

        Returns:
            PrecedentReasoningResult object containing ranked precedents, graph, and audit trails.
        """
        t0 = time.perf_counter()
        audit_log: List[str] = []

        # 1. Retrieve candidates if not provided
        if candidates is None:
            candidates = self.retriever.retrieve_precedents(
                query=query,
                target_sections=target_sections,
                target_statutes=target_statutes,
                top_k=top_k * 2,
            )
            audit_log.append(f"Retrieved {len(candidates)} precedent candidate passages.")
        else:
            audit_log.append(f"Received {len(candidates)} pre-retrieved precedent candidates.")

        if not candidates:
            return PrecedentReasoningResult(
                query=query,
                retrieved_precedents=[],
                ranked_precedents=[],
                ranking_decisions=[],
                authority_assessments={},
                jurisdiction_assessments={},
                relationships=[],
                conflicts=[],
                execution_time_ms=(time.perf_counter() - t0) * 1000.0,
                audit_log=audit_log,
            )

        # 2. Evaluate individual precedent dimensions
        authority_assessments: Dict[str, AuthorityAssessment] = {}
        jurisdiction_assessments: Dict[str, JurisdictionAssessment] = {}
        temporal_assessments: Dict[str, Any] = {}
        compatibility_assessments: Dict[str, Any] = {}

        for p in candidates:
            cid = p.chunk_id

            # Authority assessment
            auth = PrecedentAuthorityClassifier.evaluate_authority(p, target_jurisdiction=target_jurisdiction)
            authority_assessments[cid] = auth

            # Jurisdiction assessment
            jur = JurisdictionChecker.check_jurisdiction(p, target_state_or_territory=target_jurisdiction)
            jurisdiction_assessments[cid] = jur

            # Temporal assessment
            temp_res = PrecedentTemporalValidator.validate_temporal_status(p)
            temporal_assessments[cid] = temp_res

            # Statute-precedent compatibility
            comp_res = StatutePrecedentChecker.evaluate_compatibility(
                p, target_statutes=target_statutes, target_sections=target_sections, routed_regime=routed_regime
            )
            compatibility_assessments[cid] = comp_res

        # 3. Inter-precedent relationships & Citation Graph
        relationships = PrecedentRelationshipAnalyzer.analyze_all_relationships(candidates)
        citation_graph = PrecedentCitationGraph()
        for p in candidates:
            citation_graph.add_precedent(p)
        for r in relationships:
            citation_graph.add_relationship(r)
        audit_log.append(f"Identified {len(relationships)} explicit precedent relationships.")

        # Propagate citation graph overruling findings to temporal assessments
        for p in candidates:
            cid = p.chunk_id
            is_ovr, ovr_by = citation_graph.is_overruled(p.case_name)
            if is_ovr and ovr_by:
                temporal_assessments[cid] = (
                    PrecedentTemporalStatus.OVERRULED,
                    0.30,
                    f"Overruled by '{ovr_by}' verified via citation graph.",
                )

        # 4. Conflict detection
        conflicts = PrecedentConflictDetector.detect_conflicts(candidates, relationships)
        audit_log.append(f"Evaluated conflicts: {len(conflicts)} detected/harmonized.")

        # Compute citation in-degree centrality boosts
        citation_boosts: Dict[str, float] = {}
        for p in candidates:
            incoming_authoritative = 0
            for r in relationships:
                if PrecedentRelationshipAnalyzer._matches_name(p.case_name, r.target_case):
                    if r.relationship_type in (
                        PrecedentRelationshipType.FOLLOWED,
                        PrecedentRelationshipType.RELIED_ON,
                        PrecedentRelationshipType.DISTINGUISHED,
                    ):
                        incoming_authoritative += 1
            boost = 1.0 + (0.04 * min(incoming_authoritative, 3))
            citation_boosts[p.chunk_id] = boost

        # 5. Authority-Aware Re-ranking
        ranked_precedents, ranking_decisions = self.ranker.rank_precedents(
            precedents=candidates,
            authority_assessments=authority_assessments,
            jurisdiction_assessments=jurisdiction_assessments,
            temporal_assessments=temporal_assessments,
            compatibility_assessments=compatibility_assessments,
            citation_boosts=citation_boosts,
        )

        top_ranked = ranked_precedents[:top_k]

        # 6. Categorization & Synthesis
        categorized = PrecedentSynthesizer.categorize_precedents(
            precedents=top_ranked,
            authority_assessments=authority_assessments,
            conflicts=conflicts,
            relationships=relationships,
        )

        statute_comp_scores = {cid: compatibility_assessments[cid][0] for cid in compatibility_assessments}
        execution_time = (time.perf_counter() - t0) * 1000.0

        return PrecedentReasoningResult(
            query=query,
            retrieved_precedents=candidates,
            ranked_precedents=top_ranked,
            ranking_decisions=ranking_decisions[:top_k],
            authority_assessments=authority_assessments,
            jurisdiction_assessments=jurisdiction_assessments,
            relationships=relationships,
            conflicts=conflicts,
            controlling_precedents=categorized.get("controlling", []),
            supporting_precedents=categorized.get("supporting", []),
            persuasive_precedents=categorized.get("persuasive", []),
            conflicting_precedents=categorized.get("conflicting", []),
            unknown_authority_precedents=categorized.get("unknown", []),
            statute_compatibility_scores=statute_comp_scores,
            execution_time_ms=execution_time,
            audit_log=audit_log,
        )


_ENGINE_INSTANCE: Optional[PrecedentReasoningEngine] = None


def get_precedent_reasoning_engine(config_path: Optional[str] = None) -> PrecedentReasoningEngine:
    """Return singleton instance of PrecedentReasoningEngine."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = PrecedentReasoningEngine(config_path=config_path)
    return _ENGINE_INSTANCE
