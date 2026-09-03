"""
NyayaSetu Legal Retrieval Package.

Provides dense semantic search, query preprocessing, candidate filtering,
cross-encoder reranking, and full two-stage retrieval orchestration.
"""

from retrieval.advanced_retriever import AdvancedRetriever
from retrieval.metadata_filter import MetadataFilter
from retrieval.query_processor import ProcessedQuery, process_query
from retrieval.reranker import LegalReranker, get_legal_reranker
from retrieval.retrieval_pipeline import print_comparison_view, print_standard_view
from retrieval.similarity_search import (
    SimilaritySearchService,
    display_retrieval_results,
)

__all__ = [
    "SimilaritySearchService",
    "display_retrieval_results",
    "process_query",
    "ProcessedQuery",
    "MetadataFilter",
    "LegalReranker",
    "get_legal_reranker",
    "AdvancedRetriever",
    "print_standard_view",
    "print_comparison_view",
]
