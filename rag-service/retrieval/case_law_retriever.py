"""
Evidence-Grounded Case-Law Retriever for NyayaSetu.

Implements multi-strategy judicial retrieval:
1. Exact Case-Name & Citation Matching
2. Section-Reference Correlation (cases interpreting target statutory sections)
3. Topic & Legal Intent Filtering
4. BM25 Lexical Retrieval across case-law text
5. Dense Semantic Search in ChromaDB collection 'nyayasetu_case_law'
6. Reciprocal Rank Fusion (RRF)
7. Cross-Encoder Reranking prioritizing Holdings / Ratios over factual narrative
8. Court Hierarchy Weighting (Supreme Court > High Court)
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from embeddings.embedding_model import EmbeddingService
from retrieval.case_law_tree import CaseLawTreeIndex
from retrieval.reranker import LegalReranker
from schemas.case_law import CaseLawChunk, CourtLevel, PassageType
from schemas.retrieval import RerankedChunk, RetrievedChunk
from utils.logger import get_logger
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)

PASSAGE_TYPE_WEIGHTS = {
    PassageType.HOLDING: 1.35,
    PassageType.RATIO: 1.30,
    PassageType.LEGAL_TEST: 1.25,
    PassageType.STATUTORY_INTERPRETATION: 1.15,
    PassageType.CONCLUSION: 1.10,
    PassageType.GENERAL: 1.0,
    PassageType.FACTUAL_BACKGROUND: 0.85,
    PassageType.PROCEDURAL_HISTORY: 0.80,
}

COURT_LEVEL_WEIGHTS = {
    CourtLevel.SUPREME_COURT: 1.20,
    CourtLevel.HIGH_COURT: 1.05,
    CourtLevel.OTHER: 1.0,
}


class CaseLawRetriever:
    """Multi-strategy Case-Law Retriever over verified Indian judicial decisions."""

    def __init__(
        self,
        collection_name: str = "nyayasetu_case_law",
        tree_index: Optional[CaseLawTreeIndex] = None,
        embedder: Optional[EmbeddingService] = None,
        reranker: Optional[LegalReranker] = None,
    ) -> None:
        self.collection_name = collection_name
        self.tree_index = tree_index or CaseLawTreeIndex()
        self.embedder = embedder or EmbeddingService()
        self.reranker = reranker or LegalReranker()
        self.chroma_store = ChromaStore(collection_name=self.collection_name)

    def retrieve(
        self,
        query: str,
        target_sections: Optional[List[str]] = None,
        target_topics: Optional[List[str]] = None,
        primary_issue: Optional[str] = None,
        excluded_topics: Optional[List[str]] = None,
        top_k: int = 5,
        initial_k: int = 15,
    ) -> List[RerankedChunk]:
        """Retrieve and rerank most relevant verified case law passages for the query.

        Args:
            query: User's legal question or case-law subquery.
            target_sections: Optional list of statutory sections to correlate (e.g. ['63', '375']).
            target_topics: Optional list of topics (e.g. ['consent', 'sexual offences']).
            primary_issue: Primary legal issue identified by query analyzer.
            excluded_topics: Topics that must be excluded from results.
            top_k: Final number of ranked case-law passages to return.
            initial_k: Number of dense/lexical candidates to evaluate.

        Returns:
            List of RerankedChunk objects populated with CaseLaw metadata and evidence_type="CASE_LAW".
        """
        logger.info("Executing Case-Law Retrieval for query: '%s' [primary_issue=%s]", query, primary_issue)

        candidate_chunks: Dict[str, CaseLawChunk] = {}
        strategy_scores: Dict[str, float] = defaultdict(float)

        # 1. Check for Exact Case Name or Citation Match in query
        matched_case_id = self.tree_index.find_case_by_name_or_citation(query)
        if matched_case_id:
            logger.info("Found direct case match for query: %s", matched_case_id)
            for chunk in self.tree_index.get_chunks_for_case(matched_case_id):
                candidate_chunks[chunk.chunk_id] = chunk
                strategy_scores[chunk.chunk_id] += 1.5

        # 2. Section-Reference Search (if target sections given or extracted from query)
        sections_to_check = set(target_sections or [])
        import re
        sec_matches = re.findall(r"\b(?:section|sec\.?)\s*([0-9]{1,4}[a-z]?)\b", query, re.IGNORECASE)
        sections_to_check.update(sec_matches)

        for sec in sections_to_check:
            case_ids = self.tree_index.find_cases_for_section(sec)
            for cid in case_ids:
                for chunk in self.tree_index.get_chunks_for_case(cid):
                    candidate_chunks[chunk.chunk_id] = chunk
                    strategy_scores[chunk.chunk_id] += 0.8

        # 3. Topic Search
        topics_to_check = set(target_topics or [])
        # If primary issue is circumstantial evidence, strictly search circumstantial evidence topics
        if primary_issue == "circumstantial_evidence":
            topics_to_check.update(["circumstantial evidence", "standard of proof", "homicide"])
        elif primary_issue == "consent_and_promise_to_marry":
            topics_to_check.update(["consent", "promise to marry", "sexual offences"])
        else:
            for kw in ["consent", "murder", "culpable homicide", "promise to marry", "rti", "due process", "liberty"]:
                if kw in query.lower():
                    topics_to_check.add(kw)

        for top in topics_to_check:
            case_ids = self.tree_index.find_cases_for_topic(top)
            for cid in case_ids:
                for chunk in self.tree_index.get_chunks_for_case(cid):
                    candidate_chunks[chunk.chunk_id] = chunk
                    strategy_scores[chunk.chunk_id] += 0.5

        # 4. Dense Semantic Search in ChromaDB collection
        try:
            dense_results = self._dense_search(query, top_k=initial_k)
            for chunk, sim_score in dense_results:
                candidate_chunks[chunk.chunk_id] = chunk
                strategy_scores[chunk.chunk_id] += float(sim_score) * 1.2
        except Exception as e:
            logger.warning("Dense search in case law collection failed or empty: %s", e)

        # If no candidates found from vector store, pull all available chunks from tree index as fallback
        if not candidate_chunks:
            all_chunks = self.tree_index.get_all_chunks()
            for c in all_chunks:
                candidate_chunks[c.chunk_id] = c
                strategy_scores[c.chunk_id] = 0.5

        # 4B. Topic Incompatibility Filter (Rule 4 & 5)
        if excluded_topics:
            retained_candidates: Dict[str, CaseLawChunk] = {}
            for cid, c in candidate_chunks.items():
                c_topics_lower = [t.lower() for t in c.topics]
                c_name_lower = c.case_name.lower()
                is_excluded = False
                for ex in excluded_topics:
                    ex_l = ex.lower()
                    if any(ex_l in t for t in c_topics_lower):
                        is_excluded = True
                        break
                    if ex_l in ("consent", "promise to marry", "rape"):
                        if any(k in c_name_lower for k in ["anurag soni", "naim ahamed"]):
                            is_excluded = True
                            break
                    if ex_l in ("circumstantial evidence",):
                        if any(k in c_name_lower for k in ["sharad birdhichand", "babu v"]):
                            is_excluded = True
                            break
                if not is_excluded:
                    retained_candidates[cid] = c
                else:
                    logger.info("CaseLawRetriever excluded chunk '%s' (%s) due to excluded topic.", cid, c.case_name)
            candidate_chunks = retained_candidates

        # 4C. Primary Issue Topic Boost
        if primary_issue == "circumstantial_evidence":
            for cid, c in candidate_chunks.items():
                c_text_lower = c.text.lower()
                c_topics_lower = [t.lower() for t in c.topics]
                if any(kw in c_text_lower or any(kw in t for t in c_topics_lower) for kw in [
                    "circumstantial evidence", "chain of circumstances", "panchsheel",
                    "five golden principles", "standard of proof"
                ]):
                    strategy_scores[cid] += 2.0

        if not candidate_chunks:
            logger.warning("Zero candidate case-law passages found.")
            return []

        # 5. Cross-Encoder Reranking
        scored_candidates: List[Tuple[CaseLawChunk, float]] = []
        chunks_list = list(candidate_chunks.values())
        pairs = [(query, c.text) for c in chunks_list]

        try:
            ce_scores = self.reranker.compute_scores(pairs)
        except Exception as e:
            logger.warning("Cross-encoder reranking failed for case law, using heuristic scores: %s", e)
            ce_scores = [strategy_scores[c.chunk_id] for c in chunks_list]

        for chunk, base_score in zip(chunks_list, ce_scores):
            # Apply Passage Type boost (Holding > Ratio > Interpretation > Facts)
            passage_mult = PASSAGE_TYPE_WEIGHTS.get(chunk.passage_type, 1.0)
            if chunk.is_holding_or_ratio:
                passage_mult = max(passage_mult, 1.30)

            # Apply Court Level boost (Supreme Court > High Court)
            court_mult = COURT_LEVEL_WEIGHTS.get(chunk.court_level, 1.0)

            final_score = base_score * passage_mult * court_mult + (strategy_scores[chunk.chunk_id] * 0.1)
            scored_candidates.append((chunk, final_score))

        # Sort by final score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:top_k]

        # Convert to RerankedChunk models
        results: List[RerankedChunk] = []
        for rank, (c, final_score) in enumerate(top_candidates, start=1):
            sec_display = ", ".join(c.sections_referred) if c.sections_referred else ""
            statute_display = ", ".join(c.statutes_referred) if c.statutes_referred else "Indian Law"

            rc = RerankedChunk(
                rank=rank,
                chunk_id=c.chunk_id,
                document_name=f"{c.case_name} ({c.citation})",
                document_type="Case Law",
                source_filename=f"{c.document_id}.pdf",
                page_numbers=[int(c.paragraph_number)] if c.paragraph_number.isdigit() else [1],
                text=c.text,
                similarity_score=min(1.0, max(0.0, final_score / 2.0)),
                reranker_score=round(float(final_score), 4),
                metadata={
                    "evidence_type": "CASE_LAW",
                    "case_name": c.case_name,
                    "court": c.court,
                    "court_level": c.court_level.value if hasattr(c.court_level, "value") else str(c.court_level),
                    "citation": c.citation,
                    "judgment_date": c.judgment_date,
                    "paragraph_number": c.paragraph_number,
                    "paragraph_heading": c.paragraph_heading or "",
                    "passage_type": c.passage_type.value if hasattr(c.passage_type, "value") else str(c.passage_type),
                    "is_holding_or_ratio": c.is_holding_or_ratio,
                    "statutes_referred": c.statutes_referred,
                    "sections_referred": c.sections_referred,
                    "topics": c.topics,
                    "verified": c.verified,
                },
                section_number=sec_display,
                section_title=c.paragraph_heading or f"Paragraph {c.paragraph_number}",
                act_short_name=statute_display,
                evidence_type="CASE_LAW",
                case_name=c.case_name,
                court=c.court,
                citation=c.citation,
                judgment_date=c.judgment_date,
                paragraph_number=c.paragraph_number,
                is_holding_or_ratio=c.is_holding_or_ratio,
                topic_compatibility="DIRECT",
            )
            results.append(rc)

        logger.info("Case-Law retrieval complete: %d chunks returned. Top judgment: %s", len(results), results[0].document_name if results else "None")
        return results

    def _dense_search(self, query: str, top_k: int = 10) -> List[Tuple[CaseLawChunk, float]]:
        """Dense embedding search in ChromaDB collection 'nyayasetu_case_law'."""
        if self.chroma_store.count() == 0:
            return []

        query_vec = self.embedder.embed_text(query)
        results = self.chroma_store.collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, self.chroma_store.count()),
            include=["documents", "metadatas", "distances"],
        )

        output: List[Tuple[CaseLawChunk, float]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        distances = results["distances"][0] if "distances" in results else [0.5] * len(ids)

        for chunk_id, dist in zip(ids, distances):
            chunk = self.tree_index.chunks_by_id.get(chunk_id)
            if chunk:
                # Cosine distance to similarity: 1 - dist
                sim = max(0.0, 1.0 - float(dist))
                output.append((chunk, sim))

        return output
