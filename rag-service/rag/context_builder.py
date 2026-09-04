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

        statute_blocks: List[str] = []
        case_blocks: List[str] = []

        statute_idx = 1
        case_idx = 1

        for chunk in ranked_chunks:
            # Text deduplication check
            normalized_passage = " ".join(chunk.text.split())
            if normalized_passage in seen_texts:
                continue
            seen_texts.add(normalized_passage)

            ev_type = getattr(chunk, "evidence_type", "STATUTE")
            if not ev_type and isinstance(chunk.metadata, dict):
                ev_type = chunk.metadata.get("evidence_type", "STATUTE")

            if ev_type == "CASE_LAW":
                source_label = f"[Case Source C{case_idx}]"
                case_name = getattr(chunk, "case_name", "") or chunk.document_name
                court_name = getattr(chunk, "court", "") or "Supreme Court of India"
                cite = getattr(chunk, "citation", "") or ""
                j_date = getattr(chunk, "judgment_date", "") or ""
                para_num = getattr(chunk, "paragraph_number", "") or (str(chunk.page_numbers[0]) if chunk.page_numbers else "1")

                block = (
                    f"{source_label}\n"
                    f"Case: {case_name}\n"
                    f"Court: {court_name}\n"
                    f"Citation: {cite}\n"
                    f"Date: {j_date}\n"
                    f"Paragraph: {para_num}\n"
                    f"Chunk ID: {chunk.chunk_id}\n\n"
                    f"Judgment Text:\n"
                    f"{chunk.text}\n"
                )
                case_idx += 1
            else:
                source_label = f"[Source S{statute_idx}]"
                pages_str = ", ".join(map(str, chunk.page_numbers)) if chunk.page_numbers else "N/A"
                sec_num = getattr(chunk, "section_number", "") or ""
                sec_title = getattr(chunk, "section_title", "") or ""
                short_name = getattr(chunk, "act_short_name", "") or ""

                sec_display = f"Section {sec_num}" if sec_num else "Section Unspecified"
                if sec_title:
                    sec_display += f" — {sec_title}"

                block = (
                    f"{source_label}\n"
                    f"Act: {chunk.document_name} ({short_name or chunk.document_type})\n"
                    f"Provision: {sec_display}\n"
                    f"Pages: {pages_str}\n"
                    f"Chunk ID: {chunk.chunk_id}\n\n"
                    f"Statutory Text:\n"
                    f"{chunk.text}\n"
                )
                statute_idx += 1

            block_length = len(block)
            if (statute_blocks or case_blocks) and (current_chars + block_length > limit):
                logger.warning(
                    "Context truncation: Context limit reached (%d chars + %d > %d limit). "
                    "Skipping %s and remaining.",
                    current_chars,
                    block_length,
                    limit,
                    source_label,
                )
                truncated = True
                break

            if ev_type == "CASE_LAW":
                case_blocks.append(block)
            else:
                statute_blocks.append(block)

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
                    section_number=getattr(chunk, "section_number", ""),
                    section_title=getattr(chunk, "section_title", ""),
                    act_short_name=getattr(chunk, "act_short_name", ""),
                    evidence_type=ev_type,
                    case_name=getattr(chunk, "case_name", ""),
                    court=getattr(chunk, "court", ""),
                    citation=getattr(chunk, "citation", ""),
                    judgment_date=getattr(chunk, "judgment_date", ""),
                    paragraph_number=str(getattr(chunk, "paragraph_number", "")),
                    topic_compatibility=getattr(chunk, "topic_compatibility", "DIRECT"),
                )
            )

        context_sections: List[str] = []
        if statute_blocks:
            context_sections.append("=== STATUTORY EVIDENCE ===\n\n" + "\n---\n\n".join(statute_blocks))
        if case_blocks:
            context_sections.append("=== CASE-LAW EVIDENCE ===\n\n" + "\n---\n\n".join(case_blocks))

        formatted_context = "\n\n====================\n\n".join(context_sections)
        logger.info(
            "Built legal context: %d sources included (%d statutory, %d case-law), %d total chars (limit: %d), truncated=%s",
            len(sources),
            len(statute_blocks),
            len(case_blocks),
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
