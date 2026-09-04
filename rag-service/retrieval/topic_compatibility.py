"""
Topic Compatibility & Evidence Budgeting Layer for NyayaSetu Legal Assistant.

Implements question-specific legal-topic relevance matching:
1. Topic Compatibility Tagging: DIRECT, RELATED, BACKGROUND, IRRELEVANT
2. Strict Incompatibility Filtering: Excludes cases/statutes topically orthogonal to the primary issue
3. Evidence Budgeting: Caps context to 2–5 highly relevant, verified sources
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


class TopicCompatibility(str, Enum):
    DIRECT = "DIRECT"
    RELATED = "RELATED"
    BACKGROUND = "BACKGROUND"
    IRRELEVANT = "IRRELEVANT"


class TopicCompatibilityEngine:
    """Evaluates chunk topic compatibility against query primary issue and enforces evidence budgets."""

    @staticmethod
    def evaluate_compatibility(
        chunk: Any,
        query_analysis: Any,
    ) -> Tuple[TopicCompatibility, str]:
        """Classify a retrieved chunk's compatibility with the user's primary legal issue."""
        if not query_analysis:
            return TopicCompatibility.DIRECT, "Default direct compatibility"

        primary_issue = getattr(query_analysis, "primary_issue", "") or ""
        offence = getattr(query_analysis, "offence", None)
        excluded_topics = getattr(query_analysis, "excluded_topics", []) or []
        topic_keywords = getattr(query_analysis, "topic_keywords", []) or []
        requested_info = getattr(query_analysis, "requested_information", []) or []

        # Extract chunk properties
        is_case_law = getattr(chunk, "evidence_type", "") == "CASE_LAW" or (
            isinstance(getattr(chunk, "metadata", None), dict)
            and chunk.metadata.get("evidence_type") == "CASE_LAW"
        )
        chunk_text = getattr(chunk, "text", "") or ""
        lower_text = chunk_text.lower()
        chunk_meta = getattr(chunk, "metadata", {}) or {}
        chunk_topics = [t.lower() for t in chunk_meta.get("topics", [])]

        sec_num = str(getattr(chunk, "section_number", "") or chunk_meta.get("section_number", "")).strip()
        sec_title = str(getattr(chunk, "section_title", "") or chunk_meta.get("section_title", "")).lower()
        case_name = str(getattr(chunk, "case_name", "") or chunk_meta.get("case_name", "")).lower()

        # =====================================================================
        # 1. CASE-LAW TOPIC COMPATIBILITY
        # =====================================================================
        if is_case_law:
            # Rule 1A: Check if case is topically excluded by query analysis
            for ex in excluded_topics:
                ex_l = ex.lower()
                # Check topics array
                if any(ex_l in t for t in chunk_topics):
                    return (
                        TopicCompatibility.IRRELEVANT,
                        f"Case '{case_name}' is tagged with excluded topic '{ex}'.",
                    )
                # Check case name for distinct excluded subjects (e.g. Anurag Soni / Naim Ahamed are promise-to-marry)
                if ex_l in ("consent", "promise to marry", "rape"):
                    if any(c in case_name for c in ["anurag soni", "naim ahamed"]):
                        return (
                            TopicCompatibility.IRRELEVANT,
                            f"Case '{case_name}' addresses promise-to-marry/consent, which is excluded for primary issue '{primary_issue}'.",
                        )

            # Rule 1B: Primary Issue Match for Circumstantial Evidence
            if primary_issue == "circumstantial_evidence":
                ce_terms = [
                    "circumstantial evidence",
                    "chain of circumstances",
                    "panchsheel",
                    "five golden principles",
                    "standard of proof",
                    "conclusively established",
                    "hypothesis of innocence",
                ]
                if any(t in lower_text or any(t in ct for ct in chunk_topics) for t in ce_terms):
                    return (
                        TopicCompatibility.DIRECT,
                        "Direct judicial authority on circumstantial evidence standards and tests.",
                    )
                # If case does not discuss circumstantial evidence, mark IRRELEVANT
                return (
                    TopicCompatibility.IRRELEVANT,
                    "Case law does not discuss circumstantial evidence principles or judicial tests.",
                )

            # Rule 1C: Primary Issue Match for Consent & Promise to Marry
            if primary_issue == "consent_and_promise_to_marry":
                consent_terms = [
                    "promise to marry",
                    "misconception of fact",
                    "consent",
                    "voluntary",
                    "rape",
                    "section 375",
                    "section 63",
                    "false promise",
                ]
                if any(t in lower_text or any(t in ct for ct in chunk_topics) for t in consent_terms):
                    # But exclude circumstantial evidence cases
                    if "circumstantial evidence" in lower_text or any("circumstantial" in ct for ct in chunk_topics):
                        return (
                            TopicCompatibility.IRRELEVANT,
                            "Circumstantial evidence case is irrelevant to consent / promise-to-marry inquiry.",
                        )
                    return (
                        TopicCompatibility.DIRECT,
                        "Direct judicial authority on consent and promise to marry.",
                    )
                return (
                    TopicCompatibility.IRRELEVANT,
                    "Case does not address consent or promise to marry.",
                )

            # General Case Law: match topic keywords
            if any(tk in lower_text for tk in topic_keywords):
                return TopicCompatibility.DIRECT, "Passage addresses query legal keywords directly."

            return TopicCompatibility.RELATED, "General judicial precedent."

        # =====================================================================
        # 2. STATUTORY PROVISION COMPATIBILITY
        # =====================================================================
        # Rule 2A: Exclude orthogonal sections
        # BNS Section 108: Abetment of suicide
        if "108" in sec_num or "abetment of suicide" in sec_title or "abetment of suicide" in lower_text[:100]:
            if offence == "murder" or primary_issue == "circumstantial_evidence":
                return (
                    TopicCompatibility.IRRELEVANT,
                    "Section 108 (Abetment of suicide) is unrelated to murder / circumstantial evidence.",
                )

        # Check section against excluded topics
        for ex in excluded_topics:
            if ex.lower() in sec_title:
                return (
                    TopicCompatibility.IRRELEVANT,
                    f"Statutory section '{sec_title}' falls into excluded topic '{ex}'.",
                )

        # Rule 2B: Substantive murder offence provisions (BNS 101, 103)
        if primary_issue == "circumstantial_evidence":
            # For circumstantial evidence query, substantive definition is RELATED context
            if "101" in sec_num or "murder" in sec_title:
                if "punishment" not in sec_title and "103" not in sec_num:
                    return (
                        TopicCompatibility.RELATED,
                        "BNS Section 101 defines murder, providing necessary substantive context.",
                    )

            # Section 103: Punishment for murder
            if "103" in sec_num or "punishment for murder" in sec_title:
                if any(r in requested_info for r in ["punishment", "penalty"]):
                    return (
                        TopicCompatibility.DIRECT,
                        "Punishment provision explicitly requested by query.",
                    )
                # If punishment not requested, tag as BACKGROUND so it doesn't displace evidence
                return (
                    TopicCompatibility.BACKGROUND,
                    "Punishment provision (Section 103) is background information when query asks about evidentiary conviction standard.",
                )

        # Offence definition match
        if offence and offence in sec_title:
            return TopicCompatibility.DIRECT, f"Direct statutory provision for offence '{offence}'."

        return TopicCompatibility.RELATED, "Relevant statutory context."

    def filter_and_budget(
        self,
        statutory_chunks: List[Any],
        case_chunks: List[Any],
        query_analysis: Any,
        min_sources: int = 2,
        max_sources: int = 5,
    ) -> List[Any]:
        """Filter out IRRELEVANT sources and enforce evidence budget of 2–5 high-quality sources."""
        all_candidates = statutory_chunks + case_chunks
        direct_chunks: List[Any] = []
        related_chunks: List[Any] = []
        background_chunks: List[Any] = []

        for chunk in all_candidates:
            compat, reason = self.evaluate_compatibility(chunk, query_analysis)
            # Store compatibility attribute
            setattr(chunk, "topic_compatibility", compat.value)
            if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
                chunk.metadata["topic_compatibility"] = compat.value
                chunk.metadata["compatibility_reason"] = reason

            if compat == TopicCompatibility.DIRECT:
                direct_chunks.append(chunk)
            elif compat == TopicCompatibility.RELATED:
                related_chunks.append(chunk)
            elif compat == TopicCompatibility.BACKGROUND:
                background_chunks.append(chunk)
            elif compat == TopicCompatibility.IRRELEVANT:
                sec_or_case = getattr(chunk, "case_name", "") or getattr(chunk, "section_number", "") or getattr(chunk, "chunk_id", "")
                logger.info("Filtered IRRELEVANT source '%s': %s", sec_or_case, reason)

        # Sort within categories by score descending
        def get_score(c: Any) -> float:
            return float(getattr(c, "reranker_score", getattr(c, "similarity_score", 0.0)))

        direct_chunks.sort(key=get_score, reverse=True)
        related_chunks.sort(key=get_score, reverse=True)
        background_chunks.sort(key=get_score, reverse=True)

        selected: List[Any] = []

        # 1. Add DIRECT sources first (up to max_sources)
        selected.extend(direct_chunks[:max_sources])

        # 2. If below max_sources, fill with necessary RELATED sources
        remaining_budget = max_sources - len(selected)
        if remaining_budget > 0:
            selected.extend(related_chunks[:remaining_budget])

        # 3. Only if below min_sources, pull from BACKGROUND
        if len(selected) < min_sources:
            remaining_budget = min_sources - len(selected)
            selected.extend(background_chunks[:remaining_budget])

        logger.info(
            "Evidence budgeting complete: direct=%d, related=%d, background=%d -> retained %d sources (budget: %d-%d).",
            len(direct_chunks),
            len(related_chunks),
            len(background_chunks),
            len(selected),
            min_sources,
            max_sources,
        )

        return selected
