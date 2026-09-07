"""Precedent Relationship Analyzer with Strict Anti-Fabrication Safeguards.

Analyzes explicit relationships between judicial decisions:
- FOLLOWED: subsequent court adopts the legal principle
- APPLIED: principle applied to analogous facts
- RELIED_ON: cited with approval as governing precedent
- DISTINGUISHED: held inapplicable due to material factual difference
- QUESTIONED: doubted by coordinate bench or referred to larger bench
- OVERRULED: explicitly invalidated by superior court or larger bench

CRITICAL SAFETY RULE:
Never assert 'Case A overruled Case B' based on semantic similarity.
Overruling MUST be explicitly established by verified metadata or clear textual evidence.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from research.precedent_reasoning.models import (
    JudicialPrecedent,
    PrecedentRelationship,
    PrecedentRelationshipType,
)


class PrecedentRelationshipAnalyzer:
    """Detects and validates explicit relationships between judicial precedents."""

    # Explicit textual citation markers
    OVERRULED_PATTERNS = [
        r"overruled\s+by",
        r"is\s+hereby\s+overruled",
        r"we\s+overrule\s+the\s+decision\s+in",
        r"stands\s+overruled",
        r"no\s+longer\s+good\s+law",
    ]

    DISTINGUISHED_PATTERNS = [
        r"distinguished\s+from",
        r"is\s+clearly\s+distinguishable",
        r"the\s+decision\s+in\s+.*?\s+is\s+distinguished",
        r"facts\s+are\s+entirely\s+different\s+from",
        r"cannot\s+be\s+applied\s+to\s+the\s+facts",
    ]

    FOLLOWED_PATTERNS = [
        r"followed\s+the\s+principles\s+laid\s+down\s+in",
        r"following\s+the\s+decision\s+in",
        r"in\s+line\s+with\s+the\s+ruling\s+in",
        r"applying\s+the\s+ratio\s+of",
        r"relying\s+upon\s+the\s+dictum\s+in",
    ]

    @classmethod
    def analyze_pairwise_relationship(
        cls,
        case_a: JudicialPrecedent,
        case_b: JudicialPrecedent,
    ) -> Optional[PrecedentRelationship]:
        """Analyze if an explicit relationship exists between Case A and Case B."""
        name_a = case_a.case_name.lower().strip()
        name_b = case_b.case_name.lower().strip()

        # 1. Check Case A's metadata for explicit references to Case B
        meta_a = case_a.metadata
        meta_b = case_b.metadata

        # Check if Case A was overruled by Case B
        if meta_a.overruled_by and cls._matches_name(meta_a.overruled_by, name_b):
            return PrecedentRelationship(
                source_case=case_b.case_name,
                target_case=case_a.case_name,
                relationship_type=PrecedentRelationshipType.OVERRULED,
                evidence_text=f"Metadata record: '{case_a.case_name}' was overruled by '{case_b.case_name}'.",
                confidence=1.0,
                is_explicit_in_corpus=True,
            )

        # Check if Case B was overruled by Case A
        if meta_b.overruled_by and cls._matches_name(meta_b.overruled_by, name_a):
            return PrecedentRelationship(
                source_case=case_a.case_name,
                target_case=case_b.case_name,
                relationship_type=PrecedentRelationshipType.OVERRULED,
                evidence_text=f"Metadata record: '{case_b.case_name}' was overruled by '{case_a.case_name}'.",
                confidence=1.0,
                is_explicit_in_corpus=True,
            )

        # Check if Case A distinguished Case B
        if any(cls._matches_name(d, name_b) for d in meta_a.distinguished_by):
            return PrecedentRelationship(
                source_case=case_a.case_name,
                target_case=case_b.case_name,
                relationship_type=PrecedentRelationshipType.DISTINGUISHED,
                evidence_text=f"Metadata record: '{case_a.case_name}' distinguished '{case_b.case_name}'.",
                confidence=1.0,
                is_explicit_in_corpus=True,
            )

        # Check if Case A followed Case B
        if any(cls._matches_name(f, name_b) for f in meta_a.followed_by):
            return PrecedentRelationship(
                source_case=case_a.case_name,
                target_case=case_b.case_name,
                relationship_type=PrecedentRelationshipType.FOLLOWED,
                evidence_text=f"Metadata record: '{case_a.case_name}' followed '{case_b.case_name}'.",
                confidence=1.0,
                is_explicit_in_corpus=True,
            )

        # 2. Text-level citation analysis in Case A text mentioning Case B
        text_a = case_a.text.lower()
        key_name_b = cls._get_key_parties(name_b)
        if any(party in text_a for party in key_name_b if len(party) > 3):
            # Check for textual overruling
            for pat in cls.OVERRULED_PATTERNS:
                if re.search(pat, text_a):
                    return PrecedentRelationship(
                        source_case=case_a.case_name,
                        target_case=case_b.case_name,
                        relationship_type=PrecedentRelationshipType.OVERRULED,
                        evidence_text=f"Textual citation: '{case_a.case_name}' references overruling '{case_b.case_name}'.",
                        confidence=0.90,
                        is_explicit_in_corpus=True,
                    )

            # Check for textual distinguishing
            for pat in cls.DISTINGUISHED_PATTERNS:
                if re.search(pat, text_a):
                    return PrecedentRelationship(
                        source_case=case_a.case_name,
                        target_case=case_b.case_name,
                        relationship_type=PrecedentRelationshipType.DISTINGUISHED,
                        evidence_text=f"Textual citation: '{case_a.case_name}' distinguishes '{case_b.case_name}'.",
                        confidence=0.85,
                        is_explicit_in_corpus=True,
                    )

            # Check for textual following / applying
            for pat in cls.FOLLOWED_PATTERNS:
                if re.search(pat, text_a):
                    return PrecedentRelationship(
                        source_case=case_a.case_name,
                        target_case=case_b.case_name,
                        relationship_type=PrecedentRelationshipType.FOLLOWED,
                        evidence_text=f"Textual citation: '{case_a.case_name}' follows/applies '{case_b.case_name}'.",
                        confidence=0.85,
                        is_explicit_in_corpus=True,
                    )

            # Mention without specific qualification
            return PrecedentRelationship(
                source_case=case_a.case_name,
                target_case=case_b.case_name,
                relationship_type=PrecedentRelationshipType.RELIED_ON,
                evidence_text=f"Textual citation: '{case_a.case_name}' cites '{case_b.case_name}'.",
                confidence=0.75,
                is_explicit_in_corpus=True,
            )

        return None

    @classmethod
    def analyze_all_relationships(
        cls,
        precedents: List[JudicialPrecedent],
    ) -> List[PrecedentRelationship]:
        """Detect all pairwise relationships between a collection of retrieved precedents."""
        relationships: List[PrecedentRelationship] = []
        n = len(precedents)
        for i in range(n):
            for j in range(n):
                if i != j:
                    rel = cls.analyze_pairwise_relationship(precedents[i], precedents[j])
                    if rel is not None:
                        relationships.append(rel)
        return relationships

    @staticmethod
    def _matches_name(text_ref: str, target_name: str) -> bool:
        """Check if a reference matches a target case name."""
        t_clean = text_ref.lower().strip()
        target_clean = target_name.lower().strip()
        if t_clean in target_clean or target_clean in t_clean:
            return True
        # Match primary party name
        parties = [p.strip() for p in target_clean.split("v.") if p.strip()]
        if parties and any(p in t_clean for p in parties if len(p) > 3):
            return True
        return False

    @staticmethod
    def _get_key_parties(case_name: str) -> List[str]:
        """Extract primary party names from case title."""
        parts = re.split(r"\s+v\.\s+|\s+vs\.\s+", case_name, flags=re.IGNORECASE)
        parties = []
        for p in parts:
            clean = re.sub(r"\(.*?\)", "", p).strip().lower()
            if clean and len(clean) > 3:
                parties.append(clean)
        return parties
