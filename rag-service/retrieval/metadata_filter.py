"""
Metadata and duplicate filtering module for NyayaSetu RAG Service.

Filters raw retrieval candidates to eliminate duplicate chunk IDs, identical passages,
and excessive dominance by any single legal statute, maximizing candidate diversity.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from schemas.retrieval import RetrievedChunk
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class MetadataFilter:
    """Deterministic filter for retrieval candidates.

    Attributes:
        max_per_document: Maximum number of chunks permitted from any single enactment (default: 5).
    """

    def __init__(self, max_per_document: Optional[int] = None) -> None:
        self.max_per_document = (
            max_per_document if max_per_document is not None else settings.MAX_CHUNKS_PER_DOCUMENT
        )

    def filter_candidates(
        self,
        candidates: List[RetrievedChunk],
        max_per_document: Optional[int] = None,
    ) -> Tuple[List[RetrievedChunk], Dict[str, int]]:
        """Filter candidates by deduplication and document distribution constraints.

        Operations:
        1. Drop duplicate chunk IDs.
        2. Drop duplicate normalized text bodies (e.g. repeated definitions or identical annexures).
        3. Enforce max_chunks_per_document to preserve multi-document statutory diversity.

        Args:
            candidates: Ranked list of RetrievedChunk objects from initial dense search.
            max_per_document: Override limit for chunks allowed per document.

        Returns:
            Tuple of (filtered_candidates, filter_statistics).
        """
        limit = max_per_document if max_per_document is not None else self.max_per_document

        filtered: List[RetrievedChunk] = []
        seen_chunk_ids: Set[str] = set()
        seen_texts: Set[str] = set()
        doc_counts: Dict[str, int] = defaultdict(int)

        stats = {
            "initial_candidates": len(candidates),
            "dropped_duplicate_id": 0,
            "dropped_duplicate_text": 0,
            "dropped_document_cap": 0,
            "retained_candidates": 0,
        }

        for chunk in candidates:
            # 1. Deduplicate by chunk ID
            if chunk.chunk_id in seen_chunk_ids:
                stats["dropped_duplicate_id"] += 1
                continue

            # 2. Deduplicate by exact text (whitespace-normalized)
            norm_text = " ".join(chunk.text.split())
            if norm_text in seen_texts:
                stats["dropped_duplicate_text"] += 1
                continue

            # 3. Document dominance cap
            doc_key = chunk.document_name or "Unknown"
            if limit > 0 and doc_counts[doc_key] >= limit:
                stats["dropped_document_cap"] += 1
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            seen_texts.add(norm_text)
            doc_counts[doc_key] += 1
            filtered.append(chunk)

        stats["retained_candidates"] = len(filtered)
        logger.info(
            "Candidate filtering: %d in -> %d retained (dropped %d duplicate IDs, %d duplicate texts, %d capped)",
            stats["initial_candidates"],
            stats["retained_candidates"],
            stats["dropped_duplicate_id"],
            stats["dropped_duplicate_text"],
            stats["dropped_document_cap"],
        )

        return filtered, stats
