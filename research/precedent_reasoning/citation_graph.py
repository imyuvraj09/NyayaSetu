"""In-Memory Citation and Authority Graph for Judicial Precedent Lineage Tracing.

Nodes: JudicialPrecedent records
Edges: PrecedentRelationship (FOLLOWED, APPLIED, RELIED_ON, DISTINGUISHED, OVERRULED)

Enables:
- Precedent lineage tracing
- Checking if a precedent has been overruled directly or by transitively binding decisions
- Finding supporting and distinguishing case networks
- Zero-fabrication: only records relationships backed by corpus evidence
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from research.precedent_reasoning.models import (
    JudicialPrecedent,
    PrecedentRelationship,
    PrecedentRelationshipType,
)


class PrecedentCitationGraph:
    """Directed graph representing inter-precedent citation and authority links."""

    def __init__(self) -> None:
        self.nodes: Dict[str, JudicialPrecedent] = {}  # case_name -> JudicialPrecedent
        self.out_edges: Dict[str, List[PrecedentRelationship]] = defaultdict(list)  # source -> list of relationships
        self.in_edges: Dict[str, List[PrecedentRelationship]] = defaultdict(list)  # target -> list of incoming relationships

    def add_precedent(self, precedent: JudicialPrecedent) -> None:
        """Add a precedent node to the graph."""
        self.nodes[precedent.case_name] = precedent

    def add_relationship(self, rel: PrecedentRelationship) -> None:
        """Add a directed relationship edge to the graph."""
        self.out_edges[rel.source_case].append(rel)
        self.in_edges[rel.target_case].append(rel)

    def is_overruled(self, case_name: str) -> Tuple[bool, Optional[str]]:
        """Check if a case has an incoming OVERRULED edge."""
        for rel in self.in_edges.get(case_name, []):
            if rel.relationship_type == PrecedentRelationshipType.OVERRULED:
                return True, rel.source_case
        return False, None

    def find_overruling_precedents(self, case_name: str) -> List[str]:
        """Return list of precedent names that overruled this case."""
        overrulers = []
        for rel in self.in_edges.get(case_name, []):
            if rel.relationship_type in (
                PrecedentRelationshipType.OVERRULED,
                PrecedentRelationshipType.PARTIALLY_OVERRULED,
            ):
                overrulers.append(rel.source_case)
        return overrulers

    def get_followed_cases(self, case_name: str) -> List[str]:
        """Return cases that this case followed."""
        return [
            rel.target_case
            for rel in self.out_edges.get(case_name, [])
            if rel.relationship_type in (
                PrecedentRelationshipType.FOLLOWED,
                PrecedentRelationshipType.APPLIED,
                PrecedentRelationshipType.RELIED_ON,
            )
        ]

    def get_distinguished_cases(self, case_name: str) -> List[str]:
        """Return cases distinguished by this case."""
        return [
            rel.target_case
            for rel in self.out_edges.get(case_name, [])
            if rel.relationship_type == PrecedentRelationshipType.DISTINGUISHED
        ]

    def trace_lineage(self, case_name: str, max_depth: int = 3) -> Dict[str, Any]:
        """Trace authority lineage forwards and backwards from a case."""
        visited: Set[str] = set()

        def _traverse_ancestors(curr: str, depth: int) -> List[Dict[str, Any]]:
            if depth > max_depth or curr in visited:
                return []
            visited.add(curr)
            ancestors = []
            for rel in self.out_edges.get(curr, []):
                ancestors.append({
                    "case": rel.target_case,
                    "relationship": rel.relationship_type.value,
                    "evidence": rel.evidence_text,
                    "sub_lineage": _traverse_ancestors(rel.target_case, depth + 1),
                })
            return ancestors

        return {
            "root_case": case_name,
            "is_overruled": self.is_overruled(case_name)[0],
            "overruled_by": self.is_overruled(case_name)[1],
            "lineage": _traverse_ancestors(case_name, 1),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary for audit and telemetry."""
        all_edges = []
        for src, rels in self.out_edges.items():
            for r in rels:
                all_edges.append(r.to_dict())

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(all_edges),
            "nodes": list(self.nodes.keys()),
            "edges": all_edges,
        }
