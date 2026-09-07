"""Doctrinal Conflict Detector and Hierarchical Reconciliation Engine.

Identifies, reconciles, and reports conflicts between retrieved judicial decisions:
- Distinguishes genuine doctrinal conflict from factual distinctions
- Resolves conflicts using:
  1. Court Hierarchy (Supreme Court binding over High Courts)
  2. Bench Strength (Constitution Bench / Larger Bench controls Division Bench)
  3. Subsequent History (Later decision explicitly overruling earlier)
  4. Factual Distinctions (e.g. breach of promise from inception vs subsequent impossibility)
"""

from typing import List, Optional, Tuple

from research.precedent_reasoning.court_hierarchy import CourtHierarchyEngine
from research.precedent_reasoning.models import (
    ConflictStatus,
    CourtLevel,
    JudicialPrecedent,
    PrecedentConflict,
    PrecedentRelationship,
    PrecedentRelationshipType,
)


class PrecedentConflictDetector:
    """Evaluates whether retrieved precedents conflict doctrinally or can be reconciled."""

    @classmethod
    def detect_conflicts(
        cls,
        precedents: List[JudicialPrecedent],
        relationships: List[PrecedentRelationship],
    ) -> List[PrecedentConflict]:
        """Detect and evaluate conflicts across a set of retrieved precedents."""
        conflicts: List[PrecedentConflict] = []
        n = len(precedents)

        # Build relationship lookup: (src, tgt) -> relationship_type
        rel_map = {}
        for r in relationships:
            rel_map[(r.source_case.lower(), r.target_case.lower())] = r.relationship_type
            rel_map[(r.target_case.lower(), r.source_case.lower())] = r.relationship_type

        for i in range(n):
            for j in range(i + 1, n):
                case_a = precedents[i]
                case_b = precedents[j]

                # Check if cases share common topics or sections, or have an explicit relationship
                shared_secs = set(case_a.sections_referred) & set(case_b.sections_referred)
                shared_topics = set(case_a.topics) & set(case_b.topics)
                has_rel = (case_a.case_name.lower(), case_b.case_name.lower()) in rel_map

                if not shared_secs and not shared_topics and not has_rel:
                    # Dissimilar legal domains; no meaningful conflict
                    continue

                c_eval = cls._evaluate_pair_conflict(case_a, case_b, rel_map)
                if c_eval is not None:
                    conflicts.append(c_eval)

        return conflicts

    @classmethod
    def _evaluate_pair_conflict(
        cls,
        case_a: JudicialPrecedent,
        case_b: JudicialPrecedent,
        rel_map: dict,
    ) -> Optional[PrecedentConflict]:
        """Evaluate conflict between two specific precedents interpreting shared sections/topics."""
        name_a_l = case_a.case_name.lower()
        name_b_l = case_b.case_name.lower()

        rel_type = rel_map.get((name_a_l, name_b_l))

        # Case 1: Explicitly Overruled relationship
        if rel_type == PrecedentRelationshipType.OVERRULED:
            # Check which one is overruled
            overruled_target = case_b if case_a.metadata.overruled_by is None else case_a
            controlling = case_a if overruled_target == case_b else case_b
            return PrecedentConflict(
                case_a=case_a.case_name,
                case_b=case_b.case_name,
                legal_issue="Statutory Interpretation & Subsequent Authority",
                position_a=case_a.passage_type,
                position_b=case_b.passage_type,
                conflict_status=ConflictStatus.RESOLVED_BY_AUTHORITY,
                controlling_case=controlling.case_name,
                resolution_basis=f"Conflict resolved by judicial overruling: '{controlling.case_name}' overruled '{overruled_target.case_name}'.",
            )

        # Case 2: Explicitly Distinguished (Factual Distinction != Doctrinal Conflict)
        if rel_type == PrecedentRelationshipType.DISTINGUISHED:
            return PrecedentConflict(
                case_a=case_a.case_name,
                case_b=case_b.case_name,
                legal_issue="Application to Distinct Factual Matrices",
                position_a=f"Applicable to general principle in {case_a.case_name}",
                position_b=f"Distinguished on specific facts in {case_b.case_name}",
                conflict_status=ConflictStatus.NO_CONFLICT,
                controlling_case=None,
                resolution_basis="Harmonized by judicial distinction: legal difference explained by material factual distinction.",
                distinguishing_factors=[
                    f"Subsequent bench distinguished '{case_b.case_name}' from '{case_a.case_name}' on factual grounds."
                ],
            )

        # Case 3: Court Hierarchy Divergence (e.g. Supreme Court vs High Court)
        h_cmp = CourtHierarchyEngine.compare_hierarchy(case_a.court_level, case_b.court_level)
        if h_cmp != 0:
            higher = case_a if h_cmp > 0 else case_b
            lower = case_b if h_cmp > 0 else case_a
            return PrecedentConflict(
                case_a=case_a.case_name,
                case_b=case_b.case_name,
                legal_issue="Constitutional Court Hierarchy",
                position_a=case_a.court,
                position_b=case_b.court,
                conflict_status=ConflictStatus.RESOLVED_BY_AUTHORITY,
                controlling_case=higher.case_name,
                resolution_basis=(
                    f"Resolved by court hierarchy: {higher.court} ({higher.court_level.value}) "
                    f"takes constitutional precedence over {lower.court} ({lower.court_level.value}) under Article 141."
                ),
            )

        # Case 4: Coordinate Benches of Same Court (e.g. two SC decisions)
        if case_a.court_level == case_b.court_level and case_a.court_level in (CourtLevel.SUPREME_COURT, CourtLevel.HIGH_COURT):
            # Check bench strength
            weight_a = CourtHierarchyEngine.get_bench_multiplier(case_a.metadata.bench_strength)
            weight_b = CourtHierarchyEngine.get_bench_multiplier(case_b.metadata.bench_strength)

            if weight_a != weight_b:
                larger = case_a if weight_a > weight_b else case_b
                smaller = case_b if weight_a > weight_b else case_a
                return PrecedentConflict(
                    case_a=case_a.case_name,
                    case_b=case_b.case_name,
                    legal_issue="Bench Strength Precedence",
                    position_a=f"Bench: {case_a.metadata.bench_strength.value}",
                    position_b=f"Bench: {case_b.metadata.bench_strength.value}",
                    conflict_status=ConflictStatus.RESOLVED_BY_AUTHORITY,
                    controlling_case=larger.case_name,
                    resolution_basis=(
                        f"Resolved by bench strength: larger bench in '{larger.case_name}' "
                        f"({larger.metadata.bench_strength.value}) controls coordinate bench in '{smaller.case_name}'."
                    ),
                )

        return None
