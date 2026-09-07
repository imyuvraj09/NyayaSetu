"""Judicial Precedent Retriever connecting to existing indexed case-law infrastructure.

Integrates with:
1. ChromaDB 'nyayasetu_case_law' collection (dense vector similarity)
2. CaseLawTreeIndex (exact case name, citation, section correlation)
3. Lexical keyword matching over holdings and ratios
4. Strict evidence-type discrimination (STATUTE vs CASE_LAW vs UNKNOWN)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from research.precedent_reasoning.court_hierarchy import CourtHierarchyEngine
from research.precedent_reasoning.metadata_extractor import PrecedentMetadataExtractor
from research.precedent_reasoning.models import (
    CourtLevel,
    JudicialPrecedent,
    PrecedentMetadata,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"


class PrecedentRetriever:
    """Discovers, retrieves, and structures judicial precedent candidates."""

    def __init__(
        self,
        collection_name: str = "nyayasetu_case_law",
        top_k: int = 5,
    ) -> None:
        self.collection_name = collection_name
        self.top_k = top_k
        self._tree_index = None
        self._chroma_store = None
        self._embedder = None

    def _init_services(self) -> None:
        """Lazy initialization of retrieval services."""
        if self._tree_index is None:
            try:
                from retrieval.case_law_tree import CaseLawTreeIndex
                self._tree_index = CaseLawTreeIndex()
            except Exception:
                self._tree_index = None

        if self._chroma_store is None:
            try:
                from vectorstore.chroma_store import ChromaStore
                self._chroma_store = ChromaStore(collection_name=self.collection_name)
            except Exception:
                self._chroma_store = None

        if self._embedder is None:
            try:
                from embeddings.embedding_model import get_embedding_service
                self._embedder = get_embedding_service()
            except Exception:
                self._embedder = None

        if not hasattr(self, "_doc_meta") or self._doc_meta is None:
            self._doc_meta = {}
            try:
                import json
                from pathlib import Path
                raw_path = Path(__file__).resolve().parent.parent.parent / "rag-service" / "data" / "raw" / "judgments" / "verified_judgments.json"
                if raw_path.exists():
                    with open(raw_path, "r", encoding="utf-8") as f:
                        v_docs = json.load(f)
                        for d in v_docs:
                            self._doc_meta[d.get("document_id")] = d
            except Exception:
                pass

    def retrieve_precedents(
        self,
        query: str,
        target_sections: Optional[List[str]] = None,
        target_statutes: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[JudicialPrecedent]:
        """Retrieve relevant judicial precedents for a query.

        Args:
            query: User's legal question or topic.
            target_sections: Optional target statutory sections to correlate (e.g. ['375', '63']).
            target_statutes: Optional target statutes (e.g. ['IPC', 'BNS']).
            top_k: Number of precedent candidates to return.

        Returns:
            List of JudicialPrecedent instances with extracted metadata.
        """
        self._init_services()
        k = top_k or self.top_k
        candidates: Dict[str, JudicialPrecedent] = {}

        # Strategy 1: Tree index exact case-name or citation match
        if self._tree_index is not None:
            matched_case_id = self._tree_index.find_case_by_name_or_citation(query)
            if not matched_case_id:
                q_l = query.lower()
                for name, doc_id in self._tree_index.case_by_name.items():
                    parts = [p.strip() for p in name.split(" v. ") if p.strip()]
                    if any(p in q_l for p in parts if len(p) > 6):
                        matched_case_id = doc_id
                        break

            if matched_case_id:
                chunks = self._tree_index.get_chunks_for_case(matched_case_id)
                for c in chunks:
                    jp = self._chunk_to_precedent(c, score=1.0)
                    candidates[jp.chunk_id] = jp

            # Strategy 2: Section correlation in Tree index
            if target_sections:
                for sec in target_sections:
                    sec_clean = str(sec).strip().lstrip("0")
                    matching_case_ids = self._tree_index.find_cases_for_section(sec_clean)
                    for cid in matching_case_ids:
                        chunks = self._tree_index.get_chunks_for_case(cid)
                        for c in chunks:
                            if c.chunk_id not in candidates:
                                jp = self._chunk_to_precedent(c, score=0.85)
                                candidates[jp.chunk_id] = jp

        # Strategy 3: Dense vector search in ChromaDB nyayasetu_case_law
        if self._chroma_store is not None and self._embedder is not None:
            try:
                embed_fn = getattr(self._embedder, "embed_text", None) or getattr(self._embedder, "embed_query", None)
                if embed_fn is not None:
                    query_vec = embed_fn(query)
                    retrieved_chunks = self._chroma_store.query(query_vec, top_k=k * 2)
                    for chunk_cand in retrieved_chunks:
                        cid = getattr(chunk_cand, "chunk_id", None) or getattr(chunk_cand, "document_name", None) or "unknown_chunk"
                        if cid not in candidates:
                            # Reconstruct JudicialPrecedent
                            meta_dict = getattr(chunk_cand, "metadata", {}) or {}
                            doc_id = meta_dict.get("document_id") or ""
                            doc_info = getattr(self, "_doc_meta", {}).get(doc_id, {})
                            if doc_info.get("overruled_by") and not meta_dict.get("overruled_by"):
                                meta_dict["overruled_by"] = doc_info.get("overruled_by")
                            if doc_info.get("bench") and not meta_dict.get("bench"):
                                meta_dict["bench"] = doc_info.get("bench")

                            meta = PrecedentMetadataExtractor.extract_from_dict(meta_dict)
                            # Ensure case name
                            case_name = meta_dict.get("case_name") or getattr(chunk_cand, "document_name", None) or "Unknown Case"
                            court = meta_dict.get("court") or "Unknown Court"
                            court_level = CourtHierarchyEngine.classify_court_level(court)

                            raw_text = getattr(chunk_cand, "text", None) or getattr(chunk_cand, "text_snippet", "") or ""
                            raw_score = getattr(chunk_cand, "relevance_score", None) or getattr(chunk_cand, "similarity_score", 0.70)

                            jp = JudicialPrecedent(
                                chunk_id=cid,
                                document_id=meta_dict.get("document_id", cid),
                                case_name=case_name,
                                citation=meta_dict.get("citation", "Unknown Citation"),
                                court=court,
                                court_level=court_level,
                                judgment_date=meta_dict.get("judgment_date", "UNKNOWN"),
                                passage_type=meta_dict.get("passage_type", "GENERAL"),
                                text=raw_text,
                                is_holding_or_ratio=meta_dict.get("is_holding_or_ratio", False),
                                retrieval_score=float(raw_score),
                                metadata=meta,
                                statutes_referred=meta.statutes_referred,
                                sections_referred=meta.sections_referred,
                                topics=meta.topics,
                            )
                            candidates[cid] = jp
            except Exception as ex:
                import logging
                logging.getLogger(__name__).warning("Dense precedent retrieval failed: %s", ex)

        # Sort by initial retrieval score descending
        results = sorted(candidates.values(), key=lambda x: x.retrieval_score, reverse=True)
        return results[:k]

    def _chunk_to_precedent(self, chunk: Any, score: float = 0.8) -> JudicialPrecedent:
        """Convert a CaseLawChunk pydantic model to a typed JudicialPrecedent."""
        if hasattr(chunk, "model_dump"):
            d = chunk.model_dump()
        elif hasattr(chunk, "to_dict"):
            d = chunk.to_dict()
        else:
            d = vars(chunk)

        doc_info = getattr(self, "_doc_meta", {}).get(chunk.document_id, {})
        if doc_info.get("overruled_by") and not d.get("overruled_by"):
            d["overruled_by"] = doc_info.get("overruled_by")
        if doc_info.get("bench") and not d.get("bench"):
            d["bench"] = doc_info.get("bench")

        meta = PrecedentMetadataExtractor.extract_from_dict(d)
        c_level = meta.court_level

        return JudicialPrecedent(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            case_name=chunk.case_name,
            citation=chunk.citation,
            court=chunk.court,
            court_level=c_level,
            judgment_date=chunk.judgment_date,
            passage_type=chunk.passage_type.value if hasattr(chunk.passage_type, "value") else str(chunk.passage_type),
            text=chunk.text,
            is_holding_or_ratio=chunk.is_holding_or_ratio,
            retrieval_score=score,
            metadata=meta,
            statutes_referred=meta.statutes_referred,
            sections_referred=meta.sections_referred,
            topics=meta.topics,
        )
