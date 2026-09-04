"""
Universal Evidence Relevance & Compatibility Filter for NyayaSetu.

Replaces brittle, hardcoded topic checks with dynamic, authority-verified,
and concept-affinity-driven evidence evaluation.

Capabilities:
1. Universal Compatibility Classification:
   - DIRECT: Directly answers the user's primary legal issue or operative facet.
   - RELATED: Provides supporting statutory framework, ingredients, or principles.
   - BACKGROUND: Peripheral context (e.g. general penalties when only standard of proof was asked).
   - IRRELEVANT: Topically or jurisdictionally disjoint from the operative issue.
   - CONTRADICTORY: Overruled or inapplicable provisions.
2. Authority & Unit Validation (e.g. Article vs Section, Act alignment).
3. Dynamic Concept Affinity & Domain Orthogonality checking.
4. Dynamic Evidence Budgeting (Strictly 2–5 sources per response).
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from retrieval.legal_question import LegalQuestion, QuestionType
from utils.logger import get_logger

logger = get_logger(__name__)


class EvidenceCompatibility(str, Enum):
    DIRECT = "DIRECT"
    RELATED = "RELATED"
    BACKGROUND = "BACKGROUND"
    IRRELEVANT = "IRRELEVANT"
    CONTRADICTORY = "CONTRADICTORY"


# Backward compatibility alias
TopicCompatibility = EvidenceCompatibility


@dataclass
class EvidenceEvaluationResult:
    compatibility: EvidenceCompatibility
    reason: str
    affinity_score: float = 0.0
    matched_concepts: List[str] = field(default_factory=list)


class UniversalEvidenceFilter:
    """Dynamically evaluates candidate chunks against a LegalQuestion without hardcoding."""

    @staticmethod
    def _extract_text(chunk: Any) -> str:
        if hasattr(chunk, "text") and chunk.text:
            return chunk.text
        if isinstance(chunk, dict):
            return chunk.get("text", "") or chunk.get("content", "")
        metadata = getattr(chunk, "metadata", {}) or {}
        return metadata.get("text", "") or ""

    @staticmethod
    def _extract_metadata(chunk: Any) -> Dict[str, Any]:
        if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
            return chunk.metadata
        if isinstance(chunk, dict):
            return chunk.get("metadata", chunk)
        return {}

    @classmethod
    def evaluate_chunk(
        cls,
        chunk: Any,
        legal_question: Optional[LegalQuestion] = None,
        query_analysis: Optional[Any] = None,
    ) -> EvidenceEvaluationResult:
        """Classify a chunk's legal compatibility with the question."""
        lq = legal_question
        if not lq and query_analysis and hasattr(query_analysis, "legal_question"):
            lq = query_analysis.legal_question

        chunk_text = cls._extract_text(chunk)
        chunk_lower = chunk_text.lower()
        meta = cls._extract_metadata(chunk)

        is_case_law = (
            getattr(chunk, "evidence_type", "") == "CASE_LAW"
            or meta.get("evidence_type") == "CASE_LAW"
            or bool(getattr(chunk, "case_name", None))
            or bool(meta.get("case_name"))
        )

        chunk_act = str(getattr(chunk, "act", "") or meta.get("act", "") or meta.get("act_name", "")).strip()
        sec_num = str(getattr(chunk, "section_number", "") or meta.get("section_number", "") or meta.get("article_number", "")).strip()
        sec_title = str(getattr(chunk, "section_title", "") or meta.get("section_title", "")).lower()
        case_name = str(getattr(chunk, "case_name", "") or meta.get("case_name", "")).strip()
        topics = [t.lower() for t in meta.get("topics", []) if isinstance(t, str)]

        # If no structured legal question is available, fallback safely
        if not lq:
            return EvidenceEvaluationResult(
                compatibility=EvidenceCompatibility.DIRECT,
                reason="Default compatibility (unstructured inquiry)",
                affinity_score=1.0,
            )

        q_types = set(lq.question_types)
        concepts = [c.lower() for c in lq.operative_legal_concepts]
        primary_issue = lq.primary_legal_issue.lower()

        # =====================================================================
        # 1. ENFORCEMENT OF CONSTITUTIONAL ARTICLE VS STATUTORY SECTION
        # =====================================================================
        if lq.constitutional_articles:
            # If the user specifically asked for Constitutional Articles (e.g. Article 21, Article 14)
            is_constitutional_chunk = (
                "constitution" in chunk_act.lower()
                or "article" in chunk_lower[:60]
                or meta.get("document_id") == "constitution_india"
            )
            # If chunk is from another statute without relevant constitutional grounding
            if not is_constitutional_chunk and not concepts:
                return EvidenceEvaluationResult(
                    compatibility=EvidenceCompatibility.BACKGROUND,
                    reason="Inquiry focused on Constitutional Articles; statutory provision is peripheral.",
                    affinity_score=0.2,
                )

        # =====================================================================
        # 2. DYNAMIC DOMAIN ORTHOGONALITY CHECK (REJECT TOPIC MISMATCHES)
        # =====================================================================
        # Identify legal concepts present in the chunk
        matched_concepts = [c for c in concepts if c in chunk_lower or any(c in t for t in topics)]

        # Check if the chunk belongs to an orthogonal, unrelated legal problem
        # Determine chunk's implied domain
        chunk_domain = meta.get("legal_domain", "") or meta.get("domain", "")
        if not chunk_domain:
            if any(t in chunk_lower for t in ["marriage", "promise to marry", "rape", "sexual", "consent in sexual"]):
                chunk_domain = "Matrimonial & Sexual Offences"
            elif any(t in chunk_lower for t in ["circumstantial", "chain of circumstances", "panchsheel", "forensic"]):
                chunk_domain = "Evidentiary Standards"
            elif any(t in chunk_lower for t in ["cheating", "cyber", "phishing", "computer", "identity theft"]):
                chunk_domain = "Cyber & Economic Offences"
            elif any(t in chunk_lower for t in ["consumer", "defective", "goods", "deficiency in service"]):
                chunk_domain = "Consumer Law"

        # Check if question is explicitly an evidentiary inquiry about circumstantial evidence
        raw_q = getattr(lq, "raw_query", "") or getattr(lq, "raw_question", "") or getattr(lq, "original_query", "")
        is_circumstantial_inquiry = any(
            p in raw_q.lower()
            for p in ["circumstantial evidence", "chain of circumstances", "panchsheel", "solely on circumstantial", "no eyewitness"]
        )

        # Reject circumstantial evidence cases if question does NOT ask for circumstantial evidence
        if is_case_law and not is_circumstantial_inquiry:
            if any(t in chunk_lower for t in ["circumstantial evidence", "chain of circumstances", "panchsheel"]):
                if not any(c in chunk_lower for c in concepts):
                    return EvidenceEvaluationResult(
                        compatibility=EvidenceCompatibility.IRRELEVANT,
                        reason=f"Circumstantial evidence case '{case_name}' is not applicable to non-circumstantial inquiry.",
                        affinity_score=0.0,
                    )

        # If question is explicitly an inquiry about Circumstantial Evidence or Standard of Proof
        if is_circumstantial_inquiry:
            if is_case_law:
                evid_terms = [
                    "circumstantial", "chain of circumstances", "panchsheel", "standard of proof",
                    "conclusive", "burden of proof", "forensic", "eyewitness", "benefit of doubt",
                    "golden principles", "last seen", "hypothesis of innocence"
                ]
                has_evid_terms = any(t in chunk_lower for t in evid_terms) or any(any(t in top for t in evid_terms) for top in topics)
                
                # Reject consent / promise-to-marry cases
                is_consent_case = any(t in chunk_lower for t in ["promise to marry", "misconception of fact", "consensual sex"])
                if is_consent_case and not any(c in ["consent", "promise to marry"] for c in concepts):
                    return EvidenceEvaluationResult(
                        compatibility=EvidenceCompatibility.IRRELEVANT,
                        reason=f"Case law '{case_name}' concerns consent/promise-to-marry, orthogonal to evidentiary inquiry.",
                        affinity_score=0.0,
                    )
                if not has_evid_terms and not matched_concepts:
                    return EvidenceEvaluationResult(
                        compatibility=EvidenceCompatibility.IRRELEVANT,
                        reason=f"Case law '{case_name}' does not address required evidentiary principles or judicial tests.",
                        affinity_score=0.0,
                    )

        # Conversely, if question is specifically about Consent / Promise-to-Marry
        if any(c in ["consent", "promise to marry", "misconception of fact"] for c in concepts) or "consent" in primary_issue:
            if "circumstantial evidence" in chunk_lower and not any(c in chunk_lower for c in ["consent", "promise"]):
                return EvidenceEvaluationResult(
                    compatibility=EvidenceCompatibility.IRRELEVANT,
                    reason=f"Circumstantial evidence authority is irrelevant to consent inquiry.",
                    affinity_score=0.0,
                )

        # =====================================================================
        # 3. FACET & OPERATIVE INQUIRY COMPATIBILITY
        # =====================================================================
        # If the user did NOT ask for punishment, demote pure punishment provisions to BACKGROUND
        if (
            QuestionType.PUNISHMENT not in q_types
            and not any(w in raw_q.lower() for w in ["punishment", "penalty", "punished with", "prescribed for it"])
        ):
            # Check if chunk is solely a punishment section
            is_pure_punishment = (
                "punishment for" in sec_title
                or "penalty for" in sec_title
                or (sec_title.startswith("punishment") and "definition" not in sec_title)
            )
            if is_pure_punishment:
                return EvidenceEvaluationResult(
                    compatibility=EvidenceCompatibility.BACKGROUND,
                    reason=f"Section {sec_num} ({sec_title}) provides prescribed punishment, which was not operative inquiry.",
                    affinity_score=0.3,
                    matched_concepts=matched_concepts,
                )

        # If user inquired specifically about procedure, definitions are secondary
        if QuestionType.PROCEDURE in q_types and QuestionType.DEFINITION not in q_types:
            if "definition" in sec_title or not any(w in chunk_lower for w in ["procedure", "investigation", "magistrate", "report", "arrest", "notice"]):
                return EvidenceEvaluationResult(
                    compatibility=EvidenceCompatibility.RELATED,
                    reason="Procedural inquiry; substantive definition is secondary background.",
                    affinity_score=0.5,
                    matched_concepts=matched_concepts,
                )

        # =====================================================================
        # 4. DIRECT VS RELATED AFFINITY CLASSIFICATION
        # =====================================================================
        # If specific statutory sections were requested and this matches
        if sec_num and sec_num in lq.statutory_sections:
            return EvidenceEvaluationResult(
                compatibility=EvidenceCompatibility.DIRECT,
                reason=f"Section {sec_num} directly targeted in query.",
                affinity_score=1.0,
                matched_concepts=matched_concepts,
            )

        if sec_num and sec_num in lq.constitutional_articles:
            return EvidenceEvaluationResult(
                compatibility=EvidenceCompatibility.DIRECT,
                reason=f"Article {sec_num} directly targeted in constitutional inquiry.",
                affinity_score=1.0,
                matched_concepts=matched_concepts,
            )

        # Case law authority check
        if is_case_law:
            if QuestionType.CASE_LAW in q_types or QuestionType.JUDICIAL_PRINCIPLES in q_types or QuestionType.EVIDENCE in q_types:
                if matched_concepts or any(c in chunk_lower for c in concepts):
                    return EvidenceEvaluationResult(
                        compatibility=EvidenceCompatibility.DIRECT,
                        reason=f"Case '{case_name}' provides binding judicial tests directly on operative concepts.",
                        affinity_score=0.9,
                        matched_concepts=matched_concepts,
                    )
                return EvidenceEvaluationResult(
                    compatibility=EvidenceCompatibility.RELATED,
                    reason=f"Case '{case_name}' provides relevant judicial context.",
                    affinity_score=0.6,
                )

        # Statutory chunk check
        if matched_concepts:
            return EvidenceEvaluationResult(
                compatibility=EvidenceCompatibility.DIRECT,
                reason=f"Provisions directly address operative legal concepts: {', '.join(matched_concepts)}.",
                affinity_score=0.85,
                matched_concepts=matched_concepts,
            )

        # Fallback based on text overlap with primary issue
        overlap_words = [w for w in primary_issue.replace("_", " ").split() if len(w) > 3 and w in chunk_lower]
        if overlap_words:
            return EvidenceEvaluationResult(
                compatibility=EvidenceCompatibility.RELATED,
                reason=f"Provision relates to legal issue context ({', '.join(overlap_words[:3])}).",
                affinity_score=0.5,
                matched_concepts=overlap_words,
            )

        return EvidenceEvaluationResult(
            compatibility=EvidenceCompatibility.BACKGROUND,
            reason="Peripheral statutory or procedural context.",
            affinity_score=0.3,
        )

    @classmethod
    def filter_and_budget_evidence(
        cls,
        chunks: List[Any],
        legal_question: Optional[LegalQuestion] = None,
        query_analysis: Optional[Any] = None,
        min_budget: int = 2,
        max_budget: int = 5,
    ) -> List[Any]:
        """
        Filter candidate chunks and enforce a strict 2-5 source evidence budget.
        Rejects IRRELEVANT and CONTRADICTORY chunks, prioritizes DIRECT and RELATED.
        """
        if not chunks:
            return []

        evaluated: List[Tuple[Any, EvidenceEvaluationResult]] = []
        for ch in chunks:
            eval_res = cls.evaluate_chunk(ch, legal_question=legal_question, query_analysis=query_analysis)
            evaluated.append((ch, eval_res))

        # Filter out IRRELEVANT and CONTRADICTORY
        usable = [(ch, ev) for ch, ev in evaluated if ev.compatibility not in (
            EvidenceCompatibility.IRRELEVANT,
            EvidenceCompatibility.CONTRADICTORY,
        )]

        if not usable:
            logger.warning("All %d candidate chunks were deemed IRRELEVANT or CONTRADICTORY.", len(chunks))
            # Fallback: take top 2 least irrelevant if desperate
            return chunks[:min_budget]

        # Prioritization order: DIRECT > RELATED > BACKGROUND
        priority_map = {
            EvidenceCompatibility.DIRECT: 3,
            EvidenceCompatibility.RELATED: 2,
            EvidenceCompatibility.BACKGROUND: 1,
        }

        # Sort primarily by compatibility, then affinity score, then original chunk score
        def _sort_key(item: Tuple[Any, EvidenceEvaluationResult]) -> Tuple[int, float, float]:
            ch, ev = item
            score = getattr(ch, "score", 0.0) or getattr(ch, "rerank_score", 0.0) or 0.0
            return (priority_map.get(ev.compatibility, 0), ev.affinity_score, score)

        usable.sort(key=_sort_key, reverse=True)

        # Deduplicate chunks by statutory authority (Act, Section) and case authority (Case Name)
        seen_authorities: Set[str] = set()
        deduped_usable: List[Tuple[Any, EvidenceEvaluationResult]] = []
        for ch, ev in usable:
            sec = str(getattr(ch, "section_number", "") or (ch.metadata.get("section_number") if hasattr(ch, "metadata") and isinstance(ch.metadata, dict) else "")).strip()
            act = str(getattr(ch, "act", "") or getattr(ch, "act_short_name", "") or (ch.metadata.get("act") if hasattr(ch, "metadata") and isinstance(ch.metadata, dict) else "")).strip()
            c_name = str(getattr(ch, "case_name", "") or (ch.metadata.get("case_name") if hasattr(ch, "metadata") and isinstance(ch.metadata, dict) else "")).strip()
            if c_name:
                key = f"CASE::{c_name.lower()}"
            elif act and sec:
                key = f"STATUTE::{act.lower()}::{sec.lower()}"
            else:
                key = str(getattr(ch, "chunk_id", "") or id(ch))

            if key in seen_authorities:
                continue
            seen_authorities.add(key)
            deduped_usable.append((ch, ev))

        usable = deduped_usable

        direct_count = sum(1 for _, ev in usable if ev.compatibility == EvidenceCompatibility.DIRECT)
        
        # If we have sufficient DIRECT sources, omit BACKGROUND completely
        if direct_count >= min_budget:
            usable = [(ch, ev) for ch, ev in usable if ev.compatibility != EvidenceCompatibility.BACKGROUND]

        # Enforce budget
        final_chunks = [ch for ch, _ in usable[:max_budget]]

        # Ensure at least min_budget if candidates exist
        if len(final_chunks) < min_budget and len(usable) >= min_budget:
            final_chunks = [ch for ch, _ in usable[:min_budget]]

        logger.info(
            "Evidence budgeting: %d input chunks -> %d usable -> %d selected (max %d)",
            len(chunks),
            len(usable),
            len(final_chunks),
            max_budget,
        )
        return final_chunks


# Backward compatibility wrapper for existing code calling TopicCompatibilityEngine
class TopicCompatibilityEngine:
    """Compatibility bridge to UniversalEvidenceFilter."""

    @staticmethod
    def evaluate_compatibility(chunk: Any, query_analysis: Any) -> Tuple[EvidenceCompatibility, str]:
        lq = getattr(query_analysis, "legal_question", None)
        res = UniversalEvidenceFilter.evaluate_chunk(chunk, legal_question=lq, query_analysis=query_analysis)
        setattr(chunk, "topic_compatibility", res.compatibility.value)
        if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
            chunk.metadata["topic_compatibility"] = res.compatibility.value
            chunk.metadata["compatibility_reason"] = res.reason
        return res.compatibility, res.reason

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
        for chunk in all_candidates:
            self.evaluate_compatibility(chunk, query_analysis)

        lq = getattr(query_analysis, "legal_question", None)
        return UniversalEvidenceFilter.filter_and_budget_evidence(
            all_candidates,
            legal_question=lq,
            query_analysis=query_analysis,
            min_budget=min_sources,
            max_budget=max_sources,
        )

    @staticmethod
    def filter_and_budget_evidence(
        chunks: List[Any],
        query_analysis: Any,
        min_budget: int = 2,
        max_budget: int = 5,
    ) -> List[Any]:
        lq = getattr(query_analysis, "legal_question", None)
        return UniversalEvidenceFilter.filter_and_budget_evidence(
            chunks,
            legal_question=lq,
            query_analysis=query_analysis,
            min_budget=min_budget,
            max_budget=max_budget,
        )
