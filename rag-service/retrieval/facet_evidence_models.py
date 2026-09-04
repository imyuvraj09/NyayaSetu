"""
Evidence-backed Facet Models and Status Enums for NyayaSetu Legal Assistant.

Defines rich representations for:
1. FacetEvidenceSource (exact provenance of supporting statutory chunks)
2. FacetEvidence (statutory backing and status of each legal facet)
3. FacetStatus (fine-grained lifecycle status of a facet in an answer)
4. FinalQualityStatus (overall answer quality gate status)
5. Claim & ClaimValidation (atomic substantive legal assertions and verification)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceStatus(str, Enum):
    """Corpus evidence availability status for a requested facet."""
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"


class FacetStatus(str, Enum):
    """Fine-grained verification status of a legal facet in the answer."""
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED_BUT_NOT_FOUND = "REQUESTED_BUT_NOT_FOUND"
    EVIDENCE_FOUND_NOT_ANSWERED = "EVIDENCE_FOUND_NOT_ANSWERED"
    ANSWERED_UNSUPPORTED = "ANSWERED_UNSUPPORTED"
    ANSWERED_SUPPORTED = "ANSWERED_SUPPORTED"
    ANSWERED_SUPPORTED_AND_CITED = "ANSWERED_SUPPORTED_AND_CITED"


class CaseLawStatus(str, Enum):
    """Availability and coverage status of judicial case law in the corpus (Phase 22)."""
    NOT_REQUESTED = "NOT_REQUESTED"
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    CORPUS_UNAVAILABLE = "CORPUS_UNAVAILABLE"


class FinalQualityStatus(str, Enum):
    """Overall answer quality classification after claim-to-evidence validation."""
    COMPLETE = "COMPLETE"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class FacetEvidenceSource:
    """Exact statutory chunk providing proof for a specific legal facet."""
    act: str
    section: str
    section_title: str
    page: str
    chunk_id: str
    text_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "act": self.act,
            "section": self.section,
            "section_title": self.section_title,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "text_snippet": self.text_snippet[:300] if self.text_snippet else "",
        }


@dataclass
class FacetEvidence:
    """Retrieved evidence object backing a legal information facet."""
    facet: str
    display_name: str
    required: bool
    evidence_status: EvidenceStatus = EvidenceStatus.NOT_FOUND
    supported: bool = False
    support_score: float = 0.0
    sources: List[FacetEvidenceSource] = field(default_factory=list)
    evidence_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet": self.facet,
            "display_name": self.display_name,
            "required": self.required,
            "evidence_status": self.evidence_status.value if isinstance(self.evidence_status, Enum) else str(self.evidence_status),
            "supported": self.supported,
            "support_score": round(self.support_score, 2),
            "sources": [s.to_dict() for s in self.sources],
            "evidence_text": self.evidence_text[:400] if self.evidence_text else "",
            "source_sections": [s.section for s in self.sources if s.section],
        }


@dataclass
class LegalClaim:
    """Substantive assertion extracted from a generated legal answer."""
    claim_text: str
    facet: str
    section_reference: Optional[str] = None
    act_reference: Optional[str] = None
    citation_label: Optional[str] = None  # e.g., "[Source 1]" or "[Case Source 1]"
    is_negative_claim: bool = False       # True if claiming evidence is missing/unavailable
    source_required: bool = True
    evidence_type_required: str = "STATUTE"  # "STATUTE" or "CASE_LAW"
    case_reference: Optional[str] = None     # e.g., "Pramod Suryabhan Pawar"
    court_reference: Optional[str] = None    # e.g., "Supreme Court"
    paragraph_reference: Optional[str] = None # e.g., "16"

    @property
    def is_judicial(self) -> bool:
        return self.evidence_type_required == "CASE_LAW" or bool(self.case_reference) or bool(self.court_reference)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "facet": self.facet,
            "section_reference": self.section_reference,
            "act_reference": self.act_reference,
            "citation_label": self.citation_label,
            "is_negative_claim": self.is_negative_claim,
            "source_required": self.source_required,
            "evidence_type_required": self.evidence_type_required,
            "case_reference": self.case_reference,
            "court_reference": self.court_reference,
            "paragraph_reference": self.paragraph_reference,
        }


@dataclass
class ClaimValidationResult:
    """Outcome of validating a single substantive legal claim against retrieved evidence."""
    claim: str
    facet: str
    supported: bool
    source: Optional[Dict[str, Any]] = None
    citation_valid: bool = True
    is_negative_claim: bool = False
    negative_claim_valid: bool = True
    reason: str = ""
    evidence_type: str = "STATUTE"
    is_judicial_claim: bool = False
    is_fabricated_case_law: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "facet": self.facet,
            "supported": self.supported,
            "source": self.source,
            "citation_valid": self.citation_valid,
            "is_negative_claim": self.is_negative_claim,
            "negative_claim_valid": self.negative_claim_valid,
            "reason": self.reason,
            "evidence_type": self.evidence_type,
            "is_judicial_claim": self.is_judicial_claim,
            "is_fabricated_case_law": self.is_fabricated_case_law,
        }
