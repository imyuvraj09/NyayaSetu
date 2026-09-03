"""
CLI retrieval pipeline and evaluation tool for NyayaSetu Legal Assistant.

Executes and displays two-stage legal retrieval (Dense Vector Search -> Deduplication -> Cross-Encoder Reranking),
with support for candidate inspection, document distribution analysis, and side-by-side comparison with dense-only retrieval.
"""

import argparse
import sys
from typing import Optional

from retrieval.advanced_retriever import AdvancedRetriever
from schemas.retrieval import AdvancedRetrievalResult
from utils.config import settings
from utils.logger import setup_logging


def print_comparison_view(result: AdvancedRetrievalResult) -> None:
    """Print side-by-side comparison between initial dense retrieval and cross-encoder reranking."""
    print("=" * 80)
    print("COMPARISON: DENSE RETRIEVAL ONLY vs. DENSE RETRIEVAL + RERANKING")
    print("=" * 80)
    print(f"Query: \"{result.normalized_query}\"")
    print("-" * 80)

    print("\n[A] DENSE RETRIEVAL ONLY (Top-{} Before Reranking):".format(len(result.initial_results)))
    for rank, chunk in enumerate(result.initial_results, start=1):
        doc = chunk.document_name.encode("ascii", errors="replace").decode("ascii")
        preview = chunk.text[:120].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
        print(f"  #{rank} | Score: {chunk.relevance_score:.4f} | ID: {chunk.chunk_id} | Doc: {doc} | Pages: {chunk.page_numbers}")
        print(f"      \"{preview}...\"")

    print("\n[B] DENSE RETRIEVAL + CROSS-ENCODER RERANKING (Final Top-{}):".format(len(result.results)))
    for chunk in result.results:
        doc = chunk.document_name.encode("ascii", errors="replace").decode("ascii")
        preview = chunk.text[:120].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
        print(f"  #{chunk.rank} | Rerank: {chunk.reranker_score:.4f} (Sim: {chunk.similarity_score:.4f}) | ID: {chunk.chunk_id} | Doc: {doc} | Pages: {chunk.page_numbers}")
        print(f"      \"{preview}...\"")

    # Analyze ranking changes
    initial_ids = [c.chunk_id for c in result.initial_results]
    reranked_ids = [c.chunk_id for c in result.results]
    is_reordered = initial_ids != reranked_ids
    print("-" * 80)
    print(f"Ranking Change Observed: {'YES (Cross-encoder reordered or elevated candidates)' if is_reordered else 'NO (Order maintained)'}")
    print("=" * 80)


def print_standard_view(result: AdvancedRetrievalResult) -> None:
    """Print structured execution output of the advanced retrieval pipeline."""
    print("=" * 80)
    print("QUERY")
    print("=" * 80)
    print(f"\"{result.normalized_query}\"")
    print()

    print("=" * 80)
    print("INITIAL RETRIEVAL")
    print("=" * 80)
    print(f"Candidates retrieved from ChromaDB: {result.initial_candidates_count} (Target: {result.initial_k})")
    print()

    print("=" * 80)
    print("FILTERING")
    print("=" * 80)
    print(f"Candidates after deduplication & document capping: {result.filtered_candidates_count}")
    print()

    print("=" * 80)
    print("RERANKED RESULTS (Top-{})".format(result.final_results_count))
    print("=" * 80)

    if not result.results:
        print("  No matching legal passages found.")
    else:
        for chunk in result.results:
            preview = chunk.text[:220].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
            doc = chunk.document_name.encode("ascii", errors="replace").decode("ascii")
            print(f"Rank {chunk.rank}")
            print(f"  Document        : {doc} ({chunk.document_type})")
            print(f"  Source Pages    : {chunk.page_numbers}")
            print(f"  Chunk ID        : {chunk.chunk_id}")
            print(f"  Similarity Score: {chunk.similarity_score:.4f}")
            print(f"  Reranker Score  : {chunk.reranker_score:.4f}")
            print(f"  Preview         :")
            print(f"    \"{preview}...\"")
            print("-" * 80)

    print("\nDocument Distribution in Final Results:")
    for doc, count in result.document_distribution.items():
        print(f"  - {doc}: {count} chunk(s)")

    print("\nNote: Retrieval only. No LLM response or legal conclusion was generated.")
    print("=" * 80)


def main() -> None:
    """CLI entry point for the advanced retrieval pipeline."""
    parser = argparse.ArgumentParser(
        description="NyayaSetu Advanced Retrieval & Reranking Pipeline"
    )
    parser.add_argument(
        "query",
        type=str,
        help="Natural language legal query to search for",
    )
    parser.add_argument(
        "--initial-k",
        type=int,
        default=None,
        help=f"Number of initial dense candidates (default: {settings.INITIAL_RETRIEVAL_K})",
    )
    parser.add_argument(
        "--final-k",
        type=int,
        default=None,
        help=f"Final top-k chunks after reranking (default: {settings.FINAL_RETRIEVAL_K})",
    )
    parser.add_argument(
        "--max-per-document",
        type=int,
        default=None,
        help=f"Max chunks allowed per document (default: {settings.MAX_CHUNKS_PER_DOCUMENT})",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Display comparison between dense-only retrieval and dense+reranking",
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

    retriever = AdvancedRetriever()

    try:
        result = retriever.retrieve(
            query=args.query,
            initial_k=args.initial_k,
            final_k=args.final_k,
            max_per_document=args.max_per_document,
        )

        if args.compare:
            print_comparison_view(result)
        else:
            print_standard_view(result)

    except Exception as err:
        print(f"Retrieval pipeline error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
