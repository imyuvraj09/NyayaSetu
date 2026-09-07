"""Evidence Compatibility Filter Engine for NyayaSetu Legal RAG.

Integrates:
1. Fact-First Routing Decision
2. Regime Compatibility Checker
3. Legal Issue Compatibility Checker
4. Legal Role Compatibility Checker (Substantive vs Procedural vs Evidentiary)
5. Temporal Applicability Checker (Zero hallucination on missing dates)
6. Special Law vs General Law Precedence Checker
7. Inter-Chunk Evidence Relationship Analyzer
8. Transparent Soft Re-ranking Scorer

Provides deterministic, auditable, explainable legal evidence filtering with sub-millisecond overhead.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from research.evidence_compatibility.issue_checker import IssueCompatibilityChecker
from research.evidence_compatibility.legal_role_checker import LegalRoleCompatibilityChecker
from research.evidence_compatibility.models import (
    CompatibilityDecision,
    CompatibilityResult,
    CompatibilityStatus,
    LegalRole,
    TemporalStatus,
)
from research.evidence_compatibility.regime_checker import RegimeCompatibilityChecker
from research.evidence_compatibility.relationship_analyzer import EvidenceRelationshipAnalyzer
from research.evidence_compatibility.rules import resolve_statute_key
from research.evidence_compatibility.scoring import CompatibilityScorer
from research.evidence_compatibility.special_general_checker import SpecialGeneralCompatibilityChecker
from research.evidence_compatibility.temporal_checker import TemporalCompatibilityChecker
from research.schemas import ExtractedFacts, NormalizedFacts, RoutingDecision
from schemas.retrieval import RetrievedChunk

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "evidence_compatibility_config.yaml"


class EvidenceCompatibilityEngine:
    """Orchestrates multi-dimensional evidence compatibility evaluation and soft re-ranking."""

    def __init__(self, config_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        if config is not None:
            self.config = config
            self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        else:
            self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            self.config = self._load_config()

        # Initialize dimension checkers
        self.regime_checker = RegimeCompatibilityChecker(self.config.get("regime_checker"))
        self.issue_checker = IssueCompatibilityChecker(self.config.get("issue_checker"))
        self.role_checker = LegalRoleCompatibilityChecker(self.config.get("legal_role_checker"))
        self.temporal_checker = TemporalCompatibilityChecker(self.config.get("temporal_checker"))
        self.special_general_checker = SpecialGeneralCompatibilityChecker(self.config.get("special_general_checker"))
        self.relationship_analyzer = EvidenceRelationshipAnalyzer(self.config.get("relationship_analyzer"))
        self.scorer = CompatibilityScorer(self.config.get("scoring"))

        self.allow_hard_exclusion = self.config.get("allow_hard_exclusion", False)

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration or return robust defaults."""
        if not self.config_path.exists():
            return {
                "allow_hard_exclusion": False,
                "scoring": {
                    "weights": {
                        "regime": 0.25,
                        "issue": 0.25,
                        "legal_role": 0.20,
                        "temporal": 0.15,
                        "special_general": 0.10,
                        "relationship": 0.05,
                    },
                    "thresholds": {
                        "compatible": 0.80,
                        "partially_compatible": 0.55,
                        "hard_exclusion": 0.25,
                    },
                    "soft_ranking": {
                        "min_multiplier": 0.35,
                        "max_multiplier": 1.20,
                    },
                },
            }

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def evaluate_single_chunk(
        self,
        query: str,
        chunk: Any,
        routing_decision: Optional[RoutingDecision] = None,
        facts: Optional[ExtractedFacts] = None,
    ) -> CompatibilityDecision:
        """Perform comprehensive dimensional compatibility evaluation on a single chunk."""
        chunk_id = getattr(chunk, "chunk_id", "unknown")
        doc_name = getattr(chunk, "document_name", "")
        source_fn = getattr(chunk, "source_filename", "")
        text = getattr(chunk, "text", "")
        meta = getattr(chunk, "metadata", {}) or {}
        section = meta.get("section_number") or getattr(chunk, "section_number", None)

        all_violations = []
        all_supporting = []
        all_rejected = []

        # 1. Regime Compatibility
        regime_score, regime_status, reg_viols, reg_sup, reg_rej = self.regime_checker.check_regime_compatibility(
            doc_name, source_fn, routing_decision
        )
        all_violations.extend(reg_viols)
        all_supporting.extend(reg_sup)
        all_rejected.extend(reg_rej)

        # 2. Issue Compatibility
        identified_issues = routing_decision.identified_issues if routing_decision else []
        norm_facts = routing_decision.normalized_facts if routing_decision else None
        issue_score, issue_status, iss_viols, iss_sup, iss_rej = self.issue_checker.check_issue_compatibility(
            text, doc_name, section, identified_issues, norm_facts
        )
        all_violations.extend(iss_viols)
        all_supporting.extend(iss_sup)
        all_rejected.extend(iss_rej)

        # 3. Legal Role Compatibility
        evidence_role = self.role_checker.determine_evidence_role(doc_name, source_fn, section, text)
        role_score, role_status, role_viols, role_sup, role_rej = self.role_checker.check_role_compatibility(
            query, evidence_role, doc_name, section
        )
        all_violations.extend(role_viols)
        all_supporting.extend(role_sup)
        all_rejected.extend(role_rej)

        # 4. Temporal Compatibility
        temp_score, temp_status, temp_viols, temp_sup, temp_rej = self.temporal_checker.check_temporal_compatibility(
            query, doc_name, source_fn, facts
        )
        all_violations.extend(temp_viols)
        all_supporting.extend(temp_sup)
        all_rejected.extend(temp_rej)

        # 5. Special Law vs General Law Compatibility
        sg_score, sg_status, sg_viols, sg_sup, sg_rej = self.special_general_checker.check_special_general_compatibility(
            doc_name, source_fn, routing_decision
        )
        all_violations.extend(sg_viols)
        all_supporting.extend(sg_sup)
        all_rejected.extend(sg_rej)

        # Default relationship score (adjusted later in batch)
        rel_score = 1.0

        # Calculate composite score
        score_obj, comp_status = self.scorer.calculate_score(
            regime_score=regime_score,
            issue_score=issue_score,
            legal_role_score=role_score,
            temporal_score=temp_score,
            special_general_score=sg_score,
            relationship_score=rel_score,
            violations=all_violations,
        )

        statute_key = resolve_statute_key(doc_name, source_fn) or "UNKNOWN"

        reasoning = (
            f"Evaluated {statute_key} (Role: {evidence_role.value}, Temporal: {temp_status.value}). "
            f"Regime score: {regime_score:.2f}, Issue score: {issue_score:.2f}, Role score: {role_score:.2f}. "
            f"Composite score: {score_obj.total_score:.2f} -> Status: {comp_status.value}."
        )

        # Hard exclusion check (only when explicitly enabled)
        hard_excluded = False
        exclusion_reason = None
        if self.allow_hard_exclusion and score_obj.total_score < self.scorer.thresh_hard_exclusion:
            if any(v.severity in ["CRITICAL", "HIGH"] for v in all_violations):
                hard_excluded = True
                exclusion_reason = f"Score {score_obj.total_score:.2f} below threshold {self.scorer.thresh_hard_exclusion} with high violations."

        return CompatibilityDecision(
            chunk_id=chunk_id,
            document_name=doc_name,
            section=section,
            source_regime=statute_key,
            compatibility_score=score_obj.total_score,
            compatibility_status=comp_status,
            violations=all_violations,
            supporting_signals=all_supporting,
            rejected_signals=all_rejected,
            temporal_status=temp_status,
            legal_role=evidence_role,
            substantive_compatibility=role_score if evidence_role == LegalRole.SUBSTANTIVE else 1.0,
            procedural_compatibility=role_score if evidence_role == LegalRole.PROCEDURAL else 1.0,
            issue_compatibility=issue_score,
            regime_compatibility=regime_score,
            special_general_compatibility=sg_score,
            score_breakdown=score_obj,
            hard_excluded=hard_excluded,
            exclusion_reason=exclusion_reason,
            reasoning=reasoning,
        )

    def filter_and_rank_candidates(
        self,
        query: str,
        candidates: List[Any],
        routing_decision: Optional[RoutingDecision] = None,
        facts: Optional[ExtractedFacts] = None,
        top_k: int = 5,
        dimension_filter: Optional[str] = None,
    ) -> Tuple[List[Any], CompatibilityResult]:
        """Apply multi-dimensional evidence compatibility filtering and soft score adjustment.

        Args:
            query: User's legal question.
            candidates: Retrieved candidates (RetrievedChunk or RerankedChunk).
            routing_decision: Optional Phase 3 routing decision.
            facts: Optional extracted facts.
            top_k: Number of final candidates to retain.
            dimension_filter: Optional ablation filter:
                              - "regime_only" (Phase 4A)
                              - "regime_issue" (Phase 4B)
                              - "regime_issue_role" (Phase 4C)
                              - None / "full" (Phase 4D)

        Returns:
            Tuple of (re-ranked candidates, CompatibilityResult summary).
        """
        t0 = time.perf_counter()
        if not candidates:
            res = CompatibilityResult(
                query=query,
                total_candidates=0,
                compatible_count=0,
                partially_compatible_count=0,
                uncertain_count=0,
                incompatible_count=0,
                hard_excluded_count=0,
                execution_time_sec=0.0,
            )
            return [], res

        # Step 1: Evaluate individual chunk decisions
        decisions: List[CompatibilityDecision] = []
        for c in candidates:
            dec = self.evaluate_single_chunk(query, c, routing_decision, facts)

            # Apply ablation overrides if specified
            if dimension_filter == "regime_only":
                # Only regime dimension active; others neutral
                ab_score, ab_status = self.scorer.calculate_score(
                    regime_score=dec.regime_compatibility,
                    issue_score=1.0,
                    legal_role_score=1.0,
                    temporal_score=1.0,
                    special_general_score=1.0,
                    relationship_score=1.0,
                    violations=[v for v in dec.violations if v.dimension == "regime"],
                )
                dec.score_breakdown = ab_score
                dec.compatibility_score = ab_score.total_score
                dec.compatibility_status = ab_status

            elif dimension_filter == "regime_issue":
                # Regime and Issue active
                ab_score, ab_status = self.scorer.calculate_score(
                    regime_score=dec.regime_compatibility,
                    issue_score=dec.issue_compatibility,
                    legal_role_score=1.0,
                    temporal_score=1.0,
                    special_general_score=1.0,
                    relationship_score=1.0,
                    violations=[v for v in dec.violations if v.dimension in ["regime", "issue"]],
                )
                dec.score_breakdown = ab_score
                dec.compatibility_score = ab_score.total_score
                dec.compatibility_status = ab_status

            elif dimension_filter == "regime_issue_role":
                # Regime, Issue, and Role active
                ab_score, ab_status = self.scorer.calculate_score(
                    regime_score=dec.regime_compatibility,
                    issue_score=dec.issue_compatibility,
                    legal_role_score=dec.substantive_compatibility if dec.legal_role == LegalRole.SUBSTANTIVE else dec.procedural_compatibility,
                    temporal_score=1.0,
                    special_general_score=1.0,
                    relationship_score=1.0,
                    violations=[v for v in dec.violations if v.dimension in ["regime", "issue", "legal_role"]],
                )
                dec.score_breakdown = ab_score
                dec.compatibility_score = ab_score.total_score
                dec.compatibility_status = ab_status

            decisions.append(dec)

        # Step 2: Cross-chunk relationship analysis (for full or relationship-enabled mode)
        c_map = {getattr(c, "chunk_id", ""): getattr(c, "source_filename", "") for c in candidates}
        candidate_items = [
            {
                "chunk_id": d.chunk_id,
                "document_name": d.document_name,
                "source_filename": c_map.get(d.chunk_id, ""),
                "section": d.section,
                "legal_role": d.legal_role,
                "temporal_status": d.temporal_status,
            }
            for d in decisions
        ]

        relationships = []
        coherence_score = 1.0
        if dimension_filter in [None, "full"]:
            relationships, rel_chunk_scores, coherence_score = self.relationship_analyzer.analyze_relationships(candidate_items)
            for d in decisions:
                if d.chunk_id in rel_chunk_scores and d.score_breakdown:
                    r_adj = rel_chunk_scores[d.chunk_id]
                    d.score_breakdown.relationship_score = r_adj
                    # Recalculate soft multiplier with relationship synergy
                    d.score_breakdown.soft_multiplier = max(
                        self.scorer.min_multiplier,
                        min(self.scorer.max_multiplier, d.score_breakdown.soft_multiplier * r_adj),
                    )

        # Step 3: Soft Re-ranking of candidate pool
        dec_map = {d.chunk_id: d for d in decisions}
        scored_candidates: List[Tuple[Any, float]] = []

        for c in candidates:
            cid = getattr(c, "chunk_id", "")
            decision = dec_map.get(cid)
            orig_score = getattr(c, "relevance_score", 0.5)

            if decision and decision.hard_excluded:
                # Omit only if hard excluded under strict configuration
                continue

            multiplier = decision.score_breakdown.soft_multiplier if decision and decision.score_breakdown else 1.0
            adjusted_score = orig_score * multiplier
            scored_candidates.append((c, adjusted_score))

        # Sort descending by adjusted score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        final_candidates: List[Any] = []
        for rank, (cand, adj_score) in enumerate(scored_candidates[:top_k], start=1):
            # Update candidate relevance score and rank
            if hasattr(cand, "relevance_score"):
                cand.relevance_score = round(adj_score, 4)
            if hasattr(cand, "rank"):
                cand.rank = rank
            final_candidates.append(cand)

        exec_time = time.perf_counter() - t0

        # Build collection result
        comp_count = sum(1 for d in decisions if d.compatibility_status == CompatibilityStatus.COMPATIBLE)
        part_count = sum(1 for d in decisions if d.compatibility_status == CompatibilityStatus.PARTIALLY_COMPATIBLE)
        unc_count = sum(1 for d in decisions if d.compatibility_status == CompatibilityStatus.UNCERTAIN)
        incomp_count = sum(1 for d in decisions if d.compatibility_status == CompatibilityStatus.INCOMPATIBLE)
        hard_count = sum(1 for d in decisions if d.hard_excluded)

        comp_result = CompatibilityResult(
            query=query,
            total_candidates=len(candidates),
            compatible_count=comp_count,
            partially_compatible_count=part_count,
            uncertain_count=unc_count,
            incompatible_count=incomp_count,
            hard_excluded_count=hard_count,
            decisions=decisions,
            relationships=relationships,
            regime_coherence_score=coherence_score,
            execution_time_sec=exec_time,
        )

        return final_candidates, comp_result


_ENGINE_SINGLETON: Optional[EvidenceCompatibilityEngine] = None


def get_evidence_compatibility_engine(config_path: Optional[str] = None) -> EvidenceCompatibilityEngine:
    """Obtain shared singleton instance of EvidenceCompatibilityEngine."""
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None:
        _ENGINE_SINGLETON = EvidenceCompatibilityEngine(config_path=config_path)
    return _ENGINE_SINGLETON
