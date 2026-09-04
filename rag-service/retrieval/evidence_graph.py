"""
In-Memory Legal Evidence Graph for NyayaSetu.

Models the multi-authority evidence network connecting:
QUESTION -> FACET -> EVIDENCE NODE -> SOURCE PROVENANCE

Preserves strict authority distinctions between:
- STATUTE (Enactment, Section, Title, Page, Chunk)
- CASE_LAW (Case, Court, Citation, Date, Paragraph, Holding)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from schemas.case_law import EvidenceType
from schemas.retrieval import RerankedChunk


@dataclass
class EvidenceGraphNode:
    """Represents a node in the in-memory evidence graph."""
    node_id: str
    node_type: str  # "QUESTION", "FACET", "STATUTE", "CASE_LAW"
    evidence_type: EvidenceType
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "evidence_type": self.evidence_type.value,
            "title": self.title,
            "content": self.content[:300] if len(self.content) > 300 else self.content,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceGraphEdge:
    """Represents a directed authority relationship between two nodes."""
    source_id: str
    target_id: str
    relation: str  # "REQUIRES_FACET", "SUPPORTED_BY", "INTERPRETS_SECTION"
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
        }


class LegalEvidenceGraph:
    """In-memory structured graph object connecting questions, facets, and dual evidence."""

    def __init__(self, query: Optional[str] = None) -> None:
        self.nodes: Dict[str, EvidenceGraphNode] = {}
        self.edges: List[EvidenceGraphEdge] = []
        self.case_law_status: Optional[Any] = None
        if query:
            q_node = EvidenceGraphNode(
                node_id="q_root",
                node_type="QUESTION",
                evidence_type=EvidenceType.UNKNOWN,
                title="User Question",
                content=query,
            )
            self.add_node(q_node)

    def add_node(self, node: EvidenceGraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0) -> None:
        self.edges.append(EvidenceGraphEdge(source_id=source_id, target_id=target_id, relation=relation, weight=weight))

    def add_facet(self, facet: str, description: str = "") -> None:
        f_id = f"facet_{facet}"
        f_node = EvidenceGraphNode(
            node_id=f_id,
            node_type="FACET",
            evidence_type=EvidenceType.UNKNOWN,
            title=facet,
            content=description or f"Requested legal facet: {facet}",
        )
        self.add_node(f_node)
        if "q_root" in self.nodes:
            self.add_edge("q_root", f_id, "REQUIRES_FACET")

    def add_case_evidence(
        self,
        chunk_id: str,
        case_id: str,
        case_name: str,
        paragraph: str,
        text: str,
        facet: Optional[str] = None,
        weight: float = 1.0,
    ) -> None:
        c_id = f"caselaw_{chunk_id}"
        c_node = EvidenceGraphNode(
            node_id=c_id,
            node_type="CASE_LAW",
            evidence_type=EvidenceType.CASE_LAW,
            title=f"{case_name} [{paragraph}]",
            content=text,
            metadata={"case_id": case_id, "case_name": case_name, "paragraph": paragraph},
        )
        self.add_node(c_node)
        if "q_root" in self.nodes:
            self.add_edge("q_root", c_id, "JUDICIAL_PRECEDENT", weight=weight)
        if facet:
            f_id = f"facet_{facet}"
            if f_id in self.nodes:
                self.add_edge(f_id, c_id, "SUPPORTED_BY", weight=weight)

    def build_from_retrieval(
        self,
        query: str,
        requested_facets: List[str],
        statutory_chunks: List[RerankedChunk],
        case_law_chunks: List[RerankedChunk],
    ) -> "LegalEvidenceGraph":
        """Construct graph populated with question, facets, statutory provisions, and case precedents."""
        # 1. Root Question Node
        q_node = EvidenceGraphNode(
            node_id="q_root",
            node_type="QUESTION",
            evidence_type=EvidenceType.UNKNOWN,
            title="User Question",
            content=query,
        )
        self.add_node(q_node)

        # 2. Facet Nodes
        for facet in requested_facets:
            f_id = f"facet_{facet}"
            f_node = EvidenceGraphNode(
                node_id=f_id,
                node_type="FACET",
                evidence_type=EvidenceType.UNKNOWN,
                title=facet,
                content=f"Requested legal facet: {facet}",
            )
            self.add_node(f_node)
            self.add_edge("q_root", f_id, "REQUIRES_FACET")

        # 3. Statutory Evidence Nodes
        for idx, sc in enumerate(statutory_chunks, start=1):
            s_id = f"statute_{sc.chunk_id}"
            sec_label = f"{sc.document_name} Section {sc.section_number}" if sc.section_number else sc.document_name
            s_node = EvidenceGraphNode(
                node_id=s_id,
                node_type="STATUTE",
                evidence_type=EvidenceType.STATUTE,
                title=sec_label,
                content=sc.text,
                metadata={
                    "act": sc.document_name,
                    "section": sc.section_number,
                    "title": sc.section_title,
                    "pages": sc.page_numbers,
                    "chunk_id": sc.chunk_id,
                    "reranker_score": sc.reranker_score,
                },
            )
            self.add_node(s_node)
            self.add_edge("q_root", s_id, "STATUTORY_AUTHORITY", weight=sc.reranker_score)

        # 4. Case-Law Evidence Nodes
        for idx, cl in enumerate(case_law_chunks, start=1):
            c_id = f"caselaw_{cl.chunk_id}"
            cl_meta = cl.metadata or {}
            c_node = EvidenceGraphNode(
                node_id=c_id,
                node_type="CASE_LAW",
                evidence_type=EvidenceType.CASE_LAW,
                title=f"{cl.case_name} ({cl.citation}) [Para {cl.paragraph_number}]",
                content=cl.text,
                metadata={
                    "case_name": cl.case_name,
                    "court": cl.court,
                    "citation": cl.citation,
                    "date": cl.judgment_date,
                    "paragraph": cl.paragraph_number,
                    "chunk_id": cl.chunk_id,
                    "reranker_score": cl.reranker_score,
                    "is_holding": cl_meta.get("is_holding_or_ratio", False),
                },
            )
            self.add_node(c_node)
            self.add_edge("q_root", c_id, "JUDICIAL_PRECEDENT", weight=cl.reranker_score)

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire evidence graph to dictionary structure."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "summary": self.get_summary(),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Return structural summary of the evidence graph."""
        statute_count = sum(1 for n in self.nodes.values() if n.node_type == "STATUTE")
        caselaw_count = sum(1 for n in self.nodes.values() if n.node_type == "CASE_LAW")
        facet_count = sum(1 for n in self.nodes.values() if n.node_type == "FACET")

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "statute_nodes": statute_count,
            "case_law_nodes": caselaw_count,
            "facet_nodes": facet_count,
            "has_both_authorities": (statute_count > 0 and caselaw_count > 0),
        }

