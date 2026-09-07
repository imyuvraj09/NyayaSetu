"""Cross-Chunk Evidence Relationship Analyzer for Multi-Statute Coherence.

Analyzes pairwise doctrinal and evidentiary relationships among candidate chunks:
- SUPPORTS
- COMPLEMENTS
- PROCEDURALLY_SUPPORTS (e.g., BNSS arrest powers supporting BNS substantive offense)
- EVIDENTIALLY_SUPPORTS (e.g., BSA § 63 certificate proving IT Act digital data)
- CONFLICTS
- TEMPORALLY_CONFLICTS (e.g., mixing repealed IPC with new BNS for same offense)
- DUPLICATES
- UNRELATED

Provides lightweight, deterministic, low-latency coherence scoring for the retrieved pool.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from research.evidence_compatibility.models import (
    EvidenceRelationship,
    EvidenceRelationshipType,
    LegalRole,
    TemporalStatus,
)
from research.evidence_compatibility.rules import (
    COHERENT_REGIME_BRIDGES,
    STATUTE_REGISTRY,
    resolve_statute_key,
)


class EvidenceRelationshipAnalyzer:
    """Detects doctrinal synergy and conflicts across retrieved evidence chunks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def analyze_relationships(
        self,
        candidate_items: List[Dict[str, Any]],
    ) -> Tuple[List[EvidenceRelationship], Dict[str, float], float]:
        """Analyze inter-chunk doctrinal relationships across candidate evidence items.

        Args:
            candidate_items: List of dicts with keys: chunk_id, document_name, section,
                             text, legal_role, temporal_status.

        Returns:
            Tuple of:
            - List of EvidenceRelationship instances
            - Dict of chunk_id -> relationship_score (bonus/penalty multiplier)
            - Collection-level regime_coherence_score (0.0 to 1.0)
        """
        relationships: List[EvidenceRelationship] = []
        chunk_scores: Dict[str, float] = {item["chunk_id"]: 1.0 for item in candidate_items}

        n = len(candidate_items)
        if n < 2:
            return relationships, chunk_scores, 1.0

        coherent_pair_count = 0
        total_pairs = 0

        for i in range(n):
            for j in range(i + 1, n):
                c1 = candidate_items[i]
                c2 = candidate_items[j]
                total_pairs += 1

                rel = self._evaluate_pair_relationship(c1, c2)
                if rel:
                    relationships.append(rel)

                    if rel.relationship_type in [
                        EvidenceRelationshipType.SUPPORTS,
                        EvidenceRelationshipType.COMPLEMENTS,
                        EvidenceRelationshipType.PROCEDURALLY_SUPPORTS,
                        EvidenceRelationshipType.EVIDENTIALLY_SUPPORTS,
                    ]:
                        coherent_pair_count += 1
                        # Small synergy boost for mutually supporting evidence
                        chunk_scores[c1["chunk_id"]] = min(1.05, chunk_scores[c1["chunk_id"]] + 0.02)
                        chunk_scores[c2["chunk_id"]] = min(1.05, chunk_scores[c2["chunk_id"]] + 0.02)

                    elif rel.relationship_type == EvidenceRelationshipType.TEMPORALLY_CONFLICTS:
                        # Conflict penalty for mixing superseded with current
                        chunk_scores[c1["chunk_id"]] = max(0.60, chunk_scores[c1["chunk_id"]] - 0.15)
                        chunk_scores[c2["chunk_id"]] = max(0.60, chunk_scores[c2["chunk_id"]] - 0.15)

                    elif rel.relationship_type == EvidenceRelationshipType.DUPLICATES:
                        # De-duplicate penalty on the lower-ranked chunk
                        chunk_scores[c2["chunk_id"]] = max(0.70, chunk_scores[c2["chunk_id"]] - 0.10)

        regime_coherence_score = round(coherent_pair_count / max(1, total_pairs), 4) if total_pairs > 0 else 1.0
        return relationships, chunk_scores, regime_coherence_score

    def _evaluate_pair_relationship(
        self,
        c1: Dict[str, Any],
        c2: Dict[str, Any],
    ) -> Optional[EvidenceRelationship]:
        """Classify relationship between two specific chunks."""
        id1, id2 = c1["chunk_id"], c2["chunk_id"]
        doc1, doc2 = c1.get("document_name", ""), c2.get("document_name", "")
        stat1 = resolve_statute_key(doc1, c1.get("source_filename", ""))
        stat2 = resolve_statute_key(doc2, c2.get("source_filename", ""))
        role1 = c1.get("legal_role", LegalRole.UNKNOWN)
        role2 = c2.get("legal_role", LegalRole.UNKNOWN)
        temp1 = c1.get("temporal_status", TemporalStatus.UNKNOWN)
        temp2 = c2.get("temporal_status", TemporalStatus.UNKNOWN)

        # 1. Temporal Conflict: e.g. BNS and IPC together, or BNSS and CrPC together
        if (stat1 == "BNS" and stat2 == "IPC") or (stat1 == "IPC" and stat2 == "BNS"):
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.TEMPORALLY_CONFLICTS,
                confidence=0.95,
                description="Temporal conflict: mixes modern Bharatiya Nyaya Sanhita with repealed Indian Penal Code",
            )
        if (stat1 == "BNSS" and stat2 == "CRPC") or (stat1 == "CRPC" and stat2 == "BNSS"):
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.TEMPORALLY_CONFLICTS,
                confidence=0.95,
                description="Temporal conflict: mixes modern BNSS with repealed CrPC",
            )
        if (stat1 == "BSA" and stat2 == "IEA") or (stat1 == "IEA" and stat2 == "BSA"):
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.TEMPORALLY_CONFLICTS,
                confidence=0.95,
                description="Temporal conflict: mixes modern Bharatiya Sakshya Adhiniyam with repealed Indian Evidence Act",
            )

        # 2. Textual Duplication
        sec1 = c1.get("section")
        sec2 = c2.get("section")
        if stat1 and stat2 and stat1 == stat2 and sec1 and sec2 and sec1 == sec2:
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.DUPLICATES,
                confidence=0.90,
                description=f"Duplicate section: both chunks represent {stat1} Section {sec1}",
            )

        # 3. Procedural Support Bridge: Substantive offense + Procedural provision
        if (role1 == LegalRole.SUBSTANTIVE and role2 == LegalRole.PROCEDURAL) or (
            role1 == LegalRole.PROCEDURAL and role2 == LegalRole.SUBSTANTIVE
        ):
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.PROCEDURALLY_SUPPORTS,
                confidence=0.85,
                description="Procedural bridge: pairs substantive legal offense with governing procedural mechanism",
            )

        # 4. Evidentiary Support Bridge: Substantive / Special offense + Evidence provision
        if (role1 in [LegalRole.SUBSTANTIVE, LegalRole.SPECIAL_LAW] and role2 == LegalRole.EVIDENTIARY) or (
            role1 == LegalRole.EVIDENTIARY and role2 in [LegalRole.SUBSTANTIVE, LegalRole.SPECIAL_LAW]
        ):
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.EVIDENTIALLY_SUPPORTS,
                confidence=0.85,
                description="Evidentiary bridge: statutory offense or record substantiated by governing rules of evidence",
            )

        # 5. Complementary provisions within same statute (e.g. BSA Section 62 and Section 63)
        if stat1 and stat2 and stat1 == stat2:
            return EvidenceRelationship(
                source_chunk_id=id1,
                target_chunk_id=id2,
                relationship_type=EvidenceRelationshipType.COMPLEMENTS,
                confidence=0.80,
                description=f"Complementary provisions within {stat1}",
            )

        # 6. Unrelated
        return None
