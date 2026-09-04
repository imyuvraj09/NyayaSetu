"""
Advanced Legal-Evidence-First Retrieval Orchestrator for NyayaSetu.

Implements multi-strategy statutory retrieval:
1. Legal Query Analysis & Statute Routing
2. Multi-Part Query Decomposition
3. Multi-Strategy Candidate Generation:
   - Dense Semantic Retrieval (BAAI/bge-small-en-v1.5)
   - BM25 Lexical Keyword Retrieval
   - Exact Section-Number Matching
   - Section-Title Matching
   - Legal Concept & Statutory Phrase Expansion
   - Sub-query Retrieval for Multi-part Inquiries
4. Evidence Fusion using Reciprocal Rank Fusion (RRF) with Statute Purity Boosting
5. Evidence Sufficiency Verification & Automatic Secondary Fallback Retrieval
6. Cross-Encoder Reranking (BAAI/bge-reranker-base)
7. Provenance-Rich Serialization with Section Numbers, Titles, and Debug Telemetry
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from retrieval.answer_facet_analyzer import (
    AnswerFacetAnalyzer,
    FacetAnalysisResult,
    get_answer_facet_analyzer,
)
from retrieval.bm25_search import BM25SearchEngine, get_bm25_engine
from retrieval.evidence_checker import LegalEvidenceChecker, get_evidence_checker
from retrieval.facet_evidence_models import (
    EvidenceStatus,
    FacetEvidence,
    FacetEvidenceSource,
)
from retrieval.legal_concept_mapper import LegalConceptMapper, get_legal_concept_mapper
from retrieval.metadata_filter import MetadataFilter
from retrieval.query_analyzer import (
    KNOWN_ACT_REGISTRY,
    LegalQueryAnalysis,
    LegalQueryAnalyzer,
    get_query_analyzer,
)
from retrieval.reranker import LegalReranker, get_legal_reranker
from retrieval.section_indexer import (
    CANONICAL_SECTION_TITLES,
    IndexedChunk,
    SectionIndexer,
    get_section_indexer,
)
from retrieval.similarity_search import SimilaritySearchService
from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk, RetrievedChunk
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedRetriever:
    """End-to-end multi-strategy legal evidence retrieval engine."""

    def __init__(
        self,
        similarity_service: Optional[SimilaritySearchService] = None,
        reranker: Optional[LegalReranker] = None,
        metadata_filter: Optional[MetadataFilter] = None,
        query_analyzer: Optional[LegalQueryAnalyzer] = None,
        concept_mapper: Optional[LegalConceptMapper] = None,
        section_indexer: Optional[SectionIndexer] = None,
        bm25_engine: Optional[BM25SearchEngine] = None,
        evidence_checker: Optional[LegalEvidenceChecker] = None,
        facet_analyzer: Optional[AnswerFacetAnalyzer] = None,
        initial_k: Optional[int] = None,
        final_k: Optional[int] = None,
        max_per_document: Optional[int] = None,
    ) -> None:
        self.similarity_service = similarity_service or SimilaritySearchService()
        self.reranker = reranker or get_legal_reranker()
        self.metadata_filter = metadata_filter or MetadataFilter()
        self.query_analyzer = query_analyzer or get_query_analyzer()
        self.concept_mapper = concept_mapper or get_legal_concept_mapper()
        self.section_indexer = section_indexer or get_section_indexer()
        self.bm25_engine = bm25_engine or get_bm25_engine()
        self.evidence_checker = evidence_checker or get_evidence_checker()
        self.facet_analyzer = facet_analyzer or get_answer_facet_analyzer()
        self.initial_k = initial_k or settings.INITIAL_RETRIEVAL_K
        self.final_k = final_k or settings.FINAL_RETRIEVAL_K
        self.max_per_document = max_per_document or settings.MAX_CHUNKS_PER_DOCUMENT

    def retrieve(
        self,
        query: str,
        initial_k: Optional[int] = None,
        final_k: Optional[int] = None,
        max_per_document: Optional[int] = None,
    ) -> AdvancedRetrievalResult:
        """Execute evidence-first multi-strategy retrieval."""
        ik = initial_k or self.initial_k
        fk = final_k or self.final_k
        mpd = max_per_document or self.max_per_document

        start_time = datetime.now(timezone.utc)

        # ---------------------------------------------------------
        # Step 1: Legal Query Analysis & Routing
        # ---------------------------------------------------------
        analysis: LegalQueryAnalysis = self.query_analyzer.analyze(query)
        facet_analysis: FacetAnalysisResult = self.facet_analyzer.analyze_facets(
            query=analysis.normalized_query,
            detected_entities=analysis.entities,
        )
        logger.info(
            "Query Analysis: Act='%s', Domain='%s', Intent='%s', Multi-part=%s, Sub-queries=%d | Facets: %s",
            analysis.act,
            analysis.legal_domain,
            analysis.intent,
            analysis.is_multi_part,
            len(analysis.sub_queries),
            facet_analysis.required_facets,
        )

        # Collect all valid target acts (from primary analysis + sub-queries)
        target_doc_ids: Set[str] = set()
        if analysis.document_id:
            target_doc_ids.add(analysis.document_id)
        for sq in analysis.sub_queries:
            if sq.target_act:
                for act_info in KNOWN_ACT_REGISTRY:
                    if (
                        act_info["act_name"].lower() == sq.target_act.lower()
                        or sq.target_act.lower() in [a.lower() for a in act_info["aliases"]]
                        or sq.target_act.lower() == act_info["short_name"].lower()
                    ):
                        target_doc_ids.add(act_info["document_id"])

        # ---------------------------------------------------------
        # Step 2: Legal Concept & Section Mapping
        # ---------------------------------------------------------
        exp_terms, stat_phrases, candidate_sections = self.concept_mapper.map_query_concepts(
            query=analysis.normalized_query,
            document_id=analysis.document_id if len(target_doc_ids) <= 1 else None,
            entities=analysis.entities,
        )

        # Augment statutory phrases with keywords from detected facets
        for f in facet_analysis.facets:
            if f.required:
                stat_phrases.extend(f.retrieval_keywords[:3])
        stat_phrases = list(dict.fromkeys(stat_phrases))

        # Combine sections extracted from query and mapped from concepts
        all_candidate_sections = list(dict.fromkeys(analysis.section_candidates + candidate_sections))

        # ---------------------------------------------------------
        # Step 3: Multi-Strategy Candidate Generation
        # ---------------------------------------------------------
        strategy_candidates: Dict[str, List[RetrievedChunk]] = {
            "dense_primary": [],
            "dense_subqueries": [],
            "bm25_primary": [],
            "bm25_phrases": [],
            "section_number_matches": [],
            "section_title_matches": [],
        }

        # Strategy A: Dense Semantic Search (Primary Query)
        dense_search = self.similarity_service.search(
            query=analysis.normalized_query,
            top_k=ik,
        )
        strategy_candidates["dense_primary"] = dense_search.results

        # Strategy A2: Dense Search on Sub-queries & Facet queries
        if analysis.is_multi_part:
            for sq in analysis.sub_queries:
                sq_res = self.similarity_service.search(query=sq.sub_query_text, top_k=8)
                strategy_candidates["dense_subqueries"].extend(sq_res.results)

        for facet in facet_analysis.facets:
            if facet.required and facet.suggested_subquery:
                sq_res = self.similarity_service.search(query=facet.suggested_subquery, top_k=5)
                strategy_candidates["dense_subqueries"].extend(sq_res.results)

        # Strategy B: BM25 Lexical Search (Primary Query)
        bm25_hits = self.bm25_engine.search(
            query=analysis.normalized_query,
            document_id=analysis.document_id if len(target_doc_ids) <= 1 else None,
            top_k=ik,
        )
        for chunk, score in bm25_hits:
            strategy_candidates["bm25_primary"].append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    document_type=chunk.document_type,
                    source_filename=chunk.source_filename,
                    page_numbers=chunk.page_numbers,
                    text=chunk.text,
                    relevance_score=round(min(1.0, score / 40.0), 4),
                    metadata=chunk.metadata,
                )
            )

        # Strategy B2: BM25 on statutory phrases
        for phrase in stat_phrases:
            phrase_hits = self.bm25_engine.search(
                query=phrase,
                document_id=analysis.document_id if len(target_doc_ids) <= 1 else None,
                top_k=5,
            )
            for chunk, score in phrase_hits:
                strategy_candidates["bm25_phrases"].append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        document_name=chunk.document_name,
                        document_type=chunk.document_type,
                        source_filename=chunk.source_filename,
                        page_numbers=chunk.page_numbers,
                        text=chunk.text,
                        relevance_score=round(min(1.0, score / 40.0), 4),
                        metadata=chunk.metadata,
                    )
                )

        # Strategy C: Exact Section-Number Matching
        if all_candidate_sections:
            sec_chunks = self.section_indexer.search_by_section_candidates(
                document_id=analysis.document_id if len(target_doc_ids) <= 1 else None,
                section_candidates=all_candidate_sections,
            )
            for chunk in sec_chunks:
                strategy_candidates["section_number_matches"].append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        document_name=chunk.document_name,
                        document_type=chunk.document_type,
                        source_filename=chunk.source_filename,
                        page_numbers=chunk.page_numbers,
                        text=chunk.text,
                        relevance_score=0.98,
                        metadata=chunk.metadata,
                    )
                )

        # Strategy D: Section-Title Matching
        for entity in analysis.entities:
            title_chunks = self.section_indexer.get_chunks_by_section_title(
                title_query=entity,
                document_id=analysis.document_id if len(target_doc_ids) <= 1 else None,
            )
            for chunk in title_chunks:
                strategy_candidates["section_title_matches"].append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        document_name=chunk.document_name,
                        document_type=chunk.document_type,
                        source_filename=chunk.source_filename,
                        page_numbers=chunk.page_numbers,
                        text=chunk.text,
                        relevance_score=0.95,
                        metadata=chunk.metadata,
                    )
                )

        if "punishment" in analysis.requested_information:
            punish_title = f"punishment for {analysis.entities[0]}" if analysis.entities else "punishment"
            p_chunks = self.section_indexer.get_chunks_by_section_title(
                title_query=punish_title,
                document_id=analysis.document_id,
            )
            for chunk in p_chunks:
                strategy_candidates["section_title_matches"].append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        document_name=chunk.document_name,
                        document_type=chunk.document_type,
                        source_filename=chunk.source_filename,
                        page_numbers=chunk.page_numbers,
                        text=chunk.text,
                        relevance_score=0.96,
                        metadata=chunk.metadata,
                    )
                )

        # ---------------------------------------------------------
        # Step 4: Evidence Fusion via Reciprocal Rank Fusion (RRF)
        # ---------------------------------------------------------
        rrf_k = 60.0
        candidate_pool: Dict[str, RetrievedChunk] = {}
        rrf_scores: Dict[str, float] = defaultdict(float)

        strategy_weights = {
            "section_number_matches": 2.5,
            "section_title_matches": 2.2,
            "dense_subqueries": 1.8,
            "bm25_phrases": 1.6,
            "bm25_primary": 1.4,
            "dense_primary": 1.0,
        }

        for strategy_name, chunks in strategy_candidates.items():
            weight = strategy_weights.get(strategy_name, 1.0)
            seen_strat_ids = set()
            rank = 1
            for chunk in chunks:
                if chunk.chunk_id in seen_strat_ids:
                    continue
                seen_strat_ids.add(chunk.chunk_id)
                candidate_pool[chunk.chunk_id] = chunk

                # RRF calculation: weight / (rrf_k + rank)
                rrf_scores[chunk.chunk_id] += weight / (rrf_k + rank)
                rank += 1

        # Statute Purity Boost: if query specifies or targets Acts, boost chunks from those Acts
        for chunk_id, chunk in candidate_pool.items():
            meta = chunk.metadata or {}
            c_doc_id = meta.get("document_id") or chunk.chunk_id.split("_c")[0]
            if target_doc_ids:
                if c_doc_id in target_doc_ids:
                    rrf_scores[chunk_id] *= 2.0
                else:
                    rrf_scores[chunk_id] *= 0.5

        sorted_candidates = sorted(
            candidate_pool.values(),
            key=lambda c: rrf_scores[c.chunk_id],
            reverse=True,
        )

        # ---------------------------------------------------------
        # Step 5: Evidence Sufficiency Verification & Secondary Retrieval
        # ---------------------------------------------------------
        sufficiency_result = self.evidence_checker.check_and_recover(
            analysis=analysis,
            current_candidates=sorted_candidates[:15],
        )

        # If secondary retrieval recovered missing statutory provisions, inject them at top
        if sufficiency_result.secondary_retrieval_triggered and sufficiency_result.recovered_chunks:
            for rec_chunk in reversed(sufficiency_result.recovered_chunks):
                rec_retrieved = RetrievedChunk(
                    chunk_id=rec_chunk.chunk_id,
                    document_name=rec_chunk.document_name,
                    document_type=rec_chunk.document_type,
                    source_filename=rec_chunk.source_filename,
                    page_numbers=rec_chunk.page_numbers,
                    text=rec_chunk.text,
                    relevance_score=0.99,
                    metadata=rec_chunk.metadata,
                )
                if rec_retrieved.chunk_id in candidate_pool:
                    rrf_scores[rec_retrieved.chunk_id] += 1.0
                else:
                    candidate_pool[rec_retrieved.chunk_id] = rec_retrieved
                    rrf_scores[rec_retrieved.chunk_id] = 2.0

            sorted_candidates = sorted(
                candidate_pool.values(),
                key=lambda c: rrf_scores[c.chunk_id],
                reverse=True,
            )

        # ---------------------------------------------------------
        # Step 5B: Facet Coverage Determination & Targeted Facet Recovery
        # ---------------------------------------------------------
        facet_coverage: Dict[str, Dict[str, Any]] = {}
        facet_evidence_map: Dict[str, FacetEvidence] = {}
        facet_recovery_triggered = False

        is_unindexed_query = getattr(analysis, "is_unindexed_statute", False)

        for facet in facet_analysis.facets:
            if not facet.required:
                continue

            f_name = facet.name
            supporting_sections: List[str] = []
            supporting_chunk_ids: List[str] = []
            supporting_sources: List[FacetEvidenceSource] = []
            best_support_score = 0.0
            entity_term = analysis.entities[0] if analysis.entities else ""

            if is_unindexed_query:
                # Query targets an enactment genuinely not in our indexed corpus
                facet_coverage[f_name] = {
                    "facet_name": f_name,
                    "display_name": facet.display_name,
                    "supported": False,
                    "evidence_status": EvidenceStatus.NOT_FOUND.value,
                    "source_sections": [],
                    "supporting_chunk_ids": [],
                    "best_support_score": 0.0,
                }
                facet_evidence_map[f_name] = FacetEvidence(
                    facet=f_name,
                    display_name=facet.display_name,
                    required=facet.required,
                    evidence_status=EvidenceStatus.NOT_FOUND,
                    sources=[],
                )
                continue

            # Inspect current top candidates for this facet
            for cand in sorted_candidates[:15]:
                meta = cand.metadata or {}
                c_doc_id = meta.get("document_id") or cand.chunk_id.split("_c")[0]
                if target_doc_ids and c_doc_id not in target_doc_ids:
                    # Do NOT let chunks from unrelated statutes satisfy facet evidence for target enactment
                    continue

                c_text = cand.text.lower()
                idx_chunk = self.section_indexer.chunks_by_id.get(cand.chunk_id)
                titles = idx_chunk.section_titles if idx_chunk else []
                sections = idx_chunk.section_numbers if idx_chunk else []

                # Check title match
                title_match = any(
                    f_name in t.lower() or any(kw.lower() in t.lower() for kw in facet.retrieval_keywords[:3])
                    for t in titles
                )
                # Check keyword match in text
                kw_match = any(re.search(rf"\b{re.escape(kw.lower())}\b", c_text) for kw in facet.retrieval_keywords)
                # Check semantic facet indicator match
                indic_match = self.evidence_checker.has_facet_evidence(f_name, cand.text, titles, entity_term)

                if title_match or kw_match or indic_match:
                    score = (0.40 if title_match else 0.0) + (0.35 if kw_match or indic_match else 0.0) + (0.25 if sections else 0.0)
                    if score > best_support_score:
                        best_support_score = score
                    if sections:
                        supporting_sections.extend(sections)
                    supporting_chunk_ids.append(cand.chunk_id)
                    supporting_sources.append(
                        FacetEvidenceSource(
                            act=cand.document_name,
                            section=sections[0] if sections else "",
                            section_title=titles[0] if titles else "",
                            page=str(cand.page_numbers[0]) if cand.page_numbers else "",
                            chunk_id=cand.chunk_id,
                            text_snippet=cand.text[:300],
                        )
                    )

            supporting_sections = list(dict.fromkeys(supporting_sections))
            is_supported = (best_support_score >= 0.35) or len(supporting_chunk_ids) > 0

            # Facet-Specific Targeted Secondary Retrieval if missing
            if not is_supported:
                logger.info(
                    "Required facet '%s' lacking direct evidence in candidates. Triggering targeted recovery...",
                    f_name,
                )
                target_doc = analysis.document_id if len(target_doc_ids) <= 1 else None

                recovered_chunks: List[Any] = []
                # 1. Search section indexer by facet title
                title_chunks = self.section_indexer.get_chunks_by_section_title(facet.display_name, target_doc)
                recovered_chunks.extend(title_chunks[:3])

                # 2. Search BM25 by facet display name and keywords
                bm25_facet_hits = self.bm25_engine.search(
                    query=f"{facet.display_name} {entity_term}".strip(),
                    document_id=target_doc,
                    top_k=3,
                )
                for chunk, _ in bm25_facet_hits:
                    if chunk.chunk_id not in [r.chunk_id for r in recovered_chunks]:
                        recovered_chunks.append(chunk)

                if recovered_chunks:
                    facet_recovery_triggered = True
                    for rec in recovered_chunks:
                        retrieved_obj = RetrievedChunk(
                            chunk_id=rec.chunk_id,
                            document_name=rec.document_name,
                            document_type=rec.document_type,
                            source_filename=rec.source_filename,
                            page_numbers=rec.page_numbers,
                            text=rec.text,
                            relevance_score=0.99,
                            metadata=rec.metadata,
                        )
                        candidate_pool[retrieved_obj.chunk_id] = retrieved_obj
                        rrf_scores[retrieved_obj.chunk_id] += 2.5
                        if rec.section_numbers:
                            supporting_sections.extend(rec.section_numbers)
                        supporting_sources.append(
                            FacetEvidenceSource(
                                act=rec.document_name,
                                section=rec.section_numbers[0] if rec.section_numbers else "",
                                section_title=rec.section_titles[0] if rec.section_titles else "",
                                page=str(rec.page_numbers[0]) if rec.page_numbers else "",
                                chunk_id=rec.chunk_id,
                                text_snippet=rec.text[:300],
                            )
                        )
                    is_supported = True
                    best_support_score = 0.85

            evidence_status = EvidenceStatus.FOUND if is_supported else EvidenceStatus.NOT_FOUND

            facet_ev_obj = FacetEvidence(
                facet=f_name,
                display_name=facet.display_name,
                required=facet.required,
                evidence_status=evidence_status,
                supported=is_supported,
                support_score=best_support_score,
                sources=supporting_sources[:3],
                evidence_text=supporting_sources[0].text_snippet if supporting_sources else "",
            )
            facet_evidence_map[f_name] = facet_ev_obj
            facet_coverage[f_name] = facet_ev_obj.to_dict()

        if facet_recovery_triggered:
            sorted_candidates = sorted(
                candidate_pool.values(),
                key=lambda c: rrf_scores[c.chunk_id],
                reverse=True,
            )

        # ---------------------------------------------------------
        # Step 6: Metadata & Diversity Filtering
        # ---------------------------------------------------------
        filtered_candidates, filter_stats = self.metadata_filter.filter_candidates(
            candidates=sorted_candidates,
            max_per_document=mpd,
        )

        # ---------------------------------------------------------
        # Step 7: Cross-Encoder Reranking with Enriched Statutory Context
        # ---------------------------------------------------------
        candidates_to_rerank = filtered_candidates[:max(ik, len(filtered_candidates))]

        # Prefix chunks with statutory provenance so cross-encoder recognizes act and section
        enriched_candidates: List[RetrievedChunk] = []
        original_chunk_map: Dict[str, RetrievedChunk] = {}
        for c in candidates_to_rerank:
            original_chunk_map[c.chunk_id] = c
            idx_info = self.section_indexer.chunks_by_id.get(c.chunk_id)
            prefix_parts = [c.document_name]
            if idx_info and idx_info.primary_section:
                prefix_parts.append(f"Section {idx_info.primary_section}")
            if idx_info and idx_info.primary_title:
                prefix_parts.append(f"({idx_info.primary_title})")
            prefix = " ".join(prefix_parts) + ": "
            enriched_candidates.append(
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    document_name=c.document_name,
                    document_type=c.document_type,
                    source_filename=c.source_filename,
                    page_numbers=c.page_numbers,
                    text=f"{prefix}{c.text}",
                    relevance_score=c.relevance_score,
                    metadata=c.metadata,
                )
            )

        scored_pairs = self.reranker.rerank(
            query=analysis.normalized_query,
            candidates=enriched_candidates,
            top_k=len(enriched_candidates),
        )

        # Statute Purity Boosting: Prioritize target enactment over cross-references
        adjusted_scored_pairs = []
        for chunk, raw_score in scored_pairs:
            c_doc_id = chunk.metadata.get("document_id") or chunk.chunk_id.split("_c")[0]
            adj_score = raw_score
            if target_doc_ids:
                if c_doc_id in target_doc_ids:
                    adj_score += 0.35  # Primary enactment boost
                else:
                    adj_score -= 0.20  # Non-target enactment penalty
            adjusted_scored_pairs.append((chunk, adj_score, raw_score))

        adjusted_scored_pairs.sort(key=lambda x: x[1], reverse=True)

        # Topic Compatibility & Out-of-Scope Section Filtering
        clean_scored_pairs = []
        for chunk, adj_score, raw_score in adjusted_scored_pairs:
            idx_info = self.section_indexer.chunks_by_id.get(chunk.chunk_id)
            sec_num = str(idx_info.primary_section if idx_info else "").strip()
            sec_title = str(idx_info.primary_title if idx_info else "").lower()
            text_lower = chunk.text.lower()

            # Exclude Section 108 (Abetment of suicide) for murder / circumstantial evidence queries
            if "108" in sec_num or "abetment of suicide" in sec_title or "abetment of suicide" in text_lower[:100]:
                if getattr(analysis, "offence", None) == "murder" or getattr(analysis, "primary_issue", None) == "circumstantial_evidence":
                    logger.info("Filtered out Section 108 (Abetment of suicide) for murder/circumstantial evidence query.")
                    continue

            # Check query excluded topics
            is_excluded = False
            for ex in getattr(analysis, "excluded_topics", []):
                if ex.lower() in sec_title:
                    is_excluded = True
                    break
            if is_excluded:
                logger.info("Filtered out statutory section '%s' (%s) due to excluded topic.", sec_num, sec_title)
                continue

            clean_scored_pairs.append((chunk, adj_score, raw_score))

        adjusted_scored_pairs = clean_scored_pairs
        selected_pairs = adjusted_scored_pairs[:fk]

        # Generalized Facet Representation Guarantee:
        # Ensure EVERY required facet with available evidence is represented in selected_pairs
        for facet in facet_analysis.facets:
            if not facet.required:
                continue
            f_name = facet.name
            cov = facet_coverage.get(f_name, {})
            if not cov.get("supported", False):
                continue

            entity_term = analysis.entities[0] if analysis.entities else ""

            # Check if selected_pairs already contains a chunk supporting this facet
            has_facet_in_top_k = any(
                self.evidence_checker.has_facet_evidence(
                    f_name,
                    c.text,
                    self.section_indexer.chunks_by_id.get(c.chunk_id).section_titles if self.section_indexer.chunks_by_id.get(c.chunk_id) else [],
                    entity_term,
                )
                for c, _, _ in selected_pairs
            )

            if not has_facet_in_top_k:
                # Find best candidate from adjusted_scored_pairs[fk:]
                for c, adj, raw in adjusted_scored_pairs[fk:]:
                    titles = self.section_indexer.chunks_by_id.get(c.chunk_id).section_titles if self.section_indexer.chunks_by_id.get(c.chunk_id) else []
                    if self.evidence_checker.has_facet_evidence(f_name, c.text, titles, entity_term):
                        # Replace the lowest-priority redundant chunk in selected_pairs
                        if len(selected_pairs) >= fk:
                            selected_pairs.pop()
                        selected_pairs.append((c, adj, raw))
                        logger.info("Promoted candidate '%s' into top context to guarantee facet '%s' coverage.", c.chunk_id, f_name)
                        break

        # Multi-Statute Representation Guarantee:
        # If query targets multiple distinct Acts (e.g. cross-domain query), ensure each target Act is represented in top-k
        if len(target_doc_ids) > 1:
            represented_docs = {
                (c.metadata.get("document_id") or c.chunk_id.split("_c")[0])
                for c, _, _ in selected_pairs
            }
            for t_doc in target_doc_ids:
                if t_doc not in represented_docs:
                    # Find highest scored candidate for this document from adjusted_scored_pairs
                    for c, adj, raw in adjusted_scored_pairs:
                        c_doc = c.metadata.get("document_id") or c.chunk_id.split("_c")[0]
                        if c_doc == t_doc and c.chunk_id not in [sel[0].chunk_id for sel in selected_pairs]:
                            if len(selected_pairs) >= fk:
                                selected_pairs.pop()
                            selected_pairs.append((c, adj, raw))
                            represented_docs.add(t_doc)
                            break

        # ---------------------------------------------------------
        # Step 8: Build Provenance-Rich Final Results
        # ---------------------------------------------------------
        final_chunks: List[RerankedChunk] = []
        for rank, (chunk, _, raw_score) in enumerate(selected_pairs, start=1):
            original_chunk = original_chunk_map.get(chunk.chunk_id, chunk)
            indexed_info = self.section_indexer.chunks_by_id.get(chunk.chunk_id)
            sec_num = indexed_info.primary_section if indexed_info else ""
            sec_title = indexed_info.primary_title if indexed_info else ""
            short_name = indexed_info.act_short_name if indexed_info else ""

            # If section_number is empty, scan text for statutory section indicators
            if not sec_num:
                sec_match = re.search(r"\b(?:Section|Sec\.)\s+(\d+[A-Z]?)\b", original_chunk.text, re.IGNORECASE) or re.search(r"^\s*(\d+[A-Z]?)\.\s*\(", original_chunk.text)
                if sec_match:
                    sec_num = sec_match.group(1)
                    if indexed_info and indexed_info.document_id:
                        doc_catalog = CANONICAL_SECTION_TITLES.get(indexed_info.document_id, {})
                        if sec_num in doc_catalog:
                            sec_title = doc_catalog[sec_num]

            # If chunk contains multiple sections, select the one explicitly matching query candidates or required facets
            if indexed_info and len(indexed_info.section_numbers) > 1:
                if all_candidate_sections:
                    for cand_sec in all_candidate_sections:
                        if cand_sec in indexed_info.section_numbers:
                            sec_num = cand_sec
                            doc_catalog = CANONICAL_SECTION_TITLES.get(indexed_info.document_id, {})
                            if cand_sec in doc_catalog:
                                sec_title = doc_catalog[cand_sec]
                            break
                else:
                    # Check if any required facet keyword or title matches a specific section in this chunk
                    matched_sec = False
                    for s_num, s_t in zip(indexed_info.section_numbers, indexed_info.section_titles):
                        for f in facet_analysis.facets:
                            if not f.required:
                                continue
                            if f.name in s_t.lower() or any(kw.lower() in s_t.lower() for kw in f.retrieval_keywords[:3]):
                                sec_num = s_num
                                sec_title = s_t
                                matched_sec = True
                                break
                        if matched_sec:
                            break

            final_chunks.append(
                RerankedChunk(
                    rank=rank,
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    document_type=chunk.document_type,
                    source_filename=chunk.source_filename or chunk.metadata.get("source_filename", ""),
                    page_numbers=chunk.page_numbers,
                    text=original_chunk.text,  # Clean original text
                    similarity_score=chunk.relevance_score,
                    reranker_score=round(raw_score, 4),
                    metadata=chunk.metadata,
                    section_number=sec_num,
                    section_title=sec_title,
                    act_short_name=short_name,
                )
            )

        doc_dist = dict(Counter(c.document_name for c in final_chunks))

        debug_telemetry = {
            "strategy_counts": {k: len(v) for k, v in strategy_candidates.items()},
            "fused_candidate_count": len(candidate_pool),
            "evidence_sufficiency": {
                "is_sufficient": sufficiency_result.is_sufficient,
                "verified_aspects": sufficiency_result.verified_aspects,
                "missing_aspects": sufficiency_result.missing_aspects,
                "secondary_retrieval_triggered": sufficiency_result.secondary_retrieval_triggered,
                "recovered_chunks_count": len(sufficiency_result.recovered_chunks),
            },
            "candidate_sections": all_candidate_sections,
            "facet_coverage": facet_coverage,
            "facet_analysis": facet_analysis.to_dict(),
            "candidate_summary": [
                {
                    "rank": c.rank,
                    "chunk_id": c.chunk_id,
                    "act": c.act_short_name or c.document_name,
                    "section": c.section_number,
                    "title": c.section_title,
                    "pages": c.page_numbers,
                    "score": c.reranker_score,
                }
                for c in final_chunks
            ],
        }

        logger.info(
            "Evidence-First Retrieval complete: %d initial -> %d filtered -> %d final. Top provision: %s Sec %s (%s)",
            len(candidate_pool),
            len(filtered_candidates),
            len(final_chunks),
            final_chunks[0].act_short_name if final_chunks else "None",
            final_chunks[0].section_number if final_chunks else "",
            final_chunks[0].section_title if final_chunks else "",
        )

        return AdvancedRetrievalResult(
            original_query=analysis.original_query,
            normalized_query=analysis.normalized_query,
            initial_k=ik,
            final_k=fk,
            initial_candidates_count=len(candidate_pool),
            filtered_candidates_count=len(filtered_candidates),
            final_results_count=len(final_chunks),
            results=final_chunks,
            initial_results=filtered_candidates[:fk],
            document_distribution=doc_dist,
            query_analysis=analysis.to_dict(),
            facet_analysis=facet_analysis.to_dict(),
            facet_coverage=facet_coverage,
            debug_telemetry=debug_telemetry,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        )
