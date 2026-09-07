"""Phase 4: Evidence Compatibility Filtering for NyayaSetu Legal RAG.

Exported Classes and Functions:
- EvidenceCompatibilityEngine, get_evidence_compatibility_engine
- CompatibilityDecision, CompatibilityResult, CompatibilityScore, CompatibilityViolation
- CompatibilityStatus, LegalRole, TemporalStatus, EvidenceRelationshipType, EvidenceRelationship
- RegimeCompatibilityChecker
- IssueCompatibilityChecker
- LegalRoleCompatibilityChecker
- TemporalCompatibilityChecker
- SpecialGeneralCompatibilityChecker
- EvidenceRelationshipAnalyzer
- CompatibilityScorer
"""

from research.evidence_compatibility.engine import (
    EvidenceCompatibilityEngine,
    get_evidence_compatibility_engine,
)
from research.evidence_compatibility.issue_checker import IssueCompatibilityChecker
from research.evidence_compatibility.legal_role_checker import LegalRoleCompatibilityChecker
from research.evidence_compatibility.models import (
    CompatibilityDecision,
    CompatibilityResult,
    CompatibilityScore,
    CompatibilityStatus,
    CompatibilityViolation,
    EvidenceRelationship,
    EvidenceRelationshipType,
    LegalRole,
    TemporalStatus,
)
from research.evidence_compatibility.regime_checker import RegimeCompatibilityChecker
from research.evidence_compatibility.relationship_analyzer import EvidenceRelationshipAnalyzer
from research.evidence_compatibility.scoring import CompatibilityScorer
from research.evidence_compatibility.special_general_checker import SpecialGeneralCompatibilityChecker
from research.evidence_compatibility.temporal_checker import TemporalCompatibilityChecker

__all__ = [
    "EvidenceCompatibilityEngine",
    "get_evidence_compatibility_engine",
    "CompatibilityDecision",
    "CompatibilityResult",
    "CompatibilityScore",
    "CompatibilityViolation",
    "CompatibilityStatus",
    "LegalRole",
    "TemporalStatus",
    "EvidenceRelationshipType",
    "EvidenceRelationship",
    "RegimeCompatibilityChecker",
    "IssueCompatibilityChecker",
    "LegalRoleCompatibilityChecker",
    "TemporalCompatibilityChecker",
    "SpecialGeneralCompatibilityChecker",
    "EvidenceRelationshipAnalyzer",
    "CompatibilityScorer",
]
