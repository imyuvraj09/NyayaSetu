"""Research Data Schemas for Fact-First Legal Issue Routing.

Provides typed dataclasses, enums, and serialization for:
1. ExtractedFacts (unprocessed factual structure, strictly preserving uncertainty)
2. NormalizedFacts (canonicalized legal actions, objects, and terms with provenance)
3. IdentifiedLegalIssue (inferred multi-issue legal hypotheses with evidence)
4. CandidateLegalRegime (scored target legal regimes with supporting signals)
5. RoutingDecision (traceable confidence-aware routing plan)
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RoutingMode(str, Enum):
    """Execution mode determined by routing confidence estimation."""

    HIGH_CONFIDENCE = "high_confidence"
    MEDIUM_CONFIDENCE_SOFT_BOOST = "medium_confidence_soft_boost"
    LOW_CONFIDENCE_FALLBACK = "low_confidence_fallback"
    AMBIGUOUS_FALLBACK = "ambiguous_fallback"
    DISABLED = "disabled"


@dataclass
class ExtractedFacts:
    """Explicitly observed factual structure extracted from citizen or legal query.

    CRITICAL RULE:
    Zero hallucination. If an actor, object, temporal cue, or relationship is not
    explicitly stated in the query text, the field MUST remain empty or None.
    """

    actors: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    temporal_context: Optional[str] = None
    location_context: Optional[str] = None
    relationships: List[str] = field(default_factory=list)
    explicit_legal_terms: List[str] = field(default_factory=list)
    jurisdiction: Optional[str] = None
    statutory_references: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if any factual evidence was extracted."""
        return not (
            self.actors
            or self.actions
            or self.objects
            or self.events
            or self.temporal_context
            or self.location_context
            or self.relationships
            or self.explicit_legal_terms
            or self.statutory_references
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedFactItem:
    """A single canonicalized factual item with full provenance tracing."""

    category: str  # e.g., "action", "object", "legal_term", "actor", "temporal"
    original_value: str
    canonical_value: str
    normalization_source: str  # e.g., "synonym_lexicon", "statutory_term_map", "regex_canonicalizer"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedFacts:
    """Normalized factual representations preserving raw evidence."""

    items: List[NormalizedFactItem] = field(default_factory=list)
    raw_facts: Optional[ExtractedFacts] = None

    @property
    def canonical_actions(self) -> List[str]:
        return [i.canonical_value for i in self.items if i.category == "action"]

    @property
    def canonical_objects(self) -> List[str]:
        return [i.canonical_value for i in self.items if i.category == "object"]

    @property
    def canonical_terms(self) -> List[str]:
        return [i.canonical_value for i in self.items if i.category == "legal_term"]

    @property
    def canonical_actors(self) -> List[str]:
        return [i.canonical_value for i in self.items if i.category == "actor"]

    @property
    def canonical_statutes(self) -> List[str]:
        return [i.canonical_value for i in self.items if i.category == "statutory_reference"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "raw_facts": self.raw_facts.to_dict() if self.raw_facts else None,
            "summary": {
                "actions": self.canonical_actions,
                "objects": self.canonical_objects,
                "terms": self.canonical_terms,
                "statutes": self.canonical_statutes,
            },
        }


@dataclass
class IdentifiedLegalIssue:
    """Inferred legal issue candidate supported by factual evidence."""

    issue_id: str
    issue_name: str
    confidence: float
    supporting_facts: List[str] = field(default_factory=list)
    reasoning_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateLegalRegime:
    """A target legal regime scored for retrieval scoping."""

    regime_id: str
    regime_name: str
    confidence: float
    supporting_signals: List[str] = field(default_factory=list)
    priority_boost: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingDecision:
    """Traceable, confidence-aware decision guiding multi-statute retrieval."""

    selected_regimes: List[str]
    routing_mode: RoutingMode
    confidence: float
    fallback_used: bool
    routing_reason: List[str] = field(default_factory=list)
    candidate_distribution: Dict[str, float] = field(default_factory=dict)
    candidate_regimes: List[CandidateLegalRegime] = field(default_factory=list)
    identified_issues: List[IdentifiedLegalIssue] = field(default_factory=list)
    normalized_facts: Optional[NormalizedFacts] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_regimes": self.selected_regimes,
            "routing_mode": self.routing_mode.value,
            "confidence": round(self.confidence, 4),
            "fallback_used": self.fallback_used,
            "routing_reason": self.routing_reason,
            "candidate_distribution": {k: round(v, 4) for k, v in self.candidate_distribution.items()},
            "candidate_regimes": [r.to_dict() for r in self.candidate_regimes],
            "identified_issues": [i.to_dict() for i in self.identified_issues],
            "normalized_facts": self.normalized_facts.to_dict() if self.normalized_facts else None,
        }
