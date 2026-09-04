"""
Pydantic schemas for LLM answer generation in NyayaSetu RAG Service.

Defines the structure for source references, generation responses, and metadata.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Source provenance record associated with a generated legal answer."""

    source_label: str = Field(
        ...,
        description="Assigned label used in prompt context and citation (e.g. [SOURCE 1])",
        examples=["[SOURCE 1]"],
    )
    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier from legal_chunks.jsonl",
        examples=["bns_2023_c0384"],
    )
    document_name: str = Field(
        ...,
        description="Canonical Indian statutory enactment name",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: str = Field(
        default="Unknown",
        description="Legal domain classification",
        examples=["Criminal Law"],
    )
    source_filename: str = Field(
        default="",
        description="Original source PDF file name",
        examples=["bns_2023.pdf"],
    )
    page_numbers: List[int] = Field(
        default_factory=list,
        description="Source PDF page numbers containing this passage",
        examples=[[82]],
    )
    similarity_score: float = Field(
        ...,
        description="Initial dense retrieval cosine score",
        examples=[0.8252],
    )
    reranker_score: float = Field(
        ...,
        description="Cross-encoder relevance score",
        examples=[0.9996],
    )
    text_snippet: str = Field(
        ...,
        description="Excerpt or full text of the statutory passage",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata",
    )
    section_number: str = Field(
        default="",
        description="Statutory section number (e.g. '101', '103')",
    )
    section_title: str = Field(
        default="",
        description="Official title of the statutory section",
    )
    act_short_name: str = Field(
        default="",
        description="Abbreviated statutory enactment name (e.g. 'BNS')",
    )
    evidence_type: str = Field(
        default="STATUTE",
        description="Evidence type: STATUTE, CASE_LAW, etc.",
    )
    case_name: str = Field(
        default="",
        description="Official case name if evidence_type is CASE_LAW",
    )
    court: str = Field(
        default="",
        description="Court name (e.g. Supreme Court of India)",
    )
    citation: str = Field(
        default="",
        description="Official case citation",
    )
    judgment_date: str = Field(
        default="",
        description="Judgment date (YYYY-MM-DD)",
    )
    paragraph_number: str = Field(
        default="",
        description="Numbered paragraph or passage in judgment",
    )
    topic_compatibility: str = Field(
        default="DIRECT",
        description="Topic compatibility: DIRECT, RELATED, BACKGROUND, IRRELEVANT",
    )


class RAGResponse(BaseModel):
    """Grounded legal response returned to the user or API client."""

    query: str = Field(
        ...,
        description="Original or normalized user query string",
    )
    answer: str = Field(
        ...,
        description="Grounded natural language answer synthesized from retrieved sources",
    )
    sources: List[SourceReference] = Field(
        default_factory=list,
        description="List of verified legal source chunks included in the context",
    )
    retrieval_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata on candidate discovery, filtering, and cross-encoder scoring",
    )
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata regarding the LLM provider, model version, and tokens",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Safety, validation, or evidence limitation notices",
    )
    status: str = Field(
        default="success",
        description="Execution status ('success', 'unconfigured_llm', 'no_sources_found', 'error')",
    )
    requested_facets: List[str] = Field(
        default_factory=list,
        description="Requested legal facets identified from the query",
    )
    facet_coverage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage status for each required facet in the retrieved evidence",
    )
    facet_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Facet completeness validation results on generated answer",
    )
    claim_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Substantive claim-to-evidence validation metrics",
    )
    quality_status: str = Field(
        default="COMPLETE",
        description="Overall legal answer quality gate status ('COMPLETE', 'PARTIALLY_COMPLETE', 'UNSUPPORTED_CLAIM', 'INSUFFICIENT_EVIDENCE')",
    )
    case_law_status: str = Field(
        default="NOT_REQUESTED",
        description="Case law availability status: 'NOT_REQUESTED', 'FOUND', 'NOT_FOUND', 'CORPUS_UNAVAILABLE'",
    )
    evidence_graph: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structural summary of the multi-authority evidence graph",
    )
    generation_status: str = Field(
        default="SUCCESS",
        description="LLM generation outcome: 'SUCCESS', 'RETRIEVAL_ONLY', 'RATE_LIMITED', 'QUOTA_EXCEEDED', 'TIMEOUT', 'PROVIDER_ERROR', 'VALIDATION_FAILED', 'AUTHENTICATION_ERROR', 'INVALID_MODEL', 'UNCONFIGURED'",
    )
    retrieval_status: str = Field(
        default="SUCCESS",
        description="Retrieval pipeline outcome: 'SUCCESS', 'NO_SOURCES_FOUND', 'ERROR'",
    )
    validation_status: str = Field(
        default="PASSED",
        description="Answer validation outcome: 'PASSED', 'FAILED', 'NOT_RUN'",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of generation",
    )

