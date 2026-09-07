"""Typed Data Models and Enums for Phase 4 Evidence Compatibility Filtering.

Provides structured, auditable, and explainable representations for:
1. CompatibilityStatus (COMPATIBLE, PARTIALLY_COMPATIBLE, UNCERTAIN, INCOMPATIBLE)
2. LegalRole (SUBSTANTIVE, PROCEDURAL, EVIDENTIARY, CONSTITUTIONAL, SPECIAL_LAW, GENERAL_LAW)
3. TemporalStatus (APPLICABLE, REPEALED, SUPERSEDED, PENDING_ENACTMENT, UNKNOWN)
4. EvidenceRelationshipType (SUPPORTS, COMPLEMENTS, PROCEDURALLY_SUPPORTS,
   EVIDENTIALLY_SUPPORTS, CONFLICTS, TEMPORALLY_CONFLICTS, DUPLICATES, UNRELATED)
5. CompatibilityViolation (Audit record for incompatible signals)
6. CompatibilityScore (Dimensional breakdown of compatibility metrics)
7. EvidenceRelationship (Cross-chunk doctrinal link)
8. CompatibilityDecision (Per-chunk evaluation record)
9. CompatibilityResult (Collection-level evaluation summary)
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompatibilityStatus(str, Enum):
    """Evaluation status for evidence compatibility."""

    COMPATIBLE = "COMPATIBLE"
    PARTIALLY_COMPATIBLE = "PARTIALLY_COMPATIBLE"
    UNCERTAIN = "UNCERTAIN"
    INCOMPATIBLE = "INCOMPATIBLE"


class LegalRole(str, Enum):
    """Doctrinal function and classification of a statutory provision."""

    SUBSTANTIVE = "SUBSTANTIVE"
    PROCEDURAL = "PROCEDURAL"
    EVIDENTIARY = "EVIDENTIARY"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    SPECIAL_LAW = "SPECIAL_LAW"
    GENERAL_LAW = "GENERAL_LAW"
    UNKNOWN = "UNKNOWN"


class TemporalStatus(str, Enum):
    """Temporal validity and applicability status of retrieved legal text."""

    APPLICABLE = "APPLICABLE"
    REPEALED = "REPEALED"
    SUPERSEDED = "SUPERSEDED"
    PENDING_ENACTMENT = "PENDING_ENACTMENT"
    UNKNOWN = "UNKNOWN"


class EvidenceRelationshipType(str, Enum):
    """Categorization of inter-chunk evidentiary and doctrinal relationships."""

    SUPPORTS = "SUPPORTS"
    COMPLEMENTS = "COMPLEMENTS"
    PROCEDURALLY_SUPPORTS = "PROCEDURALLY_SUPPORTS"
    EVIDENTIALLY_SUPPORTS = "EVIDENTIALLY_SUPPORTS"
    CONFLICTS = "CONFLICTS"
    TEMPORALLY_CONFLICTS = "TEMPORALLY_CONFLICTS"
    DUPLICATES = "DUPLICATES"
    UNRELATED = "UNRELATED"


@dataclass
class CompatibilityViolation:
    """Explicit audit record of a doctrinal, temporal, or regime mismatch."""

    dimension: str  # e.g., "regime", "issue", "legal_role", "temporal", "special_general"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    rule_name: str
    message: str
    penalty: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompatibilityScore:
    """Detailed score breakdown across all independent compatibility dimensions."""

    regime_score: float = 1.0
    issue_score: float = 1.0
    legal_role_score: float = 1.0
    temporal_score: float = 1.0
    special_general_score: float = 1.0
    relationship_score: float = 1.0
    total_score: float = 1.0
    soft_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime_score": round(self.regime_score, 4),
            "issue_score": round(self.issue_score, 4),
            "legal_role_score": round(self.legal_role_score, 4),
            "temporal_score": round(self.temporal_score, 4),
            "special_general_score": round(self.special_general_score, 4),
            "relationship_score": round(self.relationship_score, 4),
            "total_score": round(self.total_score, 4),
            "soft_multiplier": round(self.soft_multiplier, 4),
        }


@dataclass
class EvidenceRelationship:
    """Inter-chunk doctrinal relationship between retrieved evidence items."""

    source_chunk_id: str
    target_chunk_id: str
    relationship_type: EvidenceRelationshipType
    confidence: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_chunk_id": self.source_chunk_id,
            "target_chunk_id": self.target_chunk_id,
            "relationship_type": self.relationship_type.value,
            "confidence": round(self.confidence, 4),
            "description": self.description,
        }


@dataclass
class CompatibilityDecision:
    """Auditable compatibility decision for a single retrieved chunk."""

    chunk_id: str
    document_name: str
    section: Optional[str]
    source_regime: str
    compatibility_score: float
    compatibility_status: CompatibilityStatus
    violations: List[CompatibilityViolation] = field(default_factory=list)
    supporting_signals: List[str] = field(default_factory=list)
    rejected_signals: List[str] = field(default_factory=list)
    temporal_status: TemporalStatus = TemporalStatus.UNKNOWN
    legal_role: LegalRole = LegalRole.UNKNOWN
    substantive_compatibility: float = 1.0
    procedural_compatibility: float = 1.0
    issue_compatibility: float = 1.0
    regime_compatibility: float = 1.0
    special_general_compatibility: float = 1.0
    score_breakdown: Optional[CompatibilityScore] = None
    hard_excluded: bool = False
    exclusion_reason: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_name": self.document_name,
            "section": self.section,
            "source_regime": self.source_regime,
            "compatibility_score": round(self.compatibility_score, 4),
            "compatibility_status": self.compatibility_status.value,
            "violations": [v.to_dict() for v in self.violations],
            "supporting_signals": self.supporting_signals,
            "rejected_signals": self.rejected_signals,
            "temporal_status": self.temporal_status.value,
            "legal_role": self.legal_role.value,
            "substantive_compatibility": round(self.substantive_compatibility, 4),
            "procedural_compatibility": round(self.procedural_compatibility, 4),
            "issue_compatibility": round(self.issue_compatibility, 4),
            "regime_compatibility": round(self.regime_compatibility, 4),
            "special_general_compatibility": round(self.special_general_compatibility, 4),
            "score_breakdown": self.score_breakdown.to_dict() if self.score_breakdown else None,
            "hard_excluded": self.hard_excluded,
            "exclusion_reason": self.exclusion_reason,
            "reasoning": self.reasoning,
        }


@dataclass
class CompatibilityResult:
    """Aggregate result from evidence compatibility filtering on candidate pool."""

    query: str
    total_candidates: int
    compatible_count: int
    partially_compatible_count: int
    uncertain_count: int
    incompatible_count: int
    hard_excluded_count: int
    decisions: List[CompatibilityDecision] = field(default_factory=list)
    relationships: List[EvidenceRelationship] = field(default_factory=list)
    regime_coherence_score: float = 1.0
    execution_time_sec: float = 0.0

    def get_decision_map(self) -> Dict[str, CompatibilityDecision]:
        return {d.chunk_id: d for d in self.decisions}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_candidates": self.total_candidates,
            "compatible_count": self.compatible_count,
            "partially_compatible_count": self.partially_compatible_count,
            "uncertain_count": self.uncertain_count,
            "incompatible_count": self.incompatible_count,
            "hard_excluded_count": self.hard_excluded_count,
            "regime_coherence_score": round(self.regime_coherence_score, 4),
            "execution_time_sec": round(self.execution_time_sec, 6),
            "decisions": [d.to_dict() for d in self.decisions],
            "relationships": [r.to_dict() for r in self.relationships],
        }
