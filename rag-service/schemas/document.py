"""
Document and Ingestion Schemas for NyayaSetu RAG Service.

Defines the structure for extracted page-level legal records and the
pipeline ingestion manifest/summary.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentPageRecord(BaseModel):
    """Structured record representing an extracted page of a legal document."""

    document_id: str = Field(
        ...,
        description="Unique identifier for the page record (e.g. bns_2023_p1)",
        examples=["bns_2023_p1"],
    )
    document_name: str = Field(
        ...,
        description="Canonical name of the legal enactment or document",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    source_filename: str = Field(
        ...,
        description="Original name of the source PDF file",
        examples=["bns_2023.pdf"],
    )
    source_path: str = Field(
        ...,
        description="Relative or normalized path to the source PDF file",
        examples=["data/raw/bns_2023.pdf"],
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-based page number within the source document",
        examples=[1],
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
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction",
    )
    text: str = Field(
        default="",
        description="Cleaned text content of the page",
    )
    character_count: int = Field(
        default=0,
        description="Character count of cleaned page text",
    )
    has_text: bool = Field(
        default=False,
        description="Whether the page contains non-whitespace text",
    )


class IngestionManifest(BaseModel):
    """Summary manifest generated upon completing an ingestion run."""

    total_files_discovered: int = Field(
        default=0,
        description="Total PDF files discovered in raw data directory",
    )
    successfully_processed_files: int = Field(
        default=0,
        description="Number of files processed without fatal errors",
    )
    failed_files: int = Field(
        default=0,
        description="Number of files that failed to load or parse",
    )
    total_pages: int = Field(
        default=0,
        description="Total pages extracted across all processed documents",
    )
    pages_containing_text: int = Field(
        default=0,
        description="Number of pages with non-empty extracted text",
    )
    empty_pages: int = Field(
        default=0,
        description="Number of blank or non-text/scanned pages",
    )
    processing_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of ingestion completion",
    )
    processed_documents: List[str] = Field(
        default_factory=list,
        description="List of filenames successfully processed",
    )
    failed_documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of failed documents with error descriptions",
    )
