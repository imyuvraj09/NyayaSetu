"""
Hierarchical Case-Law Navigation Tree and Metadata Index for NyayaSetu.

Supports structured navigation:
COURT -> YEAR -> CASE -> PARAGRAPH -> CHUNK

Also provides inverted lookup indexes:
- case name / citation / alias lookup
- section-to-case lookup (e.g. which cases interpret Section 63 BNS or Section 375 IPC)
- topic-to-case lookup (e.g. consent, murder, procedural fairness)
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from schemas.case_law import CaseLawChunk, CourtLevel
from utils.logger import get_logger

logger = get_logger(__name__)


class CaseLawTreeIndex:
    """In-memory hierarchical index and inverted metadata index over case law."""

    def __init__(self, chunks_file: Optional[Path] = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.chunks_file = chunks_file or (base_dir / "data" / "processed" / "case_law_chunks.jsonl")
        self.raw_data_file = base_dir / "data" / "raw" / "judgments" / "verified_judgments.json"

        # Hierarchical tree: court -> year -> case_id -> paragraphs
        self.tree: Dict[str, Dict[str, Dict[str, List[CaseLawChunk]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # Inverted indexes
        self.case_by_name: Dict[str, str] = {}  # normalized name -> document_id
        self.case_by_citation: Dict[str, str] = {}  # normalized citation -> document_id
        self.cases_by_section: Dict[str, Set[str]] = defaultdict(set)  # section_num -> set of document_ids
        self.cases_by_topic: Dict[str, Set[str]] = defaultdict(set)  # topic -> set of document_ids
        self.chunks_by_id: Dict[str, CaseLawChunk] = {}
        self.chunks_by_case: Dict[str, List[CaseLawChunk]] = defaultdict(list)

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Parse processed chunks and build all hierarchical and inverted indexes."""
        if not self.chunks_file.exists():
            # If processed chunks not yet generated, build from raw if available
            if self.raw_data_file.exists():
                from case_law.ingestion.case_law_chunker import CaseLawChunker
                from case_law.ingestion.case_law_loader import CaseLawLoader
                docs = CaseLawLoader(self.raw_data_file).load_documents()
                chunks = CaseLawChunker(self.raw_data_file).chunk_documents(docs)
            else:
                logger.warning("No case-law files found to build tree index.")
                return
        else:
            chunks = []
            with open(self.chunks_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        chunks.append(CaseLawChunk.model_validate_json(line))

        for c in chunks:
            self.chunks_by_id[c.chunk_id] = c
            self.chunks_by_case[c.document_id].append(c)

            court_key = c.court_level.value if hasattr(c.court_level, "value") else str(c.court_level)
            year = c.judgment_date.split("-")[0] if "-" in c.judgment_date else "UNKNOWN"

            self.tree[court_key][year][c.document_id].append(c)

            # Inverted lookups
            norm_name = " ".join(c.case_name.lower().split())
            self.case_by_name[norm_name] = c.document_id

            norm_cite = "".join(c.citation.lower().split())
            self.case_by_citation[norm_cite] = c.document_id

            for sec in c.sections_referred:
                sec_clean = "".join(filter(str.isalnum, sec.lower()))
                if sec_clean:
                    self.cases_by_section[sec_clean].add(c.document_id)

            for topic in c.topics:
                norm_top = topic.lower().strip()
                self.cases_by_topic[norm_top].add(c.document_id)

        logger.info(
            "Built CaseLawTreeIndex: %d courts, %d cases, %d chunks, %d section mappings",
            len(self.tree),
            len(self.chunks_by_case),
            len(self.chunks_by_id),
            len(self.cases_by_section),
        )

    def find_cases_for_section(self, section_num: str) -> List[str]:
        """Find case document IDs that interpret or cite the given section number."""
        sec_clean = "".join(filter(str.isalnum, section_num.lower()))
        return list(self.cases_by_section.get(sec_clean, set()))

    def find_cases_for_topic(self, topic: str) -> List[str]:
        """Find case document IDs discussing a legal topic."""
        matches = set()
        topic_lower = topic.lower().strip()
        for indexed_topic, doc_ids in self.cases_by_topic.items():
            if topic_lower in indexed_topic or indexed_topic in topic_lower:
                matches.update(doc_ids)
        return list(matches)

    def find_case_by_name_or_citation(self, query: str) -> Optional[str]:
        """Exact or substring match for case name or citation in query."""
        q_lower = query.lower()
        for name, doc_id in self.case_by_name.items():
            # Check if key words of case appear
            parts = name.split(" v. ")
            if len(parts) == 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                if (p1 in q_lower and p2 in q_lower) or (name in q_lower):
                    return doc_id
            elif name in q_lower:
                return doc_id

        # Check citation
        q_cite_clean = "".join(filter(str.isalnum, q_lower))
        for cite_clean, doc_id in self.case_by_citation.items():
            clean_c = "".join(filter(str.isalnum, cite_clean))
            if clean_c in q_cite_clean:
                return doc_id

        return None

    def get_chunks_for_case(self, document_id: str) -> List[CaseLawChunk]:
        """Retrieve all paragraph chunks for a given case."""
        return self.chunks_by_case.get(document_id, [])

    def get_all_chunks(self) -> List[CaseLawChunk]:
        """Return all indexed case law chunks."""
        return list(self.chunks_by_id.values())
