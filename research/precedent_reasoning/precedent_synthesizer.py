"""Structured Precedent Synthesis Layer for Legal Context Building.

Organizes judicial precedents into structured, explainable tiers:
1. Controlling Authority (Supreme Court ratio/holding under Article 141)
2. Supporting Authorities (Consistent rulings or applied principles)
3. Persuasive Authorities (High Courts outside primary jurisdiction, tribunals)
4. Distinguishable / Conflicting Decisions (with explicit resolution basis)
5. Unknown Authority Precedents (unverified metadata preserved transparently)

Ensures downstream LLMs receive clearly labeled, non-hallucinatory judicial context.
"""

from typing import Dict, List

from research.precedent_reasoning.models import (
    AuthorityAssessment,
    AuthorityStatus,
    ConflictStatus,
    JudicialPrecedent,
    PrecedentConflict,
    PrecedentRelationship,
    PrecedentRelationshipType,
)


class PrecedentSynthesizer:
    """Categorizes precedents and formats structured context for generation."""

    @classmethod
    def categorize_precedents(
        cls,
        precedents: List[JudicialPrecedent],
        authority_assessments: Dict[str, AuthorityAssessment],
        conflicts: List[PrecedentConflict],
        relationships: List[PrecedentRelationship],
    ) -> Dict[str, List[JudicialPrecedent]]:
        """Group precedents into controlling, supporting, persuasive, conflicting, and unknown tiers."""
        controlling: List[JudicialPrecedent] = []
        supporting: List[JudicialPrecedent] = []
        persuasive: List[JudicialPrecedent] = []
        conflicting: List[JudicialPrecedent] = []
        unknown_tier: List[JudicialPrecedent] = []

        # Find which cases are involved in conflicts
        conflict_case_names = set()
        for c in conflicts:
            if c.conflict_status in (ConflictStatus.POTENTIAL_CONFLICT, ConflictStatus.RESOLVED_BY_AUTHORITY):
                conflict_case_names.add(c.case_a)
                conflict_case_names.add(c.case_b)

        for p in precedents:
            auth = authority_assessments.get(p.chunk_id)
            if auth is None or auth.authority_status == AuthorityStatus.UNKNOWN:
                unknown_tier.append(p)
                continue

            if p.case_name in conflict_case_names:
                conflicting.append(p)
                continue

            if auth.authority_status == AuthorityStatus.BINDING:
                controlling.append(p)
            elif auth.authority_status == AuthorityStatus.HIGHLY_PERSUASIVE:
                supporting.append(p)
            else:
                persuasive.append(p)

        return {
            "controlling": controlling,
            "supporting": supporting,
            "persuasive": persuasive,
            "conflicting": conflicting,
            "unknown": unknown_tier,
        }

    @classmethod
    def format_precedent_context_block(
        cls,
        categorized: Dict[str, List[JudicialPrecedent]],
        conflicts: List[PrecedentConflict],
    ) -> str:
        """Format categorized precedents into a clear, structured prompt-ready context block."""
        lines = ["### Judicial Precedents & Authoritative Case Law"]

        # 1. Controlling Precedents
        if categorized.get("controlling"):
            lines.append("\n#### Controlling / Binding Judicial Authorities (Article 141, Constitution of India):")
            for p in categorized["controlling"]:
                lines.append(f"- **{p.case_name}** ({p.citation}) — {p.court}")
                lines.append(f"  *Date*: {p.judgment_date} | *Role*: {p.passage_type}")
                lines.append(f"  *Judicial Principle*: \"{p.text.strip()}\"")

        # 2. Supporting Precedents
        if categorized.get("supporting"):
            lines.append("\n#### Supporting Authorities & Applied Principles:")
            for p in categorized["supporting"]:
                lines.append(f"- **{p.case_name}** ({p.citation}) — {p.court}")
                lines.append(f"  *Judicial Principle*: \"{p.text.strip()}\"")

        # 3. Persuasive Precedents
        if categorized.get("persuasive"):
            lines.append("\n#### Persuasive Authorities:")
            for p in categorized["persuasive"]:
                lines.append(f"- **{p.case_name}** ({p.citation}) — {p.court} (*Persuasive Value*)")
                lines.append(f"  *Excerpt*: \"{p.text.strip()}\"")

        # 4. Conflicting or Distinguishable Decisions
        if conflicts or categorized.get("conflicting"):
            lines.append("\n#### Precedent Relationships & Doctrinal Harmonization:")
            for c in conflicts:
                lines.append(f"- **{c.case_a}** vs **{c.case_b}** [{c.conflict_status.value}]:")
                if c.resolution_basis:
                    lines.append(f"  *Reconciliation*: {c.resolution_basis}")
                for df in c.distinguishing_factors:
                    lines.append(f"  *Factual Distinction*: {df}")

        # 5. Unknown Metadata Precedents
        if categorized.get("unknown"):
            lines.append("\n#### Unverified Precedents (Court Metadata Incomplete):")
            for p in categorized["unknown"]:
                lines.append(f"- **{p.case_name}** (*Authority: UNKNOWN*): \"{p.text.strip()}\"")

        return "\n".join(lines)
