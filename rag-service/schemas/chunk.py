"""
Legal text chunk schema for NyayaSetu RAG Service.

Defines the structure for retrieval chunks generated from ingested legal documents,
preserving complete source traceability and extensible metadata for citations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LegalChunk(BaseModel):
    """A granular, context-preserving text chunk derived from legal documents."""

    chunk_id: str = Field(
        ...,
        description="Deterministic, unique chunk identifier (e.g. bns_2023_c0001)",
        examples=["bns_2023_c0001"],
    )
    document_id: str = Field(
        ...,
        description="Canonical identifier or slug for the parent document",
        examples=["bns_2023"],
    )
    document_name: str = Field(
        ...,
        description="Canonical name of the statute or legal enactment",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    source_filename: str = Field(
        ...,
        description="Name of the original source PDF",
        examples=["bns_2023.pdf"],
    )
    document_type: str = Field(
        default="Unknown",
        description="Legal domain or document classification",
        examples=["Criminal Law"],
    )
    jurisdiction: str = Field(
        default="India",
        description="Legal jurisdiction",
        examples=["India"],
    )
    language: str = Field(
        default="English",
        description="Language of the legal text",
        examples=["English"],
    )
    text: str = Field(
        ...,
        description="Cleaned text content of the chunk",
    )
    page_numbers: List[int] = Field(
        ...,
        description="1-based page numbers from which this chunk was extracted",
        examples=[[1], [1, 2]],
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Sequential 0-based index of the chunk within the document",
        examples=[0],
    )
    character_count: int = Field(
        ...,
        ge=1,
        description="Number of characters in the chunk text",
    )
    word_count: int = Field(
        ...,
        ge=1,
        description="Number of words in the chunk text",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata (e.g. detected headings, source paths, etc.)",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of chunk generation",
    )


class ChunkingManifest(BaseModel):
    """Manifest summarizing the results and configuration of a chunking pipeline run."""

    total_documents: int = Field(
        default=0,
        description="Total unique documents processed",
    )
    total_input_pages: int = Field(
        default=0,
        description="Total input page records evaluated",
    )
    total_chunks: int = Field(
        default=0,
        description="Total legal chunks generated",
    )
    average_chunk_size: float = Field(
        default=0.0,
        description="Average character count across all generated chunks",
    )
    minimum_chunk_size: int = Field(
        default=0,
        description="Smallest chunk size in characters",
    )
    maximum_chunk_size: int = Field(
        default=0,
        description="Largest chunk size in characters",
    )
    documents_processed: List[str] = Field(
        default_factory=list,
        description="List of document names successfully chunked",
    )
    failed_documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of documents that failed processing with reasons",
    )
    processing_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of chunking completion",
    )
    chunk_size_configuration: int = Field(
        ...,
        description="Configured target chunk size in characters",
    )
    overlap_configuration: int = Field(
        ...,
        description="Configured chunk overlap in characters",
    )
