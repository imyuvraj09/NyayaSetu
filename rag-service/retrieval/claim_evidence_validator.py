"""
Claim–Evidence and Citation Validator for NyayaSetu Legal Assistant.

Implements deep legal validation:
1. Substantive Legal Claim Extraction (sentences asserting statutory rules, definitions, penalties, procedures)
2. Negative Claim Detection (assertions claiming evidence is unavailable or not found in sources)
3. Claim-to-Evidence Matching (verifying statutory text support, Act provenance, and section precision)
4. Citation-to-Evidence Validation (verifying that cited [Source X] actually backs the specific claim)
5. Evidence-First Negative Response Enforcement (rejecting false 'not found' statements when evidence exists)
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from retrieval.evidence_checker import FACET_EVIDENCE_INDICATORS
from retrieval.facet_evidence_models import (
    ClaimValidationResult,
    EvidenceStatus,
    FacetEvidence,
    LegalClaim,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Patterns identifying negative claims about corpus/source availability
NEGATIVE_CLAIM_PATTERNS = [
    r"\b(?:statutory\s+sources\s+do\s+not|provided\s+sources\s+do\s+not|available\s+sources\s+do\s+not)\b",
    r"\b(?:sources\s+do\s+not\s+(?:contain|detail|establish|specify|provide)|do\s+not\s+(?:contain|detail|specify))\b",
    r"\b(?:does\s+not\s+(?:contain|detail|establish|specify|provide)|does\s+not\s+establish)\b",
    r"\b(?:not\s+(?:detailed|found|contained|specified|provided|established)\s+in\s+the\s+(?:provided|available|indexed))\b",
    r"\b(?:no\s+provision\s+(?:was\s+found|is\s+found|found|exists)\s+in)\b",
    r"\b(?:cannot\s+be\s+determined\s+from\s+the\s+available)\b",
    r"\b(?:is\s+not\s+fully\s+detailed\s+in\s+the\s+provided\s+sources)\b",
    r"\b(?:text\s+of\s+.*?\s+is\s+not\s+(?:fully\s+detailed|contained|specified))\b",
]

# Patterns to skip non-substantive sentences
DISCLAIMER_PATTERNS = [
    r"for educational purposes",
    r"does not constitute formal legal advice",
    r"consult a qualified legal professional",
    r"consult an advocate",
    r"please refer to the complete text",
]


class ClaimEvidenceValidator:
    """Extracts substantive claims from generated answers and validates them against retrieved sources."""

    def extract_claims(self, answer_text: str) -> List[LegalClaim]:
        """Parse generated answer into discrete substantive legal claims.

        Args:
            answer_text: Raw answer text or JSON string containing mainAnswer / legalBasis.

        Returns:
            List of LegalClaim objects.
        """
        text_blocks: List[str] = []

        # 1. Attempt JSON parsing for NyayaSetu structured format
        try:
            parsed = json.loads(answer_text)
            if isinstance(parsed, dict):
                if parsed.get("mainAnswer"):
                    text_blocks.append(parsed["mainAnswer"])
                if parsed.get("legalBasis"):
                    text_blocks.append(parsed["legalBasis"])
        except Exception:
            # Fallback: treat answer_text directly
            text_blocks.append(answer_text)

        raw_sentences: List[str] = []
        for block in text_blocks:
            # Split by sentence boundaries
            splits = re.split(r"(?<=[.!?])\s+", block)
            for s in splits:
                clean_s = s.strip()
                if len(clean_s) > 15:
                    raw_sentences.append(clean_s)

        extracted_claims: List[LegalClaim] = []
        last_sec_ref = None
        last_cite_label = None
        last_act_ref = None

        for sentence in raw_sentences:
            lower_s = sentence.lower()

            # Skip disclaimers
            if any(re.search(dp, lower_s) for dp in DISCLAIMER_PATTERNS):
                continue

            # Check if this sentence is a negative claim
            is_neg = any(re.search(ncp, lower_s) for ncp in NEGATIVE_CLAIM_PATTERNS)

            # Detect mentioned sections
            sec_match = re.search(r"\b(?:Section|Sec\.)\s+(\d+[A-Z]?(?:\(\d+\))?)\b", sentence, re.IGNORECASE)
            sec_ref = sec_match.group(1) if sec_match else None

            # Detect mentioned citation ([Source 1], [Source S1], [Case Source C1], [Case Source 1])
            cite_match = re.search(r"\[((?:Case\s+Source|Source|SOURCE)\s*[A-Za-z0-9_]+)\]", sentence, re.IGNORECASE)
            cite_label = f"[{cite_match.group(1)}]" if cite_match else None

            # Detect Case-Law / Judicial claims (Phase 15 & 16)
            is_judicial = bool(
                re.search(
                    r"\b(?:supreme\s+court|high\s+court|court\s+held|courts?\s+have\s+held|bench\s+observed|judgment\s+in|ruled\s+that)\b",
                    lower_s,
                )
                or re.search(r"\b(?:v\.\s+[A-Z]|versus\s+[A-Z]|\d+\s+scc\s+\d+|scc\s+online|\d+\s+air\s+\d+)\b", sentence)
                or re.search(r"\b(?:judicial\s+principles?|judicial\s+tests?|ratio\s+decidendi|doctrine\s+of)\b", lower_s)
                or "case source" in lower_s
            )

            case_ref = None
            court_ref = None
            para_ref = None

            if is_judicial:
                if "supreme court" in lower_s:
                    court_ref = "Supreme Court of India"
                elif "high court" in lower_s:
                    court_ref = "High Court"

                para_m = re.search(r"\b(?:para(?:graph)?\.?)\s*(\d+)\b", lower_s)
                if para_m:
                    para_ref = para_m.group(1)

                # Extract case name like "State of UP v. Chhotey Lal" or "Pramod Suryabhan Pawar"
                case_m = re.search(r"\b([A-Z][A-Za-z\s\.\,\(\)]+\s+(?:v\.|versus)\s+[A-Z][A-Za-z\s\.\,\(\)]+)\b", sentence)
                if case_m:
                    case_ref = case_m.group(1).strip()

            # Detect mentioned Act
            act_ref = None
            if "bharatiya nyaya sanhita" in lower_s or "bns" in lower_s:
                act_ref = "Bharatiya Nyaya Sanhita, 2023"
            elif "bharatiya nagarik suraksha" in lower_s or "bnss" in lower_s:
                act_ref = "Bharatiya Nagarik Suraksha Sanhita, 2023"
            elif "bharatiya sakshya" in lower_s or "bsa" in lower_s:
                act_ref = "Bharatiya Sakshya Adhiniyam, 2023"
            elif "right to information" in lower_s or re.search(r"\brti\b", lower_s):
                act_ref = "Right to Information Act, 2005"
            elif "consumer protection" in lower_s:
                act_ref = "Consumer Protection Act, 2019"
            elif "pocso" in lower_s:
                act_ref = "POCSO Act, 2012"

            # Anaphora inheritance for continuation sentences like "This section..."
            is_continuation = any(lower_s.startswith(p) for p in ["this section", "the section", "this provision", "under this provision", "it further", "additionally", "this court", "the court further"])
            if is_continuation:
                if not sec_ref:
                    sec_ref = last_sec_ref
                if not cite_label:
                    cite_label = last_cite_label
                if not act_ref:
                    act_ref = last_act_ref

            if sec_ref:
                last_sec_ref = sec_ref
            if cite_label:
                last_cite_label = cite_label
            if act_ref:
                last_act_ref = act_ref

            # Determine facet
            assigned_facet = "judicial_principles" if is_judicial else "general"
            if not is_judicial:
                for facet_name, indicators in FACET_EVIDENCE_INDICATORS.items():
                    if any(re.search(rf"\b{re.escape(ind)}\b", lower_s) for ind in indicators):
                        assigned_facet = facet_name
                        break

            # If section 103 or punishment terms present, set facet to punishment
            if not is_judicial and (sec_ref and sec_ref.startswith("103") or any(kw in lower_s for kw in ["punishment", "sentencing", "punished with"])):
                assigned_facet = "punishment"

            extracted_claims.append(
                LegalClaim(
                    claim_text=sentence,
                    facet=assigned_facet,
                    section_reference=sec_ref,
                    act_reference=act_ref,
                    citation_label=cite_label,
                    is_negative_claim=is_neg,
                    source_required=True,
                    evidence_type_required="CASE_LAW" if is_judicial else "STATUTE",
                    case_reference=case_ref,
                    court_reference=court_ref,
                    paragraph_reference=para_ref,
                )
            )

        return extracted_claims

    @staticmethod
    def _get_source_text(s: Any) -> str:
        if hasattr(s, "text") and s.text:
            return str(s.text)
        if hasattr(s, "content_snippet") and s.content_snippet:
            return str(s.content_snippet)
        if hasattr(s, "text_snippet") and s.text_snippet:
            return str(s.text_snippet)
        if isinstance(s, dict):
            return str(s.get("text") or s.get("content_snippet") or s.get("text_snippet") or "")
        return ""

    @staticmethod
    def _get_source_section(s: Any) -> str:
        if hasattr(s, "section") and s.section:
            return str(s.section)
        if hasattr(s, "section_number") and s.section_number:
            return str(s.section_number)
        if isinstance(s, dict):
            return str(s.get("section") or s.get("section_number") or "")
        return ""

    @staticmethod
    def _get_source_sections_all(s: Any) -> List[str]:
        secs: List[str] = []
        sec = ClaimEvidenceValidator._get_source_section(s)
        if sec:
            secs.append(sec)
        if hasattr(s, "section_numbers") and s.section_numbers:
            secs.extend(s.section_numbers)
        if hasattr(s, "metadata") and isinstance(s.metadata, dict) and s.metadata.get("section_numbers"):
            secs.extend(s.metadata.get("section_numbers"))
        # Clean section numbers to digits
        clean_list = []
        for sn in secs:
            clean = re.sub(r"\D", "", str(sn))
            if clean:
                clean_list.append(clean)
        return list(dict.fromkeys(clean_list))

    @staticmethod
    def _get_source_doc_name(s: Any) -> str:
        if hasattr(s, "document_name") and s.document_name:
            return str(s.document_name)
        if hasattr(s, "act") and s.act:
            return str(s.act)
        if isinstance(s, dict):
            return str(s.get("document_name") or s.get("act") or "")
        return ""

    def validate_claims(
        self,
        claims: List[LegalClaim],
        sources: List[Any],
        facet_coverage: Dict[str, Any],
        target_act: Optional[str] = None,
        query_analysis: Optional[Any] = None,
    ) -> Tuple[List[ClaimValidationResult], Dict[str, Any]]:
        """Validate each claim against retrieved sources and corpus facet evidence.

        Args:
            claims: List of LegalClaim extracted from the answer.
            sources: List of SourceReference objects passed in the LLM prompt.
            facet_coverage: Dict mapping facet names to coverage info (including evidence_status).
            target_act: Optional expected primary statute name.
            query_analysis: Optional query analysis containing primary_issue and excluded_topics.

        Returns:
            Tuple of (List[ClaimValidationResult], Summary Metrics Dict).
        """
        results: List[ClaimValidationResult] = []
        source_map_by_label: Dict[str, Any] = {}
        source_map_by_section: Dict[str, List[Any]] = {}

        for i, s in enumerate(sources):
            raw_label = getattr(s, "source_label", getattr(s, "label", None))
            if not raw_label and isinstance(s, dict):
                raw_label = s.get("source_label") or s.get("label")
            if not raw_label:
                rank = getattr(s, "rank", i + 1) if not isinstance(s, dict) else s.get("rank", i + 1)
                raw_label = f"[SOURCE {rank}]"
            label = raw_label.upper().replace(" ", "")
            source_map_by_label[label] = s

            all_secs = self._get_source_sections_all(s)
            for clean_sec in all_secs:
                source_map_by_section.setdefault(clean_sec, []).append(s)

        total_claims = len(claims)
        supported_count = 0
        unsupported_count = 0
        invalid_citations_count = 0
        false_negative_count = 0

        for claim in claims:
            # Rule 8: Claim-Level Topic Check
            if query_analysis:
                excluded = getattr(query_analysis, "excluded_topics", []) or []
                p_issue = getattr(query_analysis, "primary_issue", "") or ""
                claim_lower = claim.claim_text.lower()
                is_out_of_scope = False
                out_of_scope_topic = ""
                for ex in excluded:
                    if ex.lower() in claim_lower:
                        is_out_of_scope = True
                        out_of_scope_topic = ex
                        break
                if is_out_of_scope:
                    unsupported_count += 1
                    results.append(
                        ClaimValidationResult(
                            claim=claim.claim_text,
                            facet=claim.facet,
                            supported=False,
                            source=None,
                            citation_valid=False if claim.citation_label else True,
                            is_negative_claim=False,
                            negative_claim_valid=True,
                            reason=f"OUT OF SCOPE TOPIC: Claim introduces topic '{out_of_scope_topic}' which is excluded for primary issue '{p_issue}'.",
                            evidence_type=claim.evidence_type,
                            is_judicial_claim=claim.is_judicial_claim,
                        )
                    )
                    continue

            # Case 1: Negative Claim Validation (Evidence-First Policy)
            if claim.is_negative_claim:
                f_name = claim.facet
                cov = facet_coverage.get(f_name, {})
                ev_status = cov.get("evidence_status", "")

                # If the retrieval layer found evidence for this facet in the corpus:
                if ev_status == EvidenceStatus.FOUND.value or cov.get("supported", False):
                    src_secs = cov.get("source_sections", [])
                    false_negative_count += 1
                    unsupported_count += 1
                    results.append(
                        ClaimValidationResult(
                            claim=claim.claim_text,
                            facet=claim.facet,
                            supported=False,
                            source=None,
                            citation_valid=True,
                            is_negative_claim=True,
                            negative_claim_valid=False,
                            reason=(
                                f"FALSE NEGATIVE CLAIM REJECTED: The answer asserts that '{f_name}' is "
                                f"missing or not detailed in the sources, but the retrieved corpus DOES contain "
                                f"official statutory evidence (Section(s): {src_secs})."
                            ),
                        )
                    )
                else:
                    # Legitimate negative claim (statute/provision genuinely absent)
                    supported_count += 1
                    results.append(
                        ClaimValidationResult(
                            claim=claim.claim_text,
                            facet=claim.facet,
                            supported=True,
                            source=None,
                            citation_valid=True,
                            is_negative_claim=True,
                            negative_claim_valid=True,
                            reason="VERIFIED NEGATIVE CLAIM: Statutory search confirmed no supporting provision in corpus.",
                        )
                    )
                continue

            # Case 3: Judicial Claim Validation (Phase 15 & 16)
            if claim.evidence_type_required == "CASE_LAW":
                case_law_sources = [
                    s for s in sources
                    if getattr(s, "evidence_type", "") == "CASE_LAW"
                    or (isinstance(s, dict) and s.get("evidence_type") == "CASE_LAW")
                    or "case" in getattr(s, "document_type", "").lower()
                ]

                if not case_law_sources:
                    # No CASE_LAW sources available: absolute failure against fabricated case law
                    unsupported_count += 1
                    results.append(
                        ClaimValidationResult(
                            claim=claim.claim_text,
                            facet=claim.facet,
                            supported=False,
                            source=None,
                            citation_valid=False if claim.citation_label else True,
                            is_negative_claim=False,
                            negative_claim_valid=True,
                            reason="UNSUPPORTED JUDICIAL CLAIM / FABRICATED CASE LAW: Claim asserts a court decision or judicial principle, but no verified CASE_LAW source exists in the retrieved context.",
                            evidence_type="CASE_LAW",
                            is_judicial_claim=True,
                            is_fabricated_case_law=True,
                        )
                    )
                    continue

                supporting_source = None
                citation_is_valid = True
                fail_reason = ""

                # Check cited label
                if claim.citation_label:
                    clean_label = claim.citation_label.upper().replace(" ", "")
                    cited_source = source_map_by_label.get(clean_label)
                    if cited_source:
                        ev_type = getattr(cited_source, "evidence_type", "")
                        if not ev_type and isinstance(cited_source, dict):
                            ev_type = cited_source.get("evidence_type", "")
                        if ev_type != "CASE_LAW" and "case" not in getattr(cited_source, "document_type", "").lower():
                            citation_is_valid = False
                            invalid_citations_count += 1
                            fail_reason = f"Authority mismatch: Statutory enactment {claim.citation_label} cited for a judicial precedent claim."
                        else:
                            supporting_source = cited_source
                    else:
                        citation_is_valid = False
                        invalid_citations_count += 1
                        fail_reason = f"Hallucinated citation: {claim.citation_label} does not exist in context."

                # If no cited source or mismatch, match among case_law_sources
                if not supporting_source:
                    if claim.case_reference:
                        matched_case = False
                        clean_ref = re.sub(r"\s+", " ", claim.case_reference.lower()).strip()
                        for cls in case_law_sources:
                            cls_name = getattr(cls, "case_name", getattr(cls, "document_name", "")).lower()
                            if clean_ref in cls_name or cls_name in clean_ref:
                                supporting_source = cls
                                matched_case = True
                                break
                            parties = [p.strip() for p in re.split(r"\s+(?:v\.|versus)\s+", clean_ref) if len(p.strip()) > 3]
                            if any(p in cls_name for p in parties if p not in ["state", "union of india", "delhi", "kerala", "maharashtra"]):
                                supporting_source = cls
                                matched_case = True
                                break

                        if not matched_case:
                            # Explicit case name cited that is not in retrieved verified sources
                            unsupported_count += 1
                            results.append(
                                ClaimValidationResult(
                                    claim=claim.claim_text,
                                    facet=claim.facet,
                                    supported=False,
                                    source=None,
                                    citation_valid=False,
                                    is_negative_claim=False,
                                    negative_claim_valid=True,
                                    reason=f"UNVERIFIED / FABRICATED CASE PRECEDENT: Case '{claim.case_reference}' does not exist in verified case-law sources.",
                                    evidence_type="CASE_LAW",
                                    is_judicial_claim=True,
                                    is_fabricated_case_law=True,
                                )
                            )
                            continue

                # If no specific case name cited, match by meaningful semantic keyword overlap in case_law_sources
                if not supporting_source:
                    best_cls = None
                    best_overlap = 0.0
                    claim_words = [
                        w for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim.claim_text.lower())
                        if w not in ("court", "supreme", "bench", "observed", "held", "judgment", "under", "which", "shall", "state", "order", "legal")
                    ]
                    for cls in case_law_sources:
                        cls_text = self._get_source_text(cls).lower()
                        match_count = sum(1 for w in claim_words if w in cls_text)
                        overlap = match_count / max(1, len(claim_words))
                        if overlap > best_overlap and overlap >= 0.30:
                            best_overlap = overlap
                            best_cls = cls
                    if best_cls:
                        supporting_source = best_cls

                # Verify support in supporting_source
                is_supported = False
                if supporting_source and citation_is_valid:
                    s_text = self._get_source_text(supporting_source).lower()
                    claim_words = [
                        w for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim.claim_text.lower())
                        if w not in ("court", "supreme", "bench", "observed", "held", "judgment", "under", "which", "shall", "state", "order", "legal")
                    ]
                    matching_words = [w for w in claim_words if w in s_text]
                    overlap_ratio = len(matching_words) / max(1, len(claim_words))

                    if overlap_ratio >= 0.25 or (claim.paragraph_reference and f"para {claim.paragraph_reference}" in s_text):
                        is_supported = True
                    else:
                        fail_reason = "Retrieved judgment text does not contain sufficient semantic support for this judicial claim."

                if not supporting_source and not fail_reason:
                    fail_reason = "No retrieved case-law source contains or substantiates this judicial claim."

                if is_supported and citation_is_valid:
                    supported_count += 1
                else:
                    unsupported_count += 1

                source_dict = None
                if supporting_source:
                    source_dict = {
                        "label": getattr(supporting_source, "source_label", getattr(supporting_source, "label", "")),
                        "case_name": getattr(supporting_source, "case_name", getattr(supporting_source, "document_name", "")),
                        "court": getattr(supporting_source, "court", ""),
                        "citation": getattr(supporting_source, "citation", ""),
                        "paragraph": getattr(supporting_source, "paragraph_number", ""),
                        "evidence_type": "CASE_LAW",
                    }

                results.append(
                    ClaimValidationResult(
                        claim=claim.claim_text,
                        facet=claim.facet,
                        supported=is_supported,
                        source=source_dict,
                        citation_valid=citation_is_valid,
                        is_negative_claim=False,
                        negative_claim_valid=True,
                        reason=fail_reason or "Supported by verified judicial precedent.",
                        evidence_type="CASE_LAW",
                        is_judicial_claim=True,
                        is_fabricated_case_law=False,
                    )
                )
                continue

            # Case 2: Substantive Affirmative Statutory Claim Validation
            supporting_source = None
            citation_is_valid = True
            is_supported = False
            fail_reason = ""

            # 2a. Check cited source if present
            if claim.citation_label:
                clean_label = claim.citation_label.upper().replace(" ", "")
                cited_source = source_map_by_label.get(clean_label)
                if cited_source:
                    supporting_source = cited_source
                    cited_secs = self._get_source_sections_all(cited_source)
                    cited_text = self._get_source_text(cited_source)

                    # Verify citation accuracy against claim section
                    if claim.section_reference:
                        clean_claim_sec = re.sub(r"\D", "", claim.section_reference)
                        # Check if claim section is in cited chunk sections or mentioned in text
                        sec_in_cited = (clean_claim_sec in cited_secs) or bool(
                            re.search(rf"\b(?:Section|Sec\.)?\s*{re.escape(clean_claim_sec)}\b", cited_text, re.IGNORECASE)
                        )
                        if not sec_in_cited:
                            citation_is_valid = False
                            invalid_citations_count += 1
                            fail_reason = (
                                f"Citation mismatch: Claim references Section {claim.section_reference} "
                                f"but cites {claim.citation_label} which corresponds to Section(s) {cited_secs}."
                            )
                else:
                    citation_is_valid = False
                    invalid_citations_count += 1
                    fail_reason = f"Hallucinated citation: {claim.citation_label} does not exist in context."

            # 2b. If no citation or citation mismatch, look up by claimed section
            if not supporting_source and claim.section_reference:
                clean_claim_sec = re.sub(r"\D", "", claim.section_reference)
                matching_sources = source_map_by_section.get(clean_claim_sec, [])
                if matching_sources:
                    supporting_source = matching_sources[0]

            # 2c. If still not found, search text of all available sources
            if not supporting_source:
                for s in sources:
                    s_text = self._get_source_text(s).lower()
                    if claim.section_reference and f" {claim.section_reference}." in s_text:
                        supporting_source = s
                        break

            # 2d. Verify substantive support in supporting source
            if supporting_source and citation_is_valid:
                s_text = self._get_source_text(supporting_source).lower()
                s_doc = self._get_source_doc_name(supporting_source)

                # Verify Act provenance
                act_matches = True
                if claim.act_reference and target_act:
                    if claim.act_reference.lower() not in s_doc.lower() and s_doc.lower() not in claim.act_reference.lower():
                        act_matches = False
                        fail_reason = f"Act mismatch: Expected {claim.act_reference}, found {s_doc}."

                if act_matches:
                    # Check substantive key terms from claim
                    claim_words = [
                        w for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim.claim_text.lower())
                        if w not in (
                            "under", "which", "shall", "where", "other", "person", "about",
                            "provided", "source", "provides", "section", "clause", "sub",
                            "according", "stated", "states"
                        )
                    ]
                    matching_words = [w for w in claim_words if w in s_text]
                    overlap_ratio = len(matching_words) / max(1, len(claim_words))

                    if overlap_ratio >= 0.15 or (claim.section_reference and re.search(rf"\b{re.escape(claim.section_reference)}\b", s_text)):
                        is_supported = True
                    else:
                        fail_reason = "Source text does not contain sufficient semantic overlap with claim."

            if not supporting_source and not fail_reason:
                fail_reason = "No retrieved statutory source contains or substantiates this claim."

            if is_supported and citation_is_valid:
                supported_count += 1
            else:
                unsupported_count += 1

            source_dict = None
            if supporting_source:
                sec_val = self._get_source_section(supporting_source)
                source_dict = {
                    "label": getattr(supporting_source, "source_label", getattr(supporting_source, "label", "")),
                    "act": self._get_source_doc_name(supporting_source),
                    "section": sec_val,
                    "title": getattr(supporting_source, "section_title", getattr(supporting_source, "title", "")),
                    "pages": getattr(supporting_source, "page_numbers", getattr(supporting_source, "pages", [])),
                }

            results.append(
                ClaimValidationResult(
                    claim=claim.claim_text,
                    facet=claim.facet,
                    supported=is_supported,
                    source=source_dict,
                    citation_valid=citation_is_valid,
                    is_negative_claim=False,
                    negative_claim_valid=True,
                    reason=fail_reason or "Supported by statutory source evidence.",
                )
            )

        metrics = {
            "total_claims": total_claims,
            "supported_claims": supported_count,
            "unsupported_claims": unsupported_count,
            "invalid_citations": invalid_citations_count,
            "false_negative_claims": false_negative_count,
            "claim_support_accuracy": round((supported_count / total_claims) if total_claims else 1.0, 3),
            "is_valid": (unsupported_count == 0 and false_negative_count == 0 and invalid_citations_count == 0),
        }

        logger.info(
            "Claim-Evidence Validation: total=%d, supported=%d, unsupported=%d, false_neg=%d, valid=%s",
            total_claims,
            supported_count,
            unsupported_count,
            false_negative_count,
            metrics["is_valid"],
        )

        return results, metrics

    def audit_and_sanitize_answer(
        self,
        answer_text: str,
        sources: List[Any],
        query_analysis: Optional[Any] = None,
    ) -> str:
        """Audit and sanitize a generated answer to strictly eliminate unsupported legal claims,

        model-knowledge backfill of unretrieved sections, citation borrowing, and ungrounded
        procedural or evidentiary overclaims.
        """
        if not answer_text or not sources:
            return answer_text

        # Collect valid retrieved sections and Acts
        valid_sections: Set[str] = set()
        valid_acts: Set[str] = set()
        has_procedural_source = False
        has_evidence_source = False
        has_ncrp_source = False

        for s in sources:
            all_secs = self._get_source_sections_all(s)
            for sc in all_secs:
                clean_sc = sc.lower().strip()
                valid_sections.add(clean_sc)
                valid_sections.add(re.sub(r"[^0-9a-z]", "", clean_sc))

            doc_name = self._get_source_doc_name(s).lower()
            text_content = self._get_source_text(s).lower()
            valid_acts.add(doc_name)

            if any(p in doc_name or p in text_content for p in ["procedural", "suraksha", "bnss", "crpc", "criminal procedure"]):
                has_procedural_source = True
            if any(e in doc_name or e in text_content for e in ["sakshya", "evidence", "bsa", "indian evidence"]):
                has_evidence_source = True
            if any(n in doc_name or n in text_content for n in ["cybercrime.gov.in", "ncrp", "national cyber crime reporting"]):
                has_ncrp_source = True

        def sanitize_content_string(content: str) -> str:
            lines = content.splitlines()
            sanitized_lines: List[str] = []
            in_offences_section = False
            in_investigation_section = False
            in_evidence_section = False
            in_conclusion_section = False

            for line in lines:
                trimmed = line.strip()
                lower_line = trimmed.lower()

                # Track section headers (with or without markdown '#' formatting)
                if re.match(r"^(?:#{1,4}\s+)?(?:possible\s+offences|relevant\s+offences|applicable\s+offences|offences|provisions)\b", lower_line):
                    in_offences_section = True
                    in_investigation_section = False
                    in_evidence_section = False
                    in_conclusion_section = False
                    sanitized_lines.append(line)
                    continue
                elif re.match(r"^(?:#{1,4}\s+)?(?:investigation\s+procedures?|investigation|procedural\s+steps?)\b", lower_line):
                    in_offences_section = False
                    in_investigation_section = True
                    in_evidence_section = False
                    in_conclusion_section = False
                    sanitized_lines.append(line)
                    continue
                elif re.match(r"^(?:#{1,4}\s+)?(?:evidence(?:\s+to\s+preserve|\s+required)?|proof)\b", lower_line):
                    in_offences_section = False
                    in_investigation_section = False
                    in_evidence_section = True
                    in_conclusion_section = False
                    sanitized_lines.append(line)
                    continue
                elif re.match(r"^(?:#{1,4}\s+)?(?:conclusion|summary|takeaways?)\b", lower_line):
                    in_offences_section = False
                    in_investigation_section = False
                    in_evidence_section = False
                    in_conclusion_section = True
                    sanitized_lines.append(line)
                    continue
                elif re.match(r"^(?:#{1,4}\s+)?[A-Z][A-Za-z\s]{2,30}$", trimmed) and any(hdr in lower_line for hdr in ["answer", "application", "steps", "sources", "disclaimer"]):
                    in_offences_section = False
                    in_investigation_section = False
                    in_evidence_section = False
                    in_conclusion_section = False

                # Check for unretrieved section references
                sec_matches = re.findall(r"\b(?:Section|Sec\.)\s+(\d+[A-Za-z]*)", line, re.IGNORECASE)
                if sec_matches:
                    unretrieved_found = False
                    for sm in sec_matches:
                        clean_sm = re.sub(r"[^0-9a-z]", "", sm.lower())
                        if clean_sm not in valid_sections:
                            unretrieved_found = True
                            break

                    if unretrieved_found:
                        # If inside an offence bullet or list item, prune the unretrieved section claim
                        if in_offences_section or trimmed.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.")):
                            logger.info("Pruning unsupported offence claim with unretrieved section: %s", trimmed)
                            continue
                        elif in_conclusion_section:
                            # Prune unretrieved sections from conclusion
                            clean_line = line
                            for sm in sec_matches:
                                clean_sm = re.sub(r"[^0-9a-z]", "", sm.lower())
                                if clean_sm not in valid_sections:
                                    clean_line = re.sub(rf",?\s*(?:and\s+)?(?:Section|Sec\.)\s+{re.escape(sm)}", "", clean_line, flags=re.IGNORECASE)
                            clean_line = re.sub(r"\s+,\s+", ", ", clean_line)
                            clean_line = re.sub(r"under\s*\.", "under the governing statutory provisions.", clean_line)
                            sanitized_lines.append(clean_line)
                            continue
                        else:
                            # If line asserts unretrieved section as applicable law
                            if any(w in lower_line for w in ["applies", "punishes", "attracted", "liable", "penalty", "offence", "provides", "fir", "certificate"]):
                                if in_investigation_section and not has_procedural_source:
                                    line = "Practical steps involve securing audit trails, access logs, and communications to facilitate formal reporting."
                                elif in_evidence_section and not has_evidence_source:
                                    line = "Digital evidence such as server logs, IP access records, and file checksums may help establish the facts of unauthorized entry."
                                else:
                                    logger.info("Pruning unsupported statutory assertion: %s", trimmed)
                                    continue

                # In investigation section without procedural statute, sanitize statutory procedure claims
                if in_investigation_section and not has_procedural_source:
                    if any(sp in lower_line for sp in ["mandatorily register an fir", "section 154", "statutory investigation mandate", "mandatory statutory procedure"]):
                        line = "Practical steps involve securing audit trails, access logs, and communications to facilitate formal reporting."

                # In evidence section without evidence statute, sanitize statutory certificate mandates
                if in_evidence_section and not has_evidence_source:
                    if any(es in lower_line for es in ["section 63", "section 65b", "statutory certificate under", "mandatory certificate under"]):
                        line = "Digital evidence such as server logs, IP access records, and file checksums may help establish the facts of unauthorized entry."

                sanitized_lines.append(line)

            # Recombine and clean double blank lines
            cleaned = "\n".join(sanitized_lines)
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
            return cleaned

        # Handle JSON format
        try:
            parsed = json.loads(answer_text)
            if isinstance(parsed, dict):
                if parsed.get("mainAnswer"):
                    parsed["mainAnswer"] = sanitize_content_string(parsed["mainAnswer"])
                if parsed.get("legalBasis"):
                    parsed["legalBasis"] = sanitize_content_string(parsed["legalBasis"])
                return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            pass

        return sanitize_content_string(answer_text)


_CLAIM_VALIDATOR_INSTANCE = None


def get_claim_evidence_validator() -> ClaimEvidenceValidator:
    """Return singleton instance of ClaimEvidenceValidator."""
    global _CLAIM_VALIDATOR_INSTANCE
    if _CLAIM_VALIDATOR_INSTANCE is None:
        _CLAIM_VALIDATOR_INSTANCE = ClaimEvidenceValidator()
    return _CLAIM_VALIDATOR_INSTANCE

