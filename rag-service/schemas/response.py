"""
Response schemas for the NyayaSetu RAG pipeline.

Supports grounded legal answer delivery, complete source provenance tracking,
reranker scores, retrieval metadata, and backward compatibility.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """A single retrieved legal source used to ground the answer."""

    source_label: Optional[str] = Field(
        default=None,
        description="Assigned label used in citations (e.g., [SOURCE 1]).",
        examples=["[SOURCE 1]"],
    )
    chunk_id: Optional[str] = Field(
        default=None,
        description="Unique chunk identifier from legal_chunks.jsonl.",
        examples=["bns_2023_c0384"],
    )
    document_name: Optional[str] = Field(
        default=None,
        description="Name or title of the source document.",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: Optional[str] = Field(
        default=None,
        description="Legal domain classification.",
        examples=["Criminal Law"],
    )
    source_filename: Optional[str] = Field(
        default=None,
        description="Name of the source PDF.",
        examples=["bns_2023.pdf"],
    )
    section: Optional[str] = Field(
        default=None,
        description="Section or clause number if detected.",
        examples=["Section 303"],
    )
    article: Optional[str] = Field(
        default=None,
        description="Article number (for constitutional documents).",
        examples=["Article 14"],
    )
    page: Optional[int] = Field(
        default=None,
        description="Primary page number in the source PDF.",
        examples=[82],
    )
    page_numbers: List[int] = Field(
        default_factory=list,
        description="All source PDF page numbers containing this chunk.",
        examples=[[82]],
    )
    content_snippet: Optional[str] = Field(
        default=None,
        description="Relevant text excerpt from the source.",
    )
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Initial dense semantic similarity score (0-1).",
        examples=[0.8252],
    )
    reranker_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Cross-encoder relevance score (can be boosted by court level and holding).",
        examples=[0.9996],
    )
    evidence_type: str = Field(
        default="STATUTE",
        description="Evidence type: STATUTE or CASE_LAW.",
    )
    case_name: Optional[str] = Field(
        default=None,
        description="Judicial case name for case law sources.",
    )
    court: Optional[str] = Field(
        default=None,
        description="Court name (e.g. Supreme Court of India).",
    )
    citation: Optional[str] = Field(
        default=None,
        description="Law report citation (e.g. (2019) 9 SCC 608).",
    )
    paragraph_number: Optional[str] = Field(
        default=None,
        description="Paragraph number of the judgment.",
    )
    is_holding_or_ratio: bool = Field(
        default=False,
        description="Whether this excerpt contains the judicial ratio or holding.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata.",
    )


class QueryResponse(BaseModel):
    """Schema for the response returned by the /api/v1/query endpoint."""

    answer: str = Field(
        ...,
        description="The generated answer to the user's legal question.",
    )
    sources: List[SourceDocument] = Field(
        default_factory=list,
        description="List of legal sources used to generate the answer.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID echoed back for conversation tracking.",
    )
    query: Optional[str] = Field(
        default=None,
        description="Original user inquiry string.",
    )
    retrieval_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Candidate counts and document distribution statistics.",
    )
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata on the LLM provider, model version, and tokens.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Operational warnings or fallback notices.",
    )
    status: str = Field(
        default="success",
        description="Execution status of the query pipeline.",
    )
    requested_facets: List[str] = Field(
        default_factory=list,
        description="Legal information facets identified in the query.",
    )
    facet_coverage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage mapping for requested facets.",
    )
    facet_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Facet completeness validation report.",
    )
    claim_validation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Claim-evidence validation report.",
    )
    quality_status: str = Field(
        default="COMPLETE",
        description="Quality status (COMPLETE, PARTIALLY_COMPLETE, UNSUPPORTED_CLAIM).",
    )
    case_law_status: Optional[str] = Field(
        default=None,
        description="Status of case law retrieval: NOT_REQUESTED, FOUND, NOT_FOUND, CORPUS_UNAVAILABLE.",
    )
    evidence_graph: Optional[Dict[str, Any]] = Field(
        default=None,
        description="In-memory structural legal evidence graph.",
    )
    generation_status: str = Field(
        default="SUCCESS",
        description="Generation status: SUCCESS, RETRIEVAL_ONLY, RATE_LIMITED, QUOTA_EXCEEDED, TIMEOUT, PROVIDER_ERROR, VALIDATION_FAILED, AUTHENTICATION_ERROR, INVALID_MODEL",
    )
    retrieval_status: str = Field(
        default="SUCCESS",
        description="Retrieval status: SUCCESS, NO_SOURCES_FOUND, ERROR",
    )
    validation_status: str = Field(
        default="PASSED",
        description="Validation status: PASSED, FAILED, NOT_RUN",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request correlation ID matching the client's request.",
    )
    intent_coverage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Multi-intent query coverage report.",
    )

