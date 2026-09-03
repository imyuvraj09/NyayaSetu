"""
Context builder module for NyayaSetu Legal Knowledge Assistant.

Constructs grounded, structured, and size-controlled legal context blocks from
reranked source chunks while preserving exact statutory text and complete provenance.
"""

from dataclasses import dataclass
from typing import List, Optional, Set

from schemas.generation import SourceReference
from schemas.retrieval import RerankedChunk
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BuildContextResult:
    """Output of the context building process."""

    formatted_context: str
    sources: List[SourceReference]
    total_chars: int
    included_sources_count: int
    truncated: bool


class LegalContextBuilder:
    """Builds formatted prompt context from reranked legal chunks."""

    def __init__(self, max_context_chars: Optional[int] = None) -> None:
        self.max_context_chars = (
            max_context_chars if max_context_chars is not None else settings.MAX_CONTEXT_CHARS
        )

    def build_context(
        self,
        ranked_chunks: List[RerankedChunk],
        max_context_chars: Optional[int] = None,
    ) -> BuildContextResult:
        """Assemble structured legal context with stable [SOURCE N] labels.

        Args:
            ranked_chunks: List of RerankedChunk objects ordered by relevance descending.
            max_context_chars: Maximum character length limit for the combined context.

        Returns:
            BuildContextResult with formatted text block and mapped SourceReferences.
        """
        limit = max_context_chars or self.max_context_chars
        blocks: List[str] = []
        sources: List[SourceReference] = []
        seen_texts: Set[str] = set()

        current_chars = 0
        truncated = False

        for idx, chunk in enumerate(ranked_chunks, start=1):
            # Text deduplication check
            normalized_passage = " ".join(chunk.text.split())
            if normalized_passage in seen_texts:
                continue
            seen_texts.add(normalized_passage)

            source_label = f"[SOURCE {idx}]"
            pages_str = ", ".join(map(str, chunk.page_numbers)) if chunk.page_numbers else "N/A"

            block = (
                f"{source_label}\n"
                f"Document: {chunk.document_name} ({chunk.document_type})\n"
                f"Pages: {pages_str}\n"
                f"Chunk ID: {chunk.chunk_id}\n\n"
                f"Legal Text:\n"
                f"{chunk.text}\n"
            )

            block_length = len(block)

            # Check if adding this block exceeds limit (ensure at least 1 source is included)
            if blocks and (current_chars + block_length > limit):
                logger.warning(
                    "Context truncation: Context limit reached (%d chars + %d > %d limit). "
                    "Prioritizing higher-ranked sources; skipping %s and remaining.",
                    current_chars,
                    block_length,
                    limit,
                    source_label,
                )
                truncated = True
                break

            blocks.append(block)
            current_chars += block_length

            sources.append(
                SourceReference(
                    source_label=source_label,
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    document_type=chunk.document_type,
                    source_filename=chunk.source_filename,
                    page_numbers=chunk.page_numbers,
                    similarity_score=chunk.similarity_score,
                    reranker_score=chunk.reranker_score,
                    text_snippet=chunk.text[:300] + ("..." if len(chunk.text) > 300 else ""),
                    metadata=chunk.metadata,
                )
            )

        formatted_context = "\n---\n\n".join(blocks)
        logger.info(
            "Built legal context: %d sources included, %d total chars (limit: %d), truncated=%s",
            len(sources),
            len(formatted_context),
            limit,
            truncated,
        )

        return BuildContextResult(
            formatted_context=formatted_context,
            sources=sources,
            total_chars=len(formatted_context),
            included_sources_count=len(sources),
            truncated=truncated,
        )
