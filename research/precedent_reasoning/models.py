"""Typed Data Models and Enums for Phase 7 Judicial Precedent Reasoning.

Defines structured, evidence-grounded abstractions for:
- CourtLevel & Indian Court Hierarchy
- AuthorityStatus & Article 141 Constitutional Weighting
- JurisdictionRelevance & Territorial Alignment
- PrecedentRelationshipType & Treatment Tracking
- PrecedentTemporalStatus & Conservative Overruling
- ConflictStatus & Doctrinal Reconciliation
- PrecedentMetadata, JudicialPrecedent, AuthorityAssessment, JurisdictionAssessment
- PrecedentRelationship, PrecedentConflict, PrecedentRankingDecision
- PrecedentReasoningResult
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CourtLevel(str, Enum):
    """Hierarchy level of Indian courts and tribunals."""

    SUPREME_COURT = "SUPREME_COURT"
    HIGH_COURT = "HIGH_COURT"
    TRIBUNAL = "TRIBUNAL"
    DISTRICT_COURT = "DISTRICT_COURT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class AuthorityStatus(str, Enum):
    """Legal authority classification of a precedent for a target query."""

    BINDING = "BINDING"  # e.g., Supreme Court ratio under Article 141
    HIGHLY_PERSUASIVE = "HIGHLY_PERSUASIVE"  # e.g., High Court of same jurisdiction or larger bench
    PERSUASIVE = "PERSUASIVE"  # e.g., High Court of another state
    LIMITED_AUTHORITY = "LIMITED_AUTHORITY"  # e.g., Single judge decision, obiter, or questioned
    UNKNOWN = "UNKNOWN"  # Missing court or authority metadata


class JurisdictionRelevance(str, Enum):
    """Territorial and subject-matter jurisdictional alignment."""

    DIRECTLY_RELEVANT = "DIRECTLY_RELEVANT"  # National jurisdiction (SC) or home state HC
    GENERALLY_RELEVANT = "GENERALLY_RELEVANT"  # Central statute interpreted by another HC
    PERSUASIVE = "PERSUASIVE"  # Outside territorial jurisdiction but persuasive on common law
    OUTSIDE_PRIMARY_JURISDICTION = "OUTSIDE_PRIMARY_JURISDICTION"  # Foreign or inapposite jurisdiction
    UNKNOWN = "UNKNOWN"  # User or precedent jurisdiction unspecified


class PrecedentRelationshipType(str, Enum):
    """Inter-precedent citation and subsequent judicial treatment types."""

    FOLLOWED = "FOLLOWED"  # Subsequent court explicitly adopts the reasoning
    APPLIED = "APPLIED"  # Principle extended to analogous factual matrix
    RELIED_ON = "RELIED_ON"  # Cited with approval as supporting ratio
    DISTINGUISHED = "DISTINGUISHED"  # Principle held inapplicable due to material factual difference
    QUESTIONED = "QUESTIONED"  # Doubted or referred to a larger bench
    OVERRULED = "OVERRULED"  # Formally invalidated by superior court or larger bench
    PARTIALLY_OVERRULED = "PARTIALLY_OVERRULED"  # Specific proposition invalidated while remainder stands
    NOT_CONSIDERED = "NOT_CONSIDERED"  # Parallel decision without consideration
    UNKNOWN = "UNKNOWN"  # No explicit subsequent treatment recorded in corpus


class PrecedentTemporalStatus(str, Enum):
    """Temporal validity of a precedent."""

    APPLICABLE = "APPLICABLE"  # Currently valid and unreversed law
    POTENTIALLY_SUPERSEDED = "POTENTIALLY_SUPERSEDED"  # Governing statute subsequently repealed/amended
    OVERRULED = "OVERRULED"  # Explicitly overruled by subsequent judicial authority
    UNKNOWN = "UNKNOWN"  # Temporal validity cannot be established from corpus evidence


class ConflictStatus(str, Enum):
    """Conflict status between multiple retrieved precedents."""

    NO_CONFLICT = "NO_CONFLICT"  # Harmonious or addressing distinct questions
    POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"  # Divergent propositions by coordinate benches
    RESOLVED_BY_AUTHORITY = "RESOLVED_BY_AUTHORITY"  # Resolved by higher court hierarchy or larger bench
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Cannot confirm or deny conflict from available context


class BenchStrength(str, Enum):
    """Bench composition in Indian judicial hierarchy."""

    CONSTITUTION_BENCH = "CONSTITUTION_BENCH"  # 5 or more judges
    LARGER_BENCH = "LARGER_BENCH"  # 3 judges
    DIVISION_BENCH = "DIVISION_BENCH"  # 2 judges
    SINGLE_JUDGE = "SINGLE_JUDGE"  # 1 judge
    UNKNOWN = "UNKNOWN"


@dataclass
class PrecedentMetadata:
    """Structured, verified metadata for a judicial decision."""

    case_name: str
    court: str
    court_level: CourtLevel
    citation: str
    judgment_date: str
    jurisdiction: str = "India"
    bench: List[str] = field(default_factory=list)
    bench_strength: BenchStrength = BenchStrength.UNKNOWN
    statutes_referred: List[str] = field(default_factory=list)
    sections_referred: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    overruled_by: Optional[str] = None
    overruled_in_part_by: Optional[str] = None
    distinguished_by: List[str] = field(default_factory=list)
    followed_by: List[str] = field(default_factory=list)
    source_identifier: str = "verified_corpus"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["court_level"] = self.court_level.value if hasattr(self.court_level, "value") else str(self.court_level)
        d["bench_strength"] = self.bench_strength.value if hasattr(self.bench_strength, "value") else str(self.bench_strength)
        return d


@dataclass
class JudicialPrecedent:
    """A retrieved judicial decision or passage with extracted legal metadata."""

    chunk_id: str
    document_id: str
    case_name: str
    citation: str
    court: str
    court_level: CourtLevel
    judgment_date: str
    passage_type: str  # "HOLDING", "RATIO", "LEGAL_TEST", "STATUTORY_INTERPRETATION", "GENERAL"
    text: str
    is_holding_or_ratio: bool
    retrieval_score: float
    metadata: Optional[PrecedentMetadata] = None
    statutes_referred: List[str] = field(default_factory=list)
    sections_referred: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = PrecedentMetadata(
                case_name=self.case_name,
                court=self.court,
                court_level=self.court_level,
                citation=self.citation,
                judgment_date=self.judgment_date,
                statutes_referred=list(self.statutes_referred),
                sections_referred=list(self.sections_referred),
                topics=list(self.topics),
            )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["court_level"] = self.court_level.value if hasattr(self.court_level, "value") else str(self.court_level)
        d["metadata"] = self.metadata.to_dict() if self.metadata else {}
        return d


@dataclass
class AuthorityAssessment:
    """Assessment of a precedent's binding or persuasive force."""

    precedent_id: str
    case_name: str
    court_level: CourtLevel
    authority_status: AuthorityStatus
    authority_score: float  # Bounded multiplier [0.5 to 1.3]
    bench_weight: float  # Multiplier for bench size
    binding_jurisdiction: str
    reasoning: str
    confidence: float
    article_141_binding: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["court_level"] = self.court_level.value
        d["authority_status"] = self.authority_status.value
        return d


@dataclass
class JurisdictionAssessment:
    """Assessment of territorial and subject-matter jurisdictional alignment."""

    precedent_id: str
    case_name: str
    target_jurisdiction: str
    precedent_jurisdiction: str
    jurisdiction_relevance: JurisdictionRelevance
    relevance_multiplier: float  # Bounded multiplier [0.7 to 1.1]
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["jurisdiction_relevance"] = self.jurisdiction_relevance.value
        return d


@dataclass
class PrecedentRelationship:
    """Explicit doctrinal or precedential relationship between two cases."""

    source_case: str
    target_case: str
    relationship_type: PrecedentRelationshipType
    evidence_text: str
    statute_context: Optional[str] = None
    confidence: float = 1.0
    is_explicit_in_corpus: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["relationship_type"] = self.relationship_type.value
        return d


@dataclass
class PrecedentConflict:
    """Detected conflict between two judicial decisions."""

    case_a: str
    case_b: str
    legal_issue: str
    position_a: str
    position_b: str
    conflict_status: ConflictStatus
    controlling_case: Optional[str] = None
    resolution_basis: Optional[str] = None  # e.g., "Supreme Court overrules High Court" or "Larger bench"
    distinguishing_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["conflict_status"] = self.conflict_status.value
        return d


@dataclass
class PrecedentRankingDecision:
    """Complete audit record of authority-aware re-ranking adjustments."""

    chunk_id: str
    case_name: str
    original_score: float
    authority_multiplier: float
    jurisdiction_multiplier: float
    compatibility_multiplier: float
    temporal_multiplier: float
    passage_multiplier: float
    final_score: float
    rank_before: int
    rank_after: int
    adjustment_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PrecedentReasoningResult:
    """Comprehensive result object from the Phase 7 Precedent Reasoning Engine."""

    query: str
    retrieved_precedents: List[JudicialPrecedent]
    ranked_precedents: List[JudicialPrecedent]
    ranking_decisions: List[PrecedentRankingDecision]
    authority_assessments: Dict[str, AuthorityAssessment]
    jurisdiction_assessments: Dict[str, JurisdictionAssessment]
    relationships: List[PrecedentRelationship]
    conflicts: List[PrecedentConflict]
    controlling_precedents: List[JudicialPrecedent] = field(default_factory=list)
    supporting_precedents: List[JudicialPrecedent] = field(default_factory=list)
    persuasive_precedents: List[JudicialPrecedent] = field(default_factory=list)
    conflicting_precedents: List[JudicialPrecedent] = field(default_factory=list)
    unknown_authority_precedents: List[JudicialPrecedent] = field(default_factory=list)
    statute_compatibility_scores: Dict[str, float] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    audit_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "precedents_count": len(self.ranked_precedents),
            "ranked_precedents": [p.to_dict() for p in self.ranked_precedents],
            "ranking_decisions": [d.to_dict() for d in self.ranking_decisions],
            "authority_assessments": {k: v.to_dict() for k, v in self.authority_assessments.items()},
            "jurisdiction_assessments": {k: v.to_dict() for k, v in self.jurisdiction_assessments.items()},
            "relationships": [r.to_dict() for r in self.relationships],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "controlling_count": len(self.controlling_precedents),
            "supporting_count": len(self.supporting_precedents),
            "persuasive_count": len(self.persuasive_precedents),
            "conflicts_count": len(self.conflicting_precedents),
            "unknown_count": len(self.unknown_authority_precedents),
            "execution_time_ms": round(self.execution_time_ms, 2),
            "audit_log": self.audit_log,
        }
