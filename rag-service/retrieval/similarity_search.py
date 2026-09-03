"""
Semantic similarity search module for NyayaSetu Legal Knowledge Assistant.

Converts natural language user queries into dense vector embeddings,
queries the local ChromaDB vector collection, and returns ranked legal passages
complete with document metadata, page numbers, and cosine similarity scores.
"""

import argparse
import sys
from typing import List, Optional, Union

from embeddings.embedding_model import EmbeddingService, get_embedding_service
from schemas.retrieval import RetrievalResult, RetrievedChunk
from utils.config import settings
from utils.logger import get_logger, setup_logging
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


class SimilaritySearchService:
    """Service for performing semantic retrieval across indexed legal documents."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[ChromaStore] = None,
    ) -> None:
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or ChromaStore()

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        """Perform semantic similarity retrieval for a legal question.

        Args:
            query: Natural language legal question or topic.
            top_k: Number of most relevant passages to return.

        Returns:
            RetrievalResult containing ranked RetrievedChunk instances.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        logger.info("Executing semantic search: '%s' (top_k=%d)", cleaned_query, top_k)

        # 1. Generate normalized embedding for the query
        query_embedding = self.embedding_service.embed_text(cleaned_query)

        # 2. Retrieve top-k nearest neighbors from ChromaDB
        retrieved_chunks = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        logger.info("Retrieved %d matching legal passage(s)", len(retrieved_chunks))

        return RetrievalResult(
            query=cleaned_query,
            top_k=top_k,
            results=retrieved_chunks,
        )


def display_retrieval_results(result: RetrievalResult) -> None:
    """Format and print ranked retrieval results for CLI inspection."""
    print("=" * 80)
    print("NYAYASETU LEGAL SEMANTIC SEARCH RESULTS")
    print("=" * 80)
    print(f"  Query        : \"{result.query}\"")
    print(f"  Results Count: {len(result.results)} (Requested top-{result.top_k})")
    print(f"  Timestamp    : {result.retrieval_timestamp}")
    print("=" * 80)

    if not result.results:
        print("\n  [!] No matching legal passages found in the vector database.")
        print("      Ensure the database has been populated with: python -m vectorstore.vectorstore_pipeline")
        print("=" * 80)
        return

    for rank, chunk in enumerate(result.results, start=1):
        # Format text preview safely for any terminal
        preview = chunk.text[:220].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
        doc_name = chunk.document_name.encode("ascii", errors="replace").decode("ascii")

        print(f"\nRANK #{rank} | Relevance Score: {chunk.relevance_score:.4f}")
        print(f"  Document   : {doc_name} ({chunk.document_type})")
        print(f"  Chunk ID   : {chunk.chunk_id}")
        print(f"  Source Page: {chunk.page_numbers}")
        print(f"  Text Excerpt:")
        print(f"    \"{preview}...\"")
        print("-" * 80)

    print("\nNote: Retrieval only. No LLM response or legal conclusion was generated.")
    print("=" * 80)


def main() -> None:
    """CLI entry point for testing semantic legal retrieval."""
    parser = argparse.ArgumentParser(
        description="NyayaSetu Legal Similarity Search CLI"
    )
    parser.add_argument(
        "query",
        type=str,
        help="Natural language legal query to search for",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING)",
    )

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    service = SimilaritySearchService()

    try:
        results = service.search(query=args.query, top_k=args.top_k)
        display_retrieval_results(results)
    except Exception as err:
        print(f"Search failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
