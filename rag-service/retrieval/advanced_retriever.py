"""
Advanced retrieval orchestrator for NyayaSetu Legal Knowledge Assistant.

Combines:
1. Query preprocessing
2. Dense semantic retrieval from ChromaDB (initial_k candidates)
3. Deterministic deduplication and document diversity filtering
4. Cross-encoder reranking (BAAI/bge-reranker-base)
5. Structured result serialization with full source provenance
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

from retrieval.metadata_filter import MetadataFilter
from retrieval.query_processor import process_query
from retrieval.reranker import LegalReranker, get_legal_reranker
from retrieval.similarity_search import SimilaritySearchService
from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk, RetrievedChunk
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedRetriever:
    """End-to-end two-stage legal retrieval pipeline."""

    def __init__(
        self,
        similarity_service: Optional[SimilaritySearchService] = None,
        reranker: Optional[LegalReranker] = None,
        metadata_filter: Optional[MetadataFilter] = None,
        initial_k: Optional[int] = None,
        final_k: Optional[int] = None,
        max_per_document: Optional[int] = None,
    ) -> None:
        self.similarity_service = similarity_service or SimilaritySearchService()
        self.reranker = reranker or get_legal_reranker()
        self.metadata_filter = metadata_filter or MetadataFilter()
        self.initial_k = initial_k or settings.INITIAL_RETRIEVAL_K
        self.final_k = final_k or settings.FINAL_RETRIEVAL_K
        self.max_per_document = max_per_document or settings.MAX_CHUNKS_PER_DOCUMENT

    def retrieve(
        self,
        query: str,
        initial_k: Optional[int] = None,
        final_k: Optional[int] = None,
        max_per_document: Optional[int] = None,
    ) -> AdvancedRetrievalResult:
        """Execute full two-stage retrieval with cross-encoder reranking.

        Args:
            query: User's legal question.
            initial_k: Number of candidates to fetch in dense retrieval.
            final_k: Final top-k chunks to return.
            max_per_document: Max chunks permitted from a single enactment.

        Returns:
            AdvancedRetrievalResult containing ranked chunks and stage metrics.
        """
        ik = initial_k or self.initial_k
        fk = final_k or self.final_k
        mpd = max_per_document or self.max_per_document

        # Step 1: Query Processing
        processed = process_query(query)
        logger.info(
            "Advanced retrieval initiated for query: '%s' (initial_k=%d, final_k=%d)",
            processed.normalized_query,
            ik,
            fk,
        )

        # Step 2: Dense Semantic Retrieval
        dense_search = self.similarity_service.search(
            query=processed.normalized_query,
            top_k=ik,
        )
        initial_candidates = dense_search.results
        logger.info("Dense retrieval retrieved %d candidates", len(initial_candidates))

        if not initial_candidates:
            logger.warning("No candidates retrieved from vector store.")
            return AdvancedRetrievalResult(
                original_query=processed.original_query,
                normalized_query=processed.normalized_query,
                initial_k=ik,
                final_k=fk,
                initial_candidates_count=0,
                filtered_candidates_count=0,
                final_results_count=0,
                results=[],
                initial_results=[],
                document_distribution={},
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Step 3: Metadata & Duplicate Filtering
        filtered_candidates, filter_stats = self.metadata_filter.filter_candidates(
            candidates=initial_candidates,
            max_per_document=mpd,
        )

        # Step 4: Cross-Encoder Reranking
        scored_pairs = self.reranker.rerank(
            query=processed.normalized_query,
            candidates=filtered_candidates,
            top_k=fk,
        )

        # Step 5: Format Final Reranked Results
        final_chunks: List[RerankedChunk] = []
        for rank, (chunk, reranker_score) in enumerate(scored_pairs, start=1):
            final_chunks.append(
                RerankedChunk(
                    rank=rank,
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    document_type=chunk.document_type,
                    source_filename=chunk.source_filename or chunk.metadata.get("source_filename", ""),
                    page_numbers=chunk.page_numbers,
                    text=chunk.text,
                    similarity_score=chunk.relevance_score,
                    reranker_score=reranker_score,
                    metadata=chunk.metadata,
                )
            )

        # Distribution count across legal documents
        doc_dist = dict(Counter(c.document_name for c in final_chunks))

        logger.info(
            "Advanced retrieval complete: %d initial -> %d filtered -> %d final",
            len(initial_candidates),
            len(filtered_candidates),
            len(final_chunks),
        )

        return AdvancedRetrievalResult(
            original_query=processed.original_query,
            normalized_query=processed.normalized_query,
            initial_k=ik,
            final_k=fk,
            initial_candidates_count=len(initial_candidates),
            filtered_candidates_count=len(filtered_candidates),
            final_results_count=len(final_chunks),
            results=final_chunks,
            initial_results=initial_candidates[:fk],
            document_distribution=doc_dist,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        )
