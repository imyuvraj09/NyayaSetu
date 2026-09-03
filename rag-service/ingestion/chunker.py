"""
Legal-aware text chunking module for NyayaSetu RAG Service.

Implements a hybrid chunking strategy that respects legal document boundaries:
1. Primary: Paragraph and statutory section boundaries (\\n\\n, headings, numbered provisions).
2. Secondary: Sentence boundaries for oversized paragraphs, respecting legal abbreviations.
3. Fallback: Safe word-boundary splitting for extremely long legal sentences.

Preserves complete page traceability, prevents stranding of section headers,
and yields deterministic, retrieval-optimized text chunks.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from schemas.chunk import LegalChunk
from schemas.document import DocumentPageRecord
from utils.logger import get_logger

logger = get_logger(__name__)

# Common legal abbreviations that should NOT trigger a sentence split
LEGAL_ABBREVIATIONS = {
    "sec.", "secs.", "art.", "arts.", "cl.", "cls.", "no.", "nos.",
    "v.", "vs.", "u/s", "r/w", "ors.", "anr.", "govt.", "hon'ble",
    "ltd.", "pvt.", "co.", "vol.", "air", "scc", "scr", "ilr",
    "cr.l.j.", "i.e.", "e.g.", "viz.", "etc.", "para.", "paras.",
    "w.e.f.", "sub-sec.", "sub-cl.", "dr.", "mr.", "mrs.", "ms.",
}

# Regex to detect major legal headers and section starts
HEADING_PATTERNS = [
    re.compile(r"^(?:CHAPTER|PART|SCHEDULE|THE\s+SCHEDULE)\s+[IVXLCDM\d]+", re.IGNORECASE),
    re.compile(r"^PRELIMINARY\b", re.IGNORECASE),
    re.compile(r"^(?:Section|Article|Sec\.|Art\.)\s+\d+", re.IGNORECASE),
    re.compile(r"^\d+\.\s+[A-Z][A-Za-z0-9\s,\-\(\)]{2,80}$"),
]


def is_likely_heading(line: str) -> bool:
    """Determine whether a line represents a legal heading, chapter, or section header."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False

    for pattern in HEADING_PATTERNS:
        if pattern.search(stripped):
            return True

    # Short all-caps line (e.g. "GENERAL EXCEPTIONS", "OF OFFENCES AGAINST THE STATE")
    if stripped.isupper() and 3 <= len(stripped) <= 60 and not stripped.endswith("."):
        return True

    return False


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while respecting legal citations and abbreviations."""
    if not text:
        return []

    # Match sentence endings (. ! ?) followed by whitespace and an uppercase letter/bracket/digit
    raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\(\[\"])", text)
    sentences: List[str] = []

    for piece in raw_splits:
        piece = piece.strip()
        if not piece:
            continue

        # If previous piece ended with a known legal abbreviation, merge with current piece
        if sentences:
            last_word = sentences[-1].split()[-1].lower().rstrip(".,;:()")
            if last_word in LEGAL_ABBREVIATIONS or sentences[-1].endswith(tuple(LEGAL_ABBREVIATIONS)):
                sentences[-1] = f"{sentences[-1]} {piece}"
                continue

        sentences.append(piece)

    return sentences if sentences else [text.strip()]


def split_oversized_text(text: str, max_size: int) -> List[str]:
    """Break text larger than max_size safely at clause or word boundaries."""
    if len(text) <= max_size:
        return [text]

    chunks: List[str] = []
    # Try splitting on clause delimiters: semicolon, colon, or comma
    clauses = re.split(r"(?<=[;:,])\s+", text)

    current = ""
    for clause in clauses:
        if len(clause) > max_size:
            # Fallback to word-boundary splitting
            words = clause.split(" ")
            for w in words:
                if current and len(current) + len(w) + 1 > max_size:
                    chunks.append(current.strip())
                    current = w
                else:
                    current = f"{current} {w}".strip()
        elif current and len(current) + len(clause) + 1 > max_size:
            chunks.append(current.strip())
            current = clause
        else:
            current = f"{current} {clause}".strip()

    if current.strip():
        chunks.append(current.strip())

    return chunks


@dataclass
class AtomicSegment:
    """An indivisible or natural textual unit tied to a specific source page."""

    text: str
    page_number: int
    is_heading: bool = False


class LegalChunker:
    """Legal-aware text chunker with heading preservation and cross-page continuity.

    Attributes:
        chunk_size: Target maximum characters per chunk (default: 1200).
        chunk_overlap: Target overlap in characters between consecutive chunks (default: 200).
        min_chunk_size: Minimum characters required to emit a standalone chunk (default: 150).
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        min_chunk_size: int = 150,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def _decompose_page_into_segments(
        self, page_record: DocumentPageRecord
    ) -> List[AtomicSegment]:
        """Convert a page's text into an ordered list of atomic segments."""
        raw_text = page_record.text.strip()
        if not raw_text:
            return []

        segments: List[AtomicSegment] = []
        # Split on double newlines for paragraph/logical boundaries
        paragraphs = raw_text.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this entire paragraph is a heading
            if is_likely_heading(para):
                segments.append(
                    AtomicSegment(
                        text=para,
                        page_number=page_record.page_number,
                        is_heading=True,
                    )
                )
                continue

            # If paragraph fits within target chunk size, keep it intact
            if len(para) <= self.chunk_size:
                segments.append(
                    AtomicSegment(
                        text=para,
                        page_number=page_record.page_number,
                        is_heading=False,
                    )
                )
                continue

            # Secondary: split oversized paragraph into sentences
            sentences = split_into_sentences(para)
            for sentence in sentences:
                if len(sentence) <= self.chunk_size:
                    segments.append(
                        AtomicSegment(
                            text=sentence,
                            page_number=page_record.page_number,
                            is_heading=False,
                        )
                    )
                else:
                    # Fallback: split oversized sentence safely
                    sub_parts = split_oversized_text(sentence, self.chunk_size)
                    for part in sub_parts:
                        segments.append(
                            AtomicSegment(
                                text=part,
                                page_number=page_record.page_number,
                                is_heading=False,
                            )
                        )

        return segments

    def chunk_document(
        self, page_records: List[DocumentPageRecord]
    ) -> List[LegalChunk]:
        """Transform a sequence of page records from a single document into LegalChunks.

        Args:
            page_records: Chronologically ordered page records belonging to one document.

        Returns:
            List of validated LegalChunk instances.
        """
        if not page_records:
            return []

        # Ensure page records are sorted by page_number
        sorted_records = sorted(page_records, key=lambda p: p.page_number)
        primary_record = sorted_records[0]

        doc_slug = primary_record.document_id.split("_p")[0]
        doc_name = primary_record.document_name
        source_filename = primary_record.source_filename
        source_path = primary_record.source_path
        doc_type = primary_record.document_type
        jurisdiction = primary_record.jurisdiction
        language = primary_record.language

        # Step 1: Flatten all pages into atomic segments
        all_segments: List[AtomicSegment] = []
        for pr in sorted_records:
            all_segments.extend(self._decompose_page_into_segments(pr))

        if not all_segments:
            logger.warning("No text segments produced for document: %s", doc_name)
            return []

        # Step 2: Assemble segments into chunks
        chunks: List[LegalChunk] = []
        chunk_idx = 0

        current_segments: List[AtomicSegment] = []
        current_char_count = 0

        def emit_current_chunk() -> Optional[LegalChunk]:
            nonlocal chunk_idx, current_segments, current_char_count
            if not current_segments:
                return None

            chunk_text = "\n\n".join(s.text for s in current_segments).strip()
            if not chunk_text:
                current_segments = []
                current_char_count = 0
                return None

            pages = sorted(list(set(s.page_number for s in current_segments)))
            headings_in_chunk = [s.text for s in current_segments if s.is_heading]

            # Detect section number where reliably identifiable
            sec_match = re.search(r'\b(?:Section|Sec\.)\s*(\d+[A-Z]?)\b|^\s*(\d+[A-Z]?)\.\s+[A-Z]', chunk_text, re.MULTILINE)
            section_number = (sec_match.group(1) or sec_match.group(2)) if sec_match else ""

            chunk_obj = LegalChunk(
                chunk_id=f"{doc_slug}_c{chunk_idx:04d}",
                document_id=doc_slug,
                document_name=doc_name,
                source_filename=source_filename,
                document_type=doc_type,
                jurisdiction=jurisdiction,
                language=language,
                text=chunk_text,
                page_numbers=pages,
                chunk_index=chunk_idx,
                character_count=len(chunk_text),
                word_count=len(chunk_text.split()),
                metadata={
                    "source_path": source_path,
                    "has_heading": len(headings_in_chunk) > 0,
                    "headings": headings_in_chunk,
                    "page_count": len(pages),
                    "is_cross_page": len(pages) > 1,
                    "section_number": section_number,
                },
            )

            chunk_idx += 1
            return chunk_obj

        def get_overlap_segments(
            segments: List[AtomicSegment], target_overlap: int
        ) -> List[AtomicSegment]:
            """Select trailing segments that fit within target_overlap characters."""
            if not segments or target_overlap <= 0:
                return []

            overlap_segments: List[AtomicSegment] = []
            accumulated = 0

            # Scan from end backwards
            for seg in reversed(segments):
                # Do not carry over a heading as a lonely overlap element
                if seg.is_heading:
                    break
                seg_len = len(seg.text)
                if accumulated + seg_len <= target_overlap or not overlap_segments:
                    overlap_segments.insert(0, seg)
                    accumulated += seg_len
                else:
                    break

            # If overlap accounts for more than 50% of the chunk, discard to prevent redundancy
            total_current = sum(len(s.text) for s in segments)
            if total_current > 0 and (accumulated / total_current) > 0.5:
                return []

            return overlap_segments

        for segment in all_segments:
            seg_len = len(segment.text)

            # Check if this segment is a major heading and we already have a reasonable chunk accumulated
            if segment.is_heading and current_char_count >= self.min_chunk_size:
                # Emit preceding content so the heading starts at the top of the new chunk
                chunk = emit_current_chunk()
                if chunk:
                    chunks.append(chunk)

                current_segments = [segment]
                current_char_count = seg_len
                continue

            # Check if adding this segment would exceed the target chunk size
            if current_char_count + seg_len + 2 > self.chunk_size and current_char_count >= self.min_chunk_size:
                # Prepare overlap segments before emitting
                overlap = get_overlap_segments(current_segments, self.chunk_overlap)

                chunk = emit_current_chunk()
                if chunk:
                    chunks.append(chunk)

                # Initialize next chunk with overlap + current segment
                current_segments = overlap + [segment]
                current_char_count = sum(len(s.text) for s in current_segments) + (len(current_segments) - 1) * 2
            else:
                current_segments.append(segment)
                current_char_count += seg_len + 2

        # Emit any trailing segment accumulation
        if current_segments:
            # If the trailing accumulation is tiny and we already emitted chunks, append to the last chunk
            if current_char_count < self.min_chunk_size and chunks:
                last_chunk = chunks[-1]
                trailing_text = "\n\n".join(s.text for s in current_segments).strip()
                if trailing_text:
                    merged_text = f"{last_chunk.text}\n\n{trailing_text}".strip()
                    trailing_pages = set(s.page_number for s in current_segments)
                    combined_pages = sorted(list(set(last_chunk.page_numbers).union(trailing_pages)))

                    # Update last chunk in-place
                    chunks[-1] = LegalChunk(
                        chunk_id=last_chunk.chunk_id,
                        document_id=last_chunk.document_id,
                        document_name=last_chunk.document_name,
                        source_filename=last_chunk.source_filename,
                        document_type=last_chunk.document_type,
                        jurisdiction=last_chunk.jurisdiction,
                        language=last_chunk.language,
                        text=merged_text,
                        page_numbers=combined_pages,
                        chunk_index=last_chunk.chunk_index,
                        character_count=len(merged_text),
                        word_count=len(merged_text.split()),
                        metadata={
                            **last_chunk.metadata,
                            "page_count": len(combined_pages),
                            "is_cross_page": len(combined_pages) > 1,
                        },
                    )
            else:
                final_chunk = emit_current_chunk()
                if final_chunk:
                    chunks.append(final_chunk)

        logger.info(
            "Chunked document '%s': %d pages -> %d chunks",
            doc_name,
            len(sorted_records),
            len(chunks),
        )
        return chunks
