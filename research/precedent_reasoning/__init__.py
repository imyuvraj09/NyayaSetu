"""NyayaSetu Judicial Precedent Retrieval and Authority-Aware Reasoning Package (Phase 7)."""

from research.precedent_reasoning.authority_classifier import (
    PrecedentAuthorityClassifier,
)
from research.precedent_reasoning.authority_ranker import AuthorityAwareRanker
from research.precedent_reasoning.case_retriever import PrecedentRetriever
from research.precedent_reasoning.citation_graph import PrecedentCitationGraph
from research.precedent_reasoning.conflict_detector import (
    PrecedentConflictDetector,
)
from research.precedent_reasoning.court_hierarchy import (
    HIGH_COURT_TERRITORIES,
    CourtHierarchyEngine,
)
from research.precedent_reasoning.engine import (
    PrecedentReasoningEngine,
    get_precedent_reasoning_engine,
)
from research.precedent_reasoning.jurisdiction_checker import (
    JurisdictionChecker,
)
from research.precedent_reasoning.metadata_extractor import (
    PrecedentMetadataExtractor,
)
from research.precedent_reasoning.models import (
    AuthorityAssessment,
    AuthorityStatus,
    BenchStrength,
    ConflictStatus,
    CourtLevel,
    JudicialPrecedent,
    JurisdictionAssessment,
    JurisdictionRelevance,
    PrecedentConflict,
    PrecedentMetadata,
    PrecedentRankingDecision,
    PrecedentReasoningResult,
    PrecedentRelationship,
    PrecedentRelationshipType,
    PrecedentTemporalStatus,
)
from research.precedent_reasoning.precedent_relationship_analyzer import (
    PrecedentRelationshipAnalyzer,
)
from research.precedent_reasoning.precedent_synthesizer import (
    PrecedentSynthesizer,
)
from research.precedent_reasoning.statute_precedent_checker import (
    StatutePrecedentChecker,
)
from research.precedent_reasoning.temporal_validator import (
    PrecedentTemporalValidator,
)

__all__ = [
    "CourtLevel",
    "AuthorityStatus",
    "JurisdictionRelevance",
    "PrecedentRelationshipType",
    "PrecedentTemporalStatus",
    "ConflictStatus",
    "BenchStrength",
    "PrecedentMetadata",
    "JudicialPrecedent",
    "AuthorityAssessment",
    "JurisdictionAssessment",
    "PrecedentRelationship",
    "PrecedentConflict",
    "PrecedentRankingDecision",
    "PrecedentReasoningResult",
    "CourtHierarchyEngine",
    "HIGH_COURT_TERRITORIES",
    "PrecedentMetadataExtractor",
    "PrecedentRetriever",
    "PrecedentAuthorityClassifier",
    "JurisdictionChecker",
    "PrecedentTemporalValidator",
    "PrecedentRelationshipAnalyzer",
    "PrecedentCitationGraph",
    "PrecedentConflictDetector",
    "StatutePrecedentChecker",
    "AuthorityAwareRanker",
    "PrecedentSynthesizer",
    "PrecedentReasoningEngine",
    "get_precedent_reasoning_engine",
]
