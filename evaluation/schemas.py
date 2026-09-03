"""
Pydantic schemas for NyayaSetu RAG evaluation results and aggregate quality metrics.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetrievalEvaluationItem(BaseModel):
    """Retrieval evaluation metrics for a single query."""

    query_id: str = Field(..., description="Evaluation question identifier (e.g. Q01)")
    query: str = Field(..., description="Evaluated legal question string")
    category: str = Field(..., description="Legal category")
    difficulty: str = Field(..., description="Question complexity")
    expected_document: str = Field(..., description="Canonical expected enactment")
    retrieved_documents: List[str] = Field(default_factory=list, description="Ordered document titles of retrieved chunks")
    hit_at_1: bool = Field(..., description="Was expected document at rank 1?")
    hit_at_3: bool = Field(..., description="Was expected document in top 3?")
    hit_at_5: bool = Field(..., description="Was expected document in top 5?")
    reciprocal_rank: float = Field(..., description="1 / rank of first expected document, or 0.0 if not found")
    keyword_coverage: float = Field(..., description="Fraction of expected keywords present in retrieved text")
    retrieved_chunks_count: int = Field(..., description="Total candidate chunks retrieved")
    top_chunk_id: Optional[str] = Field(default=None, description="Chunk ID of rank 1 result")
    top_reranker_score: Optional[float] = Field(default=None, description="Cross-encoder score of rank 1 result")


class GenerationEvaluationItem(BaseModel):
    """Answer generation and citation validation metrics for a single query."""

    query_id: str = Field(...)
    query: str = Field(...)
    answer_length: int = Field(...)
    sources_returned_count: int = Field(...)
    citation_validation_passed: bool = Field(...)
    valid_citations: List[str] = Field(default_factory=list)
    invalid_citations: List[str] = Field(default_factory=list)
    source_integrity_passed: bool = Field(...)
    warnings: List[str] = Field(default_factory=list)
    status: str = Field(...)


class EvaluationSummary(BaseModel):
    """Aggregate quality and safety metrics across the evaluation benchmark."""

    benchmark_name: str = Field(default="NyayaSetu Legal RAG Benchmark")
    total_queries: int = Field(...)
    document_distribution: Dict[str, int] = Field(default_factory=dict)
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Retrieval metrics
    retrieval_success_rate: float = Field(..., description="Fraction of queries retrieving at least 1 chunk")
    document_hit_at_1: float = Field(..., description="Hit@1 accuracy")
    document_hit_at_3: float = Field(..., description="Hit@3 accuracy")
    document_hit_at_5: float = Field(..., description="Hit@5 accuracy")
    average_reciprocal_rank: float = Field(..., description="Mean Reciprocal Rank (MRR) across all queries")
    average_keyword_coverage: float = Field(..., description="Average fraction of expected keywords recovered")

    # Generation & validation metrics
    generation_evaluated_count: int = Field(default=0)
    generation_success_rate: float = Field(default=0.0)
    citation_validation_success_rate: float = Field(default=0.0)
    source_integrity_success_rate: float = Field(default=0.0)

    # Safety & failures
    total_warnings: int = Field(default=0)
    total_failures: int = Field(default=0)
    evaluation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
