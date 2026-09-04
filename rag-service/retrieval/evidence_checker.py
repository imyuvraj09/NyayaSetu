"""
Evidence Sufficiency Checker and Automatic Secondary Retrieval Pipeline.

Verifies whether primary retrieval candidates contain sufficient statutory evidence
to answer all requested facets of the user's legal question (e.g. definition + punishment).
If a facet is missing, automatically executes targeted secondary retrieval across
exact sections, section titles, and keyword indices before final reranking and LLM synthesis.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from retrieval.bm25_search import get_bm25_engine
from retrieval.query_analyzer import LegalQueryAnalysis
from retrieval.section_indexer import IndexedChunk, get_section_indexer
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceSufficiencyResult:
    """Outcome of evidence sufficiency verification and secondary retrieval."""
    is_sufficient: bool
    verified_aspects: List[str]
    missing_aspects: List[str]
    secondary_retrieval_triggered: bool
    recovered_chunks: List[IndexedChunk] = field(default_factory=list)
    aspect_evidence_map: Dict[str, List[str]] = field(default_factory=dict)


class LegalEvidenceChecker:
    """Verifies evidence completeness against query requirements and performs fallback retrieval."""

    def __init__(self) -> None:
        self.section_indexer = get_section_indexer()
        self.bm25_engine = get_bm25_engine()

# Generalized statutory evidence indicators for legal facets
FACET_EVIDENCE_INDICATORS: Dict[str, List[str]] = {
    "definition": [
        "is said to", "is defined as", "means", "shall mean", "constitutes",
        "defined as", "meaning of", "refers to", "offence of", "culpable homicide is murder",
        "whoever commits", "whoever causes death", "whoever, intending to", "whoever by deceiving"
    ],
    "elements": [
        "ingredients", "essential ingredients", "constituent elements", "elements of",
        "intention of", "knowledge that", "act of causing", "bodily injury",
        "requirements to prove", "shall satisfy the following conditions"
    ],
    "exceptions": [
        "exception", "exceptions", "shall not amount to", "does not amount to",
        "exemption", "exempted", "proviso", "provided that", "saving clause",
        "private defence", "grave and sudden provocation", "sudden fight"
    ],
    "punishment": [
        "shall be punished with", "punished with death", "punishable with", "liable to fine",
        "imprisonment for life", "imprisonment of either description", "rigorous imprisonment",
        "shall also be liable to", "punishment prescribed", "sentence of imprisonment",
        "with fine which may extend", "fine and imprisonment"
    ],
    "penalty": [
        "penalty", "penalties", "liable to a penalty", "fine of", "financial penalty", "penalized"
    ],
    "procedure": [
        "procedure", "investigation", "inquest", "examination of", "police officer",
        "charge sheet", "first information report", "fir", "manner of", "inquiry",
        "application", "notice", "filing"
    ],
    "rights": [
        "right", "rights", "entitled to", "informed of the grounds", "consult",
        "consult an advocate", "right to bail", "personal liberty", "protection of"
    ],
    "duties": [
        "duty", "duties", "obligations", "shall be the duty", "responsible for",
        "responsibility", "obligation of"
    ],
    "eligibility": [
        "eligible", "eligibility", "qualification", "qualifications", "criteria",
        "who is eligible", "disqualification"
    ],
    "time_limit": [
        "time limit", "limitation", "period of limitation", "within a period of",
        "thirty days", "deadline", "within what time", "expiry of"
    ],
    "grounds": [
        "ground", "grounds for", "grounds of", "ground of", "on the ground that",
        "basis for", "on the grounds of"
    ],
    "remedies": [
        "remedy", "remedies", "redressal", "relief", "compensation", "damages",
        "appeal", "first appeal", "complaint", "revision"
    ],
    "evidence": [
        "evidence", "admissible", "admissibility", "relevant fact", "burden of proof",
        "electronic record", "certificate signed", "documentary evidence", "presumption"
    ],
    "defences": [
        "defence", "defences", "general exceptions", "private defence", "intoxication",
        "unsound mind", "justification", "plea"
    ],
    "authorities": [
        "authority", "authorities", "public information officer", "pio", "magistrate",
        "internal committee", "icc", "commission", "officer"
    ],
    "jurisdiction": [
        "jurisdiction", "court of session", "magistrate", "high court", "competent court",
        "tribunal", "cognizance", "local limits"
    ],
}


class LegalEvidenceChecker:
    """Verifies evidence completeness against query requirements and performs fallback retrieval."""

    def __init__(self) -> None:
        self.section_indexer = get_section_indexer()
        self.bm25_engine = get_bm25_engine()

    def has_facet_evidence(
        self,
        facet_name: str,
        text: str,
        titles: List[str],
        entity: str = "",
    ) -> bool:
        """Check whether statutory text or section titles support a given legal facet."""
        lower_text = text.lower()
        title_str = " ".join(titles).lower()
        indicators = FACET_EVIDENCE_INDICATORS.get(facet_name, [facet_name])

        # 1. Section title matching
        if facet_name in title_str:
            return True
        if entity and (entity.lower() in title_str):
            if facet_name == "definition" and "punishment" not in title_str:
                return True
            if facet_name == "punishment" and "punishment" in title_str:
                return True

        # 2. Textual indicator matching
        if any(ind in lower_text for ind in indicators):
            return True

        # 3. Structural indicators (e.g. elements often have (a), (b), (c) or (1), (2))
        if facet_name == "elements":
            if re.search(r"\((?:a|b|c|d|1|2|3|4)\)", text) and any(kw in lower_text for kw in ["whoever", "if", "causing", "intention", "injury"]):
                return True

        # 4. Time limit regex indicators
        if facet_name == "time_limit":
            if re.search(r"\b\d+\s+(?:days|months|years|hours)\b", lower_text):
                return True

        return False

    def _has_definition_evidence(self, text: str, titles: List[str], entity: str) -> bool:
        return self.has_facet_evidence("definition", text, titles, entity)

    def _has_punishment_evidence(self, text: str, titles: List[str]) -> bool:
        return self.has_facet_evidence("punishment", text, titles)

    def _has_procedure_evidence(self, text: str, titles: List[str]) -> bool:
        return self.has_facet_evidence("procedure", text, titles)

    def _has_evidence_rules(self, text: str, titles: List[str]) -> bool:
        return self.has_facet_evidence("evidence", text, titles)

    def check_and_recover(
        self,
        analysis: LegalQueryAnalysis,
        current_candidates: List[Any],
    ) -> EvidenceSufficiencyResult:
        """Validate candidate evidence against requested information and recover missing aspects.

        Args:
            analysis: LegalQueryAnalysis containing requested_information, act, entities, etc.
            current_candidates: List of currently retrieved chunks (IndexedChunk or RetrievedChunk).

        Returns:
            EvidenceSufficiencyResult with status and any newly recovered chunks.
        """
        entity = analysis.entities[0] if analysis.entities else ""
        doc_id = analysis.document_id

        verified: List[str] = []
        missing: List[str] = []
        aspect_evidence_map: Dict[str, List[str]] = {}

        # Scan current candidate pool for each requested information aspect
        for req in analysis.requested_information:
            facet_found = False
            for c in current_candidates:
                text = getattr(c, "text", "")
                titles = getattr(c, "section_titles", [])
                cid = getattr(c, "chunk_id", "")
                if self.has_facet_evidence(req, text, titles, entity):
                    facet_found = True
                    aspect_evidence_map.setdefault(req, []).append(cid)

            if facet_found:
                verified.append(req)
            else:
                missing.append(req)

        # If everything is satisfied, return early
        if not missing:
            logger.info("Evidence sufficiency check PASSED: all requested facets %s verified.", verified)
            return EvidenceSufficiencyResult(
                is_sufficient=True,
                verified_aspects=verified,
                missing_aspects=[],
                secondary_retrieval_triggered=False,
                recovered_chunks=[],
                aspect_evidence_map=aspect_evidence_map,
            )

        # Trigger Targeted Secondary Retrieval
        logger.warning(
            "Evidence sufficiency check FAILED for %s. Triggering targeted secondary retrieval...",
            missing,
        )

        recovered: List[IndexedChunk] = []
        recovered_ids: Set[str] = set(getattr(c, "chunk_id", "") for c in current_candidates)

        for missing_aspect in missing:
            targeted_chunks: List[IndexedChunk] = []

            # 1. Section Title Search
            if entity:
                title_query = f"{missing_aspect} for {entity}" if missing_aspect in ("punishment", "procedure", "penalty") else f"{entity}"
            else:
                title_query = missing_aspect

            title_matches = self.section_indexer.get_chunks_by_section_title(title_query, doc_id)
            targeted_chunks.extend(title_matches[:3])

            # 2. General BM25 Search across canonical statutory phrasing
            indicators = FACET_EVIDENCE_INDICATORS.get(missing_aspect, [missing_aspect])
            sample_phrase = " ".join(indicators[:3])
            bm25_query = f"{entity} {missing_aspect} {sample_phrase}".strip()
            bm25_hits = self.bm25_engine.search(bm25_query, doc_id, top_k=4)
            for chunk, _ in bm25_hits:
                targeted_chunks.append(chunk)

            # Deduplicate and add to recovered
            for chunk in targeted_chunks:
                if chunk.chunk_id not in recovered_ids:
                    recovered_ids.add(chunk.chunk_id)
                    recovered.append(chunk)
                    aspect_evidence_map.setdefault(missing_aspect, []).append(chunk.chunk_id)

        # Re-verify with recovered chunks included
        all_checked = list(current_candidates) + list(recovered)
        still_missing: List[str] = []
        for req in missing:
            facet_found = False
            for c in all_checked:
                text = getattr(c, "text", "")
                titles = getattr(c, "section_titles", [])
                if self.has_facet_evidence(req, text, titles, entity):
                    facet_found = True
                    break

            if facet_found:
                verified.append(req)
            else:
                still_missing.append(req)

        is_now_sufficient = len(still_missing) == 0
        logger.info(
            "Secondary retrieval complete: recovered %d additional chunk(s). Sufficiency: %s (Verified: %s, Still Missing: %s)",
            len(recovered),
            is_now_sufficient,
            verified,
            still_missing,
        )

        return EvidenceSufficiencyResult(
            is_sufficient=is_now_sufficient,
            verified_aspects=verified,
            missing_aspects=still_missing,
            secondary_retrieval_triggered=True,
            recovered_chunks=recovered,
            aspect_evidence_map=aspect_evidence_map,
        )


_EVIDENCE_CHECKER_INSTANCE = None

def get_evidence_checker() -> LegalEvidenceChecker:
    """Return singleton instance of LegalEvidenceChecker."""
    global _EVIDENCE_CHECKER_INSTANCE
    if _EVIDENCE_CHECKER_INSTANCE is None:
        _EVIDENCE_CHECKER_INSTANCE = LegalEvidenceChecker()
    return _EVIDENCE_CHECKER_INSTANCE
