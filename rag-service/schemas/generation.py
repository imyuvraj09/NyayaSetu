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
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of generation",
    )
