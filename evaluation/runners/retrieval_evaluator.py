"""
Retrieval evaluation runner for NyayaSetu Legal Knowledge Assistant.

Calculates Hit@K (Hit@1, Hit@3, Hit@5), Mean Reciprocal Rank (MRR),
keyword coverage, and document diversity across benchmark queries.
"""

from typing import Any, Dict, List, Optional

from evaluation.schemas import RetrievalEvaluationItem
from retrieval.advanced_retriever import AdvancedRetriever
from utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalEvaluator:
    """Evaluates retrieval quality against statutory benchmark questions."""

    def __init__(self, retriever: Optional[AdvancedRetriever] = None) -> None:
        self.retriever = retriever or AdvancedRetriever()

    def evaluate_query(
        self,
        query_item: Dict[str, Any],
        top_k: int = 5,
    ) -> RetrievalEvaluationItem:
        """Run a single benchmark query and calculate retrieval metrics.

        Args:
            query_item: Dictionary containing 'id', 'question', 'expected_document', 'expected_keywords'.
            top_k: Top results count to retrieve.

        Returns:
            RetrievalEvaluationItem with calculated metrics.
        """
        qid = query_item["id"]
        qtext = query_item["question"]
        expected_doc = query_item["expected_document"].strip()
        expected_kws = query_item.get("expected_keywords", [])
        category = query_item.get("category", "General")
        difficulty = query_item.get("difficulty", "medium")

        # Execute Phase 6 advanced retrieval
        result = self.retriever.retrieve(query=qtext, final_k=top_k)
        retrieved_chunks = result.results

        retrieved_docs = [chunk.document_name.strip() for chunk in retrieved_chunks]

        # 1. Calculate Hit@K
        hit_at_1 = len(retrieved_docs) >= 1 and (expected_doc.lower() in retrieved_docs[0].lower())
        hit_at_3 = any(expected_doc.lower() in d.lower() for d in retrieved_docs[:3])
        hit_at_5 = any(expected_doc.lower() in d.lower() for d in retrieved_docs[:5])

        # 2. Calculate Reciprocal Rank
        reciprocal_rank = 0.0
        for rank, doc in enumerate(retrieved_docs, start=1):
            if expected_doc.lower() in doc.lower():
                reciprocal_rank = 1.0 / rank
                break

        # 3. Calculate Keyword Coverage
        combined_text = " ".join(c.text.lower() for c in retrieved_chunks)
        if expected_kws:
            matched_kws = sum(1 for kw in expected_kws if kw.lower() in combined_text)
            kw_coverage = round(matched_kws / len(expected_kws), 4)
        else:
            kw_coverage = 1.0

        top_chunk_id = retrieved_chunks[0].chunk_id if retrieved_chunks else None
        top_score = retrieved_chunks[0].reranker_score if retrieved_chunks else None

        return RetrievalEvaluationItem(
            query_id=qid,
            query=qtext,
            category=category,
            difficulty=difficulty,
            expected_document=expected_doc,
            retrieved_documents=retrieved_docs,
            hit_at_1=hit_at_1,
            hit_at_3=hit_at_3,
            hit_at_5=hit_at_5,
            reciprocal_rank=round(reciprocal_rank, 4),
            keyword_coverage=kw_coverage,
            retrieved_chunks_count=len(retrieved_chunks),
            top_chunk_id=top_chunk_id,
            top_reranker_score=top_score,
        )
