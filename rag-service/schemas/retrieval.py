"""
Retrieval and vector storage schemas for NyayaSetu RAG Service.

Defines the structure for retrieved legal passages, search result collections,
cross-encoder reranked results, and embedding manifest metadata.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A legal text chunk retrieved via dense semantic similarity search."""

    chunk_id: str = Field(
        ...,
        description="Unique identifier of the retrieved chunk",
        examples=["bns_2023_c0242"],
    )
    document_name: str = Field(
        ...,
        description="Canonical name of the source enactment",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: str = Field(
        default="Unknown",
        description="Legal domain classification",
        examples=["Criminal Law"],
    )
    source_filename: str = Field(
        default="",
        description="Name of the original source PDF file",
        examples=["bns_2023.pdf"],
    )
    page_numbers: List[int] = Field(
        ...,
        description="Source PDF page numbers containing this passage",
        examples=[[53]],
    )
    text: str = Field(
        ...,
        description="Cleaned text content of the retrieved chunk",
    )
    relevance_score: float = Field(
        ...,
        description="Cosine similarity or normalized relevance score (0.0 to 1.0)",
        examples=[0.875],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible chunk metadata (e.g. source filename, headings, etc.)",
    )


class RerankedChunk(BaseModel):
    """A legal text chunk scored and ranked by a cross-encoder."""

    rank: int = Field(
        ...,
        ge=1,
        description="1-based final rank assigned by cross-encoder reranking",
        examples=[1],
    )
    chunk_id: str = Field(
        ...,
        description="Unique identifier of the chunk",
        examples=["bns_2023_c0384"],
    )
    document_name: str = Field(
        ...,
        description="Canonical name of the source enactment",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: str = Field(
        default="Unknown",
        description="Legal domain classification",
        examples=["Criminal Law"],
    )
    source_filename: str = Field(
        default="",
        description="Name of the source PDF",
        examples=["bns_2023.pdf"],
    )
    page_numbers: List[int] = Field(
        ...,
        description="Source PDF page numbers",
        examples=[[82]],
    )
    text: str = Field(
        ...,
        description="Cleaned text content of the chunk",
    )
    similarity_score: float = Field(
        ...,
        description="Initial dense retrieval cosine similarity score",
        examples=[0.8252],
    )
    reranker_score: float = Field(
        ...,
        description="Cross-encoder relevance score",
        examples=[0.9412],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved source metadata",
    )


class RetrievalResult(BaseModel):
    """Collection of ranked legal chunks returned for a basic query."""

    query: str = Field(
        ...,
        description="Original natural language query string",
    )
    top_k: int = Field(
        ...,
        ge=1,
        description="Number of requested top results",
    )
    results: List[RetrievedChunk] = Field(
        default_factory=list,
        description="List of retrieved chunks ordered by relevance score descending",
    )
    retrieval_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of retrieval",
    )


class AdvancedRetrievalResult(BaseModel):
    """Orchestrated retrieval result with initial candidates, filtering, and cross-encoder reranking."""

    original_query: str = Field(
        ...,
        description="Raw user query string",
    )
    normalized_query: str = Field(
        ...,
        description="Cleaned query used for embedding and reranking",
    )
    initial_k: int = Field(
        ...,
        description="Configured initial candidate retrieval count",
        examples=[20],
    )
    final_k: int = Field(
        ...,
        description="Configured final top-k result count",
        examples=[5],
    )
    initial_candidates_count: int = Field(
        ...,
        description="Number of candidates retrieved from ChromaDB",
    )
    filtered_candidates_count: int = Field(
        ...,
        description="Number of candidates remaining after deduplication and metadata filtering",
    )
    final_results_count: int = Field(
        ...,
        description="Number of final reranked chunks returned",
    )
    results: List[RerankedChunk] = Field(
        default_factory=list,
        description="Final top-k chunks ordered by reranker score descending",
    )
    initial_results: List[RetrievedChunk] = Field(
        default_factory=list,
        description="Initial dense retrieval top candidates before reranking (for debugging / evaluation)",
    )
    document_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of final results across legal enactments",
    )
    retrieval_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of execution",
    )


class EmbeddingManifest(BaseModel):
    """Manifest summarizing the vectorization and vector database ingestion run."""

    total_chunks_discovered: int = Field(
        default=0,
        description="Total chunks loaded from legal_chunks.jsonl",
    )
    total_chunks_embedded: int = Field(
        default=0,
        description="Total chunks successfully embedded and stored in ChromaDB",
    )
    failed_chunks: int = Field(
        default=0,
        description="Number of chunks that failed embedding or insertion",
    )
    embedding_model: str = Field(
        ...,
        description="HuggingFace model ID used for generating embeddings",
    )
    embedding_dimension: int = Field(
        ...,
        description="Dimensionality of the generated vector embeddings",
    )
    batch_size: int = Field(
        ...,
        description="Batch size used during embedding generation",
    )
    vector_collection_name: str = Field(
        ...,
        description="Name of the ChromaDB collection",
    )
    processing_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of embedding completion",
    )
