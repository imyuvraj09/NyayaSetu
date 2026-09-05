"""
NyayaSetu RAG Service — API route handlers.

All routes are mounted under the /api/v1 prefix (configured in main.py).
Wires the complete Phase 7 Legal RAG pipeline into POST /api/v1/query.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from rag.rag_pipeline import LegalRAGPipeline
from schemas.query import QueryRequest
from schemas.response import QueryResponse, SourceDocument
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Singleton pipeline instance initialized on module load
_RAG_PIPELINE: Optional[LegalRAGPipeline] = None


def get_pipeline() -> LegalRAGPipeline:
    """Lazy loader for the LegalRAGPipeline singleton."""
    global _RAG_PIPELINE
    if _RAG_PIPELINE is None:
        _RAG_PIPELINE = LegalRAGPipeline()
    return _RAG_PIPELINE


@router.get("/health")
async def health_check():
    """Return the service health and configuration status."""
    pipeline = get_pipeline()
    llm_health = pipeline.llm_provider.check_health()
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": llm_health.get("provider", settings.LLM_PROVIDER),
        "llm_model": llm_health.get("model", settings.LLM_MODEL),
        "llm_configured": llm_health.get("configured", False),
        "llm_available": llm_health.get("available", False),
        "vector_db_collection": settings.VECTOR_COLLECTION_NAME,
    }


@router.get("/health/llm")
async def llm_health_check():
    """Expose safe health information for LLM provider without revealing secrets."""
    pipeline = get_pipeline()
    return pipeline.llm_provider.check_health()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Accept a legal question and return a grounded, cited RAG-generated response.

    Executes:
    1. Query preprocessing
    2. Phase 6 two-stage dense retrieval + cross-encoder reranking
    3. Structured legal context construction with [SOURCE N] labels
    4. Grounded answer generation via LLM provider
    5. Deterministic citation validation and safety checks
    """
    session_id = request.session_id or str(uuid.uuid4())
    request_id = getattr(request, "request_id", None) or str(uuid.uuid4())

    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty or whitespace only.",
        )

    logger.info(
        "API Query received | session=%s | request_id=%s | length=%d",
        session_id,
        request_id,
        len(request.query),
    )

    try:
        pipeline = get_pipeline()
        rag_result = pipeline.query(request.query, request_id=request_id)

        # Convert SourceReference list to SourceDocument list for response
        mapped_sources = [
            SourceDocument(
                source_label=src.source_label,
                chunk_id=src.chunk_id,
                document_name=src.document_name,
                document_type=src.document_type,
                source_filename=src.source_filename,
                page=src.page_numbers[0] if src.page_numbers else None,
                page_numbers=src.page_numbers,
                content_snippet=src.text_snippet,
                relevance_score=src.similarity_score,
                reranker_score=src.reranker_score,
                evidence_type=getattr(src, "evidence_type", "STATUTE"),
                case_name=getattr(src, "case_name", None),
                court=getattr(src, "court", None),
                citation=getattr(src, "citation", None),
                paragraph_number=getattr(src, "paragraph_number", None),
                is_holding_or_ratio=getattr(src, "is_holding_or_ratio", False),
                metadata=src.metadata,
            )
            for src in rag_result.sources
        ]

        return QueryResponse(
            answer=rag_result.answer,
            sources=mapped_sources,
            session_id=session_id,
            query=request.query,
            retrieval_metadata=rag_result.retrieval_metadata,
            model_metadata=rag_result.model_metadata,
            warnings=rag_result.warnings,
            status=rag_result.status,
            requested_facets=getattr(rag_result, "requested_facets", []),
            facet_coverage=getattr(rag_result, "facet_coverage", {}),
            facet_validation=getattr(rag_result, "facet_validation", {}),
            claim_validation=getattr(rag_result, "claim_validation", {}),
            quality_status=getattr(rag_result, "quality_status", "COMPLETE"),
            case_law_status=getattr(rag_result, "case_law_status", None),
            evidence_graph=getattr(rag_result, "evidence_graph", None),
            generation_status=getattr(rag_result, "generation_status", "SUCCESS"),
            retrieval_status=getattr(rag_result, "retrieval_status", "SUCCESS"),
            validation_status=getattr(rag_result, "validation_status", "PASSED"),
            request_id=request_id,
            intent_coverage=getattr(rag_result, "intent_coverage", None),
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error("API error processing query: %s", err, exc_info=True)
        return QueryResponse(
            answer=(
                "A system error occurred while processing your legal query. "
                "Please try again or contact system support."
            ),
            sources=[],
            session_id=session_id,
            query=request.query,
            warnings=[f"Internal processing error: {err}"],
            status="error",
            request_id=request_id,
        )
