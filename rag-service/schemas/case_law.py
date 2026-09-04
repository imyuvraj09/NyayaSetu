"""
Case-law document, chunk, and evidence type schemas for NyayaSetu.

Defines:
- EvidenceType: Strict evidence classification (STATUTE, CASE_LAW, etc.)
- CourtLevel: Authority hierarchy (SUPREME_COURT, HIGH_COURT, OTHER)
- CaseLawDocument: Authoritative judgment record
- CaseLawChunk: Paragraph-aware judgment chunk with provenance
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Strict authority evidence classification."""
    STATUTE = "STATUTE"
    CASE_LAW = "CASE_LAW"
    RULE = "RULE"
    REGULATION = "REGULATION"
    NOTIFICATION = "NOTIFICATION"
    SECONDARY_SOURCE = "SECONDARY_SOURCE"
    UNKNOWN = "UNKNOWN"


class CourtLevel(str, Enum):
    """Judicial hierarchy level for authoritative weighting."""
    SUPREME_COURT = "SUPREME_COURT"
    HIGH_COURT = "HIGH_COURT"
    OTHER = "OTHER"


class PassageType(str, Enum):
    """Classification of passage content within a judicial decision."""
    HOLDING = "HOLDING"
    RATIO = "RATIO"
    STATUTORY_INTERPRETATION = "STATUTORY_INTERPRETATION"
    LEGAL_TEST = "LEGAL_TEST"
    FACTUAL_BACKGROUND = "FACTUAL_BACKGROUND"
    PROCEDURAL_HISTORY = "PROCEDURAL_HISTORY"
    CONCLUSION = "CONCLUSION"
    GENERAL = "GENERAL"


class CaseLawDocument(BaseModel):
    """Authoritative judicial decision record."""
    document_id: str = Field(..., description="Unique case document identifier")
    evidence_type: EvidenceType = Field(default=EvidenceType.CASE_LAW, description="Always CASE_LAW for judgments")
    case_name: str = Field(..., description="Official case title (e.g. Pramod Suryabhan Pawar v. State of Maharashtra)")
    court: str = Field(..., description="Court name (e.g. Supreme Court of India)")
    court_level: CourtLevel = Field(default=CourtLevel.SUPREME_COURT, description="Court hierarchy level")
    citation: str = Field(..., description="Official reporter citation (e.g. (2019) 9 SCC 608)")
    judgment_date: str = Field(..., description="ISO format judgment date (YYYY-MM-DD)")
    case_number: Optional[str] = Field(default=None, description="Official appeal / petition number")
    bench: List[str] = Field(default_factory=list, description="Bench judges")
    statutes_referred: List[str] = Field(default_factory=list, description="Statutes discussed in the judgment")
    sections_referred: List[str] = Field(default_factory=list, description="Sections discussed in the judgment")
    topics: List[str] = Field(default_factory=list, description="Legal subject topics")
    source_url: str = Field(..., description="Official court or authoritative repository URL")
    source_name: str = Field(default="Supreme Court of India / Official Reports", description="Authoritative source name")
    verified: bool = Field(default=True, description="Strict verification status")
    summary: Optional[str] = Field(default=None, description="Concise case summary / headnote")
    overruled_or_distinguished: Optional[str] = Field(default=None, description="Subsequent status if modified or distinguished")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CaseLawChunk(BaseModel):
    """Paragraph-aware chunk of an authoritative judicial decision."""
    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. sc_2019_pawar_p0016)")
    document_id: str = Field(..., description="Foreign key to parent CaseLawDocument")
    evidence_type: EvidenceType = Field(default=EvidenceType.CASE_LAW, description="Always CASE_LAW")
    case_name: str = Field(..., description="Case title")
    court: str = Field(..., description="Court name")
    court_level: CourtLevel = Field(default=CourtLevel.SUPREME_COURT, description="Court level")
    citation: str = Field(..., description="Official citation")
    judgment_date: str = Field(..., description="Judgment date (YYYY-MM-DD)")
    paragraph_number: str = Field(..., description="Numbered paragraph or passage identifier (e.g. '16')")
    paragraph_heading: Optional[str] = Field(default=None, description="Section or paragraph heading if present")
    passage_type: PassageType = Field(default=PassageType.GENERAL, description="Type of passage")
    text: str = Field(..., description="Verbatim text of the judgment paragraph")
    statutes_referred: List[str] = Field(default_factory=list, description="Statutes discussed in this paragraph")
    sections_referred: List[str] = Field(default_factory=list, description="Sections discussed in this paragraph")
    topics: List[str] = Field(default_factory=list, description="Legal topics addressed in this paragraph")
    is_holding_or_ratio: bool = Field(default=False, description="True if passage contains ratio decidendi or core holding")
    verified: bool = Field(default=True, description="Source provenance verification")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
