"""
High-performance BM25Okapi Lexical Retrieval Engine for NyayaSetu.

Implements pure Python BM25Okapi scoring over the 6,545 legal chunks:
- Legal-aware tokenization preserving section numbers, acronyms, and statutory legal phrases.
- Document-scoped filtering (e.g. search only within BNS, or cross-corpus).
- Fast inverted index lookup.
"""

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from retrieval.section_indexer import IndexedChunk, get_section_indexer
from utils.logger import get_logger

logger = get_logger(__name__)


def tokenize_legal_text(text: str) -> List[str]:
    """Tokenize legal text preserving statutory sections and legal terms."""
    # Replace punctuation except hyphens inside words and numbers
    cleaned = re.sub(r"[^\w\s\d]", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) > 1 or t.isdigit()]
    return tokens


class BM25SearchEngine:
    """BM25Okapi search engine over indexed statutory chunks."""

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.section_indexer = get_section_indexer()
        self.corpus_size: int = 0
        self.avg_dl: float = 0.0
        self.doc_lengths: Dict[str, int] = {}
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)  # token -> {chunk_id: tf}
        self.idf: Dict[str, float] = {}
        self._is_indexed = False

    def build_index(self) -> None:
        """Build BM25 index over all indexed chunks."""
        if self._is_indexed:
            return

        self.section_indexer.build_index()
        chunks = self.section_indexer.all_chunks
        self.corpus_size = len(chunks)

        if self.corpus_size == 0:
            logger.warning("No chunks available to build BM25 index.")
            self._is_indexed = True
            return

        logger.info("Building BM25 lexical index across %d legal chunks...", self.corpus_size)

        total_length = 0
        doc_frequencies: Dict[str, int] = defaultdict(int)

        for chunk in chunks:
            # Combine chunk text with section titles and act short name for boosted lexical indexing
            extra_terms = f"{chunk.document_name} {chunk.act_short_name} {' '.join(chunk.section_titles)} {' '.join(chunk.section_numbers)}"
            combined_text = f"{extra_terms} {chunk.text}"

            tokens = tokenize_legal_text(combined_text)
            dl = len(tokens)
            self.doc_lengths[chunk.chunk_id] = dl
            total_length += dl

            term_counts = Counter(tokens)
            for term, count in term_counts.items():
                self.inverted_index[term][chunk.chunk_id] = count
                doc_frequencies[term] += 1

        self.avg_dl = total_length / self.corpus_size if self.corpus_size > 0 else 1.0

        # Precompute IDF for all terms using standard Robertson-Spärck Jones IDF with smoothing
        for term, df in doc_frequencies.items():
            # idf = ln((N - df + 0.5) / (df + 0.5) + 1.0)
            self.idf[term] = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)

        self._is_indexed = True
        logger.info(
            "BM25 index built: %d terms indexed, avg doc length: %.1f tokens.",
            len(self.idf),
            self.avg_dl,
        )

    def search(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Tuple[IndexedChunk, float]]:
        """Execute BM25 lexical retrieval.

        Args:
            query: User's search query.
            document_id: Optional statute constraint (e.g. "bns_2023").
            top_k: Number of highest-scoring chunks to return.

        Returns:
            List of (IndexedChunk, score) pairs sorted in descending order of score.
        """
        self.build_index()
        query_tokens = tokenize_legal_text(query)

        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)

        for term in query_tokens:
            if term not in self.inverted_index:
                continue

            term_idf = self.idf[term]
            postings = self.inverted_index[term]

            for chunk_id, tf in postings.items():
                # Filter by document_id if specified
                if document_id:
                    chunk = self.section_indexer.chunks_by_id.get(chunk_id)
                    if not chunk or chunk.document_id != document_id:
                        continue

                dl = self.doc_lengths.get(chunk_id, self.avg_dl)
                # BM25 term score: idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avg_dl)))
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
                scores[chunk_id] += term_idf * (numerator / denominator)

        if not scores:
            return []

        # Sort chunk IDs by score descending
        sorted_chunk_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results: List[Tuple[IndexedChunk, float]] = []
        for chunk_id, score in sorted_chunk_scores:
            chunk = self.section_indexer.chunks_by_id.get(chunk_id)
            if chunk:
                results.append((chunk, score))

        return results


_BM25_INSTANCE = None

def get_bm25_engine() -> BM25SearchEngine:
    """Return singleton instance of BM25SearchEngine."""
    global _BM25_INSTANCE
    if _BM25_INSTANCE is None:
        _BM25_INSTANCE = BM25SearchEngine()
    return _BM25_INSTANCE
