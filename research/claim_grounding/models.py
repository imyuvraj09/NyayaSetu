"""Structured data models for Phase 5 Answer Claim Grounding & Citation Verification.

Defines enums and dataclasses for atomic claims, evidence matches,
citation verification results, grounding decisions, and answer-level results.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ClaimStatus(str, Enum):
    """Evidential support status for an atomic claim."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ClaimType(str, Enum):
    """Legal and structural role of an atomic claim."""

    LEGAL_RULE = "LEGAL_RULE"
    STATUTORY_PROVISION = "STATUTORY_PROVISION"
    LEGAL_CONSEQUENCE = "LEGAL_CONSEQUENCE"
    PUNISHMENT = "PUNISHMENT"
    PROCEDURAL_REQUIREMENT = "PROCEDURAL_REQUIREMENT"
    EVIDENTIARY_REQUIREMENT = "EVIDENTIARY_REQUIREMENT"
    LEGAL_INTERPRETATION = "LEGAL_INTERPRETATION"
    FACTUAL_APPLICATION = "FACTUAL_APPLICATION"
    TEMPORAL_CLAIM = "TEMPORAL_CLAIM"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"


class CitationStatus(str, Enum):
    """Status of an attached citation."""

    VALID_CITATION = "VALID_CITATION"
    MISALIGNED_CITATION = "MISALIGNED_CITATION"
    UNSUPPORTED_CITATION = "UNSUPPORTED_CITATION"
    MISSING_CITATION = "MISSING_CITATION"
    INVALID_SOURCE = "INVALID_SOURCE"


class RiskLevel(str, Enum):
    """Risk severity of an unsupported claim."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClaimHandlingAction(str, Enum):
    """Action taken by the answer validator on an atomic claim."""

    RETAIN = "RETAIN"
    QUALIFY = "QUALIFY"
    REMOVE = "REMOVE"
    ABSTAIN = "ABSTAIN"
    FLAG_UNCERTAIN = "FLAG_UNCERTAIN"


@dataclass
class AttachedCitation:
    """A citation reference parsed from claim text."""

    raw_text: str
    statute: Optional[str] = None
    section: Optional[str] = None
    source_index: Optional[int] = None
    span_start: int = 0
    span_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AtomicClaim:
    """An atomic, independently verifiable proposition extracted from an answer."""

    claim_id: str
    claim_text: str
    claim_type: ClaimType
    source_span_start: int
    source_span_end: int
    importance_weight: float = 1.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    attached_citations: List[AttachedCitation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["claim_type"] = self.claim_type.value
        d["risk_level"] = self.risk_level.value
        return d


@dataclass
class ClaimEvidenceMatch:
    """A retrieved chunk candidate evaluated against an atomic claim."""

    claim_id: str
    chunk_id: str
    statute: str
    section: str
    source_identifier: str
    match_score: float
    evidence_text: str
    support_status: ClaimStatus
    entailment_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["support_status"] = self.support_status.value
        return d


@dataclass
class CitationVerificationResult:
    """Audit record for a citation verification check."""

    claim_id: str
    citation_text: str
    status: CitationStatus
    target_statute: Optional[str] = None
    target_section: Optional[str] = None
    matched_chunk_id: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ClaimGroundingDecision:
    """Grounding evaluation and mitigation decision for a single atomic claim."""

    claim: AtomicClaim
    status: ClaimStatus
    support_score: float
    best_evidence_match: Optional[ClaimEvidenceMatch] = None
    citation_results: List[CitationVerificationResult] = field(default_factory=list)
    handling_action: ClaimHandlingAction = ClaimHandlingAction.RETAIN
    qualified_claim_text: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "claim": self.claim.to_dict(),
            "status": self.status.value,
            "support_score": self.support_score,
            "best_evidence_match": self.best_evidence_match.to_dict() if self.best_evidence_match else None,
            "citation_results": [c.to_dict() for c in self.citation_results],
            "handling_action": self.handling_action.value,
            "qualified_claim_text": self.qualified_claim_text,
            "reasoning": self.reasoning,
        }
        return d


@dataclass
class GenerationMetadata:
    """Provenance metadata regarding the generator that produced the answer."""

    generation_provider: str = "unknown"
    generation_mode: str = "standard"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    is_mock_generation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnswerGroundingResult:
    """Complete answer-level claim grounding and citation verification audit result."""

    original_answer: str
    validated_answer: str
    claims: List[AtomicClaim]
    decisions: List[ClaimGroundingDecision]
    grounding_score: float
    high_risk_error_count: int
    unsupported_claim_count: int
    contradicted_claim_count: int
    citation_accuracy: float
    citation_completeness: float
    generation_metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    latency_ms: float = 0.0
    modifications_made: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_answer": self.original_answer,
            "validated_answer": self.validated_answer,
            "claims": [c.to_dict() for c in self.claims],
            "decisions": [d.to_dict() for d in self.decisions],
            "grounding_score": self.grounding_score,
            "high_risk_error_count": self.high_risk_error_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "contradicted_claim_count": self.contradicted_claim_count,
            "citation_accuracy": self.citation_accuracy,
            "citation_completeness": self.citation_completeness,
            "generation_metadata": self.generation_metadata.to_dict(),
            "latency_ms": self.latency_ms,
            "modifications_made": self.modifications_made,
        }
