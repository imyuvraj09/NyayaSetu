"""Reproducible Experiment Runner for NyayaSetu Legal RAG Research.

Executes baseline and experimental configurations against benchmark datasets.
Enforces strict architectural isolation to ensure no baseline accidentally leaks
research components from other configurations.

Output structure:
results/experiments/{EXPERIMENT_ID}_{TIMESTAMP}/
    ├── config.yaml
    ├── manifest.json
    ├── metrics.json
    ├── predictions.jsonl
    ├── logs.txt
    └── environment.txt
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

# Add repository root and rag-service to path
REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = REPO_ROOT / "rag-service"

# Load environment variables from rag-service/.env and repo root .env
load_dotenv(RAG_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from evaluation.metrics import (
    calculate_hit_at_k,
    calculate_keyword_coverage,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from evaluation.statistics.bootstrap_ci import compute_experiment_bootstrap_cis
from llm.provider import get_llm_provider
from prompts.prompts import SYSTEM_INSTRUCTION, build_rag_prompt
from rag.context_builder import LegalContextBuilder
from retrieval.bm25_search import BM25SearchEngine, get_bm25_engine
from retrieval.reranker import LegalReranker, get_legal_reranker
from retrieval.similarity_search import SimilaritySearchService
from schemas.retrieval import RerankedChunk, RetrievedChunk
from utils.logger import setup_logging


def get_git_commit() -> str:
    """Retrieve current Git commit hash if available."""
    try:
        res = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
        return res
    except Exception:
        return "UNKNOWN_GIT_COMMIT"


def get_environment_info() -> Dict[str, Any]:
    """Capture runtime and hardware environment metadata."""
    return {
        "os": platform.platform(),
        "python_version": sys.version,
        "processor": platform.processor(),
        "machine": platform.machine(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def validate_configuration(config: Dict[str, Any]) -> None:
    """Verify that baseline configurations do not violate architectural isolation."""
    pipeline = config.get("pipeline", {})
    exp_id = config.get("experiment_id", "")

    if exp_id == "baseline_direct_llm":
        assert not pipeline.get("use_retrieval"), "Direct LLM baseline must have use_retrieval=False"
        assert not pipeline.get("use_dense_retrieval"), "Direct LLM baseline must have use_dense_retrieval=False"
        assert not pipeline.get("use_bm25"), "Direct LLM baseline must have use_bm25=False"
        assert not pipeline.get("use_reranker"), "Direct LLM baseline must have use_reranker=False"

    elif exp_id == "baseline_dense_rag":
        assert pipeline.get("use_dense_retrieval"), "Dense RAG must have use_dense_retrieval=True"
        assert not pipeline.get("use_bm25"), "Dense RAG must have use_bm25=False"
        assert not pipeline.get("use_reranker"), "Dense RAG must have use_reranker=False"
        assert not pipeline.get("use_fact_routing"), "Dense RAG must have use_fact_routing=False"
        assert not pipeline.get("use_compatibility_filter"), "Dense RAG must have use_compatibility_filter=False"

    elif exp_id == "baseline_hybrid_rag":
        assert pipeline.get("use_dense_retrieval"), "Hybrid RAG must have use_dense_retrieval=True"
        assert pipeline.get("use_bm25"), "Hybrid RAG must have use_bm25=True"
        assert pipeline.get("use_hybrid_fusion"), "Hybrid RAG must have use_hybrid_fusion=True"
        assert not pipeline.get("use_reranker"), "Hybrid RAG must have use_reranker=False"

    elif exp_id == "baseline_reranked_rag":
        assert pipeline.get("use_dense_retrieval"), "Reranked RAG must have use_dense_retrieval=True"
        assert pipeline.get("use_reranker"), "Reranked RAG must have use_reranker=True"

    elif exp_id == "routing_only":
        assert pipeline.get("use_dense_retrieval"), "routing_only must have use_dense_retrieval=True"
        assert pipeline.get("use_bm25"), "routing_only must have use_bm25=True"
        assert pipeline.get("use_hybrid_fusion"), "routing_only must have use_hybrid_fusion=True"
        assert pipeline.get("use_fact_routing"), "routing_only must have use_fact_routing=True"
        assert not pipeline.get("use_compatibility_filter"), "routing_only must have use_compatibility_filter=False"
        assert not pipeline.get("use_reranker"), "routing_only must have use_reranker=False"

    elif exp_id.startswith("phase4"):
        assert pipeline.get("use_dense_retrieval"), f"{exp_id} must have use_dense_retrieval=True"
        assert pipeline.get("use_bm25"), f"{exp_id} must have use_bm25=True"
        assert pipeline.get("use_hybrid_fusion"), f"{exp_id} must have use_hybrid_fusion=True"
        assert pipeline.get("use_fact_routing"), f"{exp_id} must have use_fact_routing=True"
        assert pipeline.get("use_compatibility_filter"), f"{exp_id} must have use_compatibility_filter=True"
        assert not pipeline.get("use_reranker"), f"{exp_id} must have use_reranker=False"


def reciprocal_rank_fusion(
    ranked_lists: List[List[RetrievedChunk]],
    k_const: int = 60,
    top_k: int = 5,
    routing_boosts: Optional[Dict[str, float]] = None,
) -> List[RetrievedChunk]:
    """Fuse multiple ranked lists using standard Reciprocal Rank Fusion, with optional soft routing boosts."""
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, RetrievedChunk] = {}

    for r_list in ranked_lists:
        for rank, chunk in enumerate(r_list, start=1):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            score = 1.0 / (k_const + rank)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score

    # Soft boost routed regimes without hard document exclusion
    if routing_boosts:
        for cid, chunk in chunk_map.items():
            doc_name = chunk.document_name or ""
            source_fn = chunk.source_filename or ""
            doc_target = f"{doc_name} {source_fn}".lower()
            max_boost = 1.0
            for doc_pat, boost in routing_boosts.items():
                if doc_pat.lower() in doc_target:
                    if boost > max_boost:
                        max_boost = boost
            if max_boost > 1.0:
                rrf_scores[cid] = rrf_scores[cid] * max_boost

    sorted_chunks = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    fused: List[RetrievedChunk] = []
    for cid in sorted_chunks[:top_k]:
        c = chunk_map[cid]
        # Store fused score
        c.relevance_score = rrf_scores[cid]
        fused.append(c)

    return fused


def run_experiment(
    config_path: str,
    limit: Optional[int] = None,
    output_dir: Optional[str] = None,
    retrieval_only: bool = False,
) -> Dict[str, Any]:
    """Execute experiment defined by config_path.
    
    Supports:
    - Track A (Retrieval Only): Set via retrieval_only=True or benchmark.eval_generation_metrics=False.
    - Track B (Generation): Requires real LLM provider; audits and logs any fallback.
    """
    cfg_file = Path(config_path)
    if not cfg_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(cfg_file, "r", encoding="utf-8") as f:
        raw_config_text = f.read()
        config = yaml.safe_load(raw_config_text)

    validate_configuration(config)

    exp_id = config.get("experiment_id", "experiment")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_dir or f"results/experiments/{exp_id}_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load benchmark
    bm_file = Path(config["benchmark"]["file"])
    with open(bm_file, "r", encoding="utf-8") as f:
        bm_raw = f.read()
        bm_data = json.loads(bm_raw)

    queries = bm_data.get("queries") or bm_data.get("questions", [])
    if limit is not None and limit > 0:
        queries = queries[:limit]

    predictions: List[Dict[str, Any]] = []
    logs: List[str] = []

    def log(msg: str):
        print(msg, flush=True)
        logs.append(msg)

    # Determine evaluation track
    eval_gen = config.get("benchmark", {}).get("eval_generation_metrics", True)
    if retrieval_only:
        eval_gen = False

    # Initialize components based on configuration switches
    pipeline_cfg = config.get("pipeline", {})
    retrieval_cfg = config.get("retrieval", {})
    top_k = retrieval_cfg.get("top_k", 5)
    initial_k = retrieval_cfg.get("initial_k", 20)

    similarity_service = SimilaritySearchService() if pipeline_cfg.get("use_dense_retrieval") else None
    bm25_engine = get_bm25_engine() if pipeline_cfg.get("use_bm25") else None
    if bm25_engine:
        log("Building BM25 index over chunk corpus...")
        bm25_engine.build_index()
    reranker = get_legal_reranker() if pipeline_cfg.get("use_reranker") else None
    if reranker:
        log("Pre-loading reranker model...")
        reranker._load_model()
    context_builder = LegalContextBuilder()

    router = None
    if pipeline_cfg.get("use_fact_routing"):
        from research.issue_router import get_fact_first_router
        log("Initializing Fact-First Legal Issue Router...")
        router = get_fact_first_router()

    compat_engine = None
    if pipeline_cfg.get("use_compatibility_filter"):
        from research.evidence_compatibility.engine import get_evidence_compatibility_engine
        log("Initializing Evidence Compatibility Engine...")
        compat_engine = get_evidence_compatibility_engine(config.get("compatibility", {}).get("config_path"))

    # Track B / Generation LLM Setup & Audit
    llm_provider = None
    generation_provider = "none"
    generation_mode = "unavailable"
    fallback_used = False
    fallback_reason = None

    if eval_gen:
        try:
            llm_provider = get_llm_provider()
            generation_provider = getattr(llm_provider, "provider_name", "unknown")
            if generation_provider == "mock":
                generation_mode = "mock"
                fallback_used = True
                fallback_reason = "Mock provider configured by environment/settings"
            else:
                generation_mode = "real"
                fallback_used = False
                fallback_reason = None
        except Exception as exc:
            generation_mode = "unavailable"
            fallback_used = False
            fallback_reason = f"Provider initialization failed: {str(exc)}"
            llm_provider = None
    else:
        generation_provider = "none"
        generation_mode = "unavailable"
        fallback_used = False
        fallback_reason = "Track A Retrieval-Only Evaluation (Zero LLM dependence)"

    log(f"\n{'='*75}")
    log(f"EXPERIMENT EXECUTION: {exp_id}")
    log(f"Evaluation Track: {'Track A (Retrieval Only)' if not eval_gen else 'Track B (Retrieval + Generation)'}")
    log(f"Benchmark File: {bm_file} | Queries: {len(queries)}")
    log(f"Pipeline Config: {pipeline_cfg}")
    log(f"Generation Mode: {generation_mode.upper()} (Provider: {generation_provider})")
    if generation_mode == "mock":
        log("  [AUDIT WARNING] Generation Mode is MOCK. Latency measurements will NOT represent production latency.")
    log(f"{'='*75}\n")

    evaluable_items: List[Dict[str, Any]] = []

    for idx, q in enumerate(queries, start=1):
        qid = q.get("query_id") or q.get("id")
        qtext = q.get("question", "")
        exp_doc = q.get("expected_document") or (q.get("statute")[0] if q.get("statute") else "")
        exp_kws = q.get("expected_keywords") or []
        is_neg = q.get("negative_or_ambiguous") or (q.get("category") in ("out_of_scope", "ambiguous"))

        retrieved_chunks: List[RetrievedChunk] = []
        retrieval_time = 0.0
        routing_time = 0.0
        routing_decision = None
        e2e_t0 = time.perf_counter()

        # Step 1: Retrieval
        if pipeline_cfg.get("use_retrieval", True):
            ret_t0 = time.perf_counter()

            # Optional Fact-First Legal Issue Routing
            routing_boosts: Optional[Dict[str, float]] = None
            if pipeline_cfg.get("use_fact_routing") and router:
                r_t0 = time.perf_counter()
                routing_decision = router.route_query(qtext)
                routing_time = time.perf_counter() - r_t0

                if not routing_decision.fallback_used and routing_decision.selected_regimes:
                    routing_boosts = {}
                    regimes_cfg = router.config.get("regimes", {})
                    for reg_id in routing_decision.selected_regimes:
                        reg_info = regimes_cfg.get(reg_id, {})
                        doc_filters = reg_info.get("document_filter", [])
                        boost_val = 1.35
                        for cr in routing_decision.candidate_regimes:
                            if cr.regime_id == reg_id:
                                boost_val = cr.priority_boost
                                break
                        for df in doc_filters:
                            routing_boosts[df] = max(routing_boosts.get(df, 1.0), boost_val)

            # Stream 1: Dense Semantic
            dense_candidates: List[RetrievedChunk] = []
            if pipeline_cfg.get("use_dense_retrieval") and similarity_service:
                s_res = similarity_service.search(qtext, top_k=initial_k if pipeline_cfg.get("use_reranker") or pipeline_cfg.get("use_hybrid_fusion") else top_k)
                dense_candidates = s_res.results

            # Stream 2: BM25 Lexical
            bm25_candidates: List[RetrievedChunk] = []
            if pipeline_cfg.get("use_bm25") and bm25_engine:
                b_res = bm25_engine.search(qtext, top_k=initial_k if pipeline_cfg.get("use_reranker") or pipeline_cfg.get("use_hybrid_fusion") else top_k)
                for chunk, score in b_res:
                    bm25_candidates.append(
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

            # Fusion / Candidate Assembly
            if pipeline_cfg.get("use_hybrid_fusion"):
                candidates = reciprocal_rank_fusion(
                    [dense_candidates, bm25_candidates],
                    k_const=retrieval_cfg.get("rrf_constant_k", 60),
                    top_k=initial_k if (pipeline_cfg.get("use_reranker") or pipeline_cfg.get("use_compatibility_filter")) else top_k,
                    routing_boosts=routing_boosts,
                )
            else:
                candidates = dense_candidates

            # Optional Evidence Compatibility Filtering (Phase 4)
            compatibility_time = 0.0
            compat_result_dict = None
            if pipeline_cfg.get("use_compatibility_filter") and compat_engine:
                c_t0 = time.perf_counter()
                facts = routing_decision.normalized_facts.raw_facts if routing_decision and routing_decision.normalized_facts else None
                dim_filter = pipeline_cfg.get("compatibility_dimension", None)
                candidates, comp_res = compat_engine.filter_and_rank_candidates(
                    query=qtext,
                    candidates=candidates,
                    routing_decision=routing_decision,
                    facts=facts,
                    top_k=initial_k if pipeline_cfg.get("use_reranker") else top_k,
                    dimension_filter=dim_filter,
                )
                compatibility_time = time.perf_counter() - c_t0
                compat_result_dict = comp_res.to_dict()

            # Reranking
            reranked_tuples = None
            if pipeline_cfg.get("use_reranker") and reranker:
                reranked_tuples = reranker.rerank(qtext, candidates, top_k=top_k)
                retrieved_chunks = [t[0] for t in reranked_tuples]
            else:
                retrieved_chunks = candidates[:top_k]

            retrieval_time = time.perf_counter() - ret_t0

        retrieved_docs = [c.document_name for c in retrieved_chunks]
        combined_text = " ".join(c.text for c in retrieved_chunks)

        # Convert retrieved chunks to RerankedChunk for context builder
        ranked_chunks_for_context: List[RerankedChunk] = []
        for r_idx, c in enumerate(retrieved_chunks, start=1):
            sim_score = getattr(c, "relevance_score", 0.0)
            rerank_score = sim_score
            if reranked_tuples:
                for rc, r_sc in reranked_tuples:
                    if rc.chunk_id == c.chunk_id:
                        rerank_score = r_sc
                        break
            meta = c.metadata if isinstance(c.metadata, dict) else {}
            ranked_chunks_for_context.append(
                RerankedChunk(
                    rank=r_idx,
                    chunk_id=c.chunk_id,
                    document_name=c.document_name,
                    document_type=c.document_type,
                    source_filename=c.source_filename,
                    page_numbers=c.page_numbers,
                    text=c.text,
                    similarity_score=sim_score,
                    reranker_score=rerank_score,
                    metadata=meta,
                    section_number=meta.get("section_number", "") or getattr(c, "section_number", ""),
                    section_title=meta.get("section_title", "") or getattr(c, "section_title", ""),
                    act_short_name=meta.get("act_short_name", "") or getattr(c, "act_short_name", ""),
                )
            )

        # Step 2: Generation (if enabled)
        generated_answer = ""
        is_mock_generation = False
        prod_e2e_time = None

        if eval_gen and llm_provider:
            try:
                if pipeline_cfg.get("use_retrieval", True) and ranked_chunks_for_context:
                    context_result = context_builder.build_context(ranked_chunks_for_context)
                    prompt = build_rag_prompt(
                        query=qtext,
                        formatted_context=context_result.formatted_context,
                        max_source_index=len(context_result.sources),
                    )
                    llm_response = llm_provider.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
                    generated_answer = llm_response.content
                else:
                    # Direct LLM baseline without retrieval
                    prompt = f"Answer the following Indian legal question based on your knowledge of Indian law. Question: {qtext}"
                    llm_response = llm_provider.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
                    generated_answer = llm_response.content
                
                is_mock_generation = (getattr(llm_provider, "provider_name", "") == "mock")
            except Exception as e:
                is_quota = any(q_term in str(e).lower() for q_term in ["quota", "429", "resource_exhausted"])
                if is_quota:
                    if config.get("llm", {}).get("fallback_allowed", True):
                        from llm.provider import MockLLMProvider
                        log(f"    [AUDIT ALERT] Quota exceeded: Engaging MockLLMProvider for query {qid}")
                        try:
                            mock_p = MockLLMProvider()
                            llm_provider = mock_p
                            generation_mode = "mock"
                            fallback_used = True
                            fallback_reason = f"Quota exceeded: {str(e)}"
                            is_mock_generation = True
                            if pipeline_cfg.get("use_retrieval", True) and ranked_chunks_for_context:
                                p_mock = f"Context: {[c.text[:200] for c in ranked_chunks_for_context]}\nQuestion: {qtext}"
                                resp = mock_p.generate(prompt=p_mock)
                                generated_answer = f"[OFFLINE/MOCK FALLBACK]: {resp.content[:200]}"
                            else:
                                resp = mock_p.generate(prompt=qtext)
                                generated_answer = f"[OFFLINE/MOCK FALLBACK]: {resp.content[:200]}"
                        except Exception as me:
                            generated_answer = f"[LLM GENERATION ERROR: {str(e)}]"
                    else:
                        generation_mode = "unavailable"
                        fallback_used = False
                        fallback_reason = f"Quota exceeded: {str(e)}"
                        generated_answer = f"[GENERATION_UNAVAILABLE: {str(e)}]"
                else:
                    generation_mode = "unavailable"
                    fallback_used = False
                    fallback_reason = f"LLM Generation Error: {str(e)}"
                    generated_answer = f"[LLM GENERATION ERROR: {str(e)}]"

        e2e_time = time.perf_counter() - e2e_t0
        if not eval_gen:
            prod_e2e_time = round(retrieval_time, 4)
        elif not is_mock_generation and generation_mode == "real":
            prod_e2e_time = round(e2e_time, 4)
        else:
            prod_e2e_time = None  # Do not report mock latency as production latency

        # Metric computation
        hit_1 = calculate_hit_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 1, partial_match=True) if exp_doc else 0.0
        hit_3 = calculate_hit_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 3, partial_match=True) if exp_doc else 0.0
        hit_5 = calculate_hit_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 5, partial_match=True) if exp_doc else 0.0
        rr = calculate_reciprocal_rank(retrieved_docs, [exp_doc] if exp_doc else [], partial_match=True) if exp_doc else 0.0
        p5 = calculate_precision_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 5, partial_match=True) if exp_doc else 0.0
        r5 = calculate_recall_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 5, partial_match=True) if exp_doc else 0.0
        ndcg_5 = calculate_ndcg_at_k(retrieved_docs, [exp_doc] if exp_doc else [], 5) if exp_doc else 0.0
        kw_cov = calculate_keyword_coverage(combined_text, exp_kws) if exp_kws else 1.0

        item_result = {
            "query_id": qid,
            "question": qtext,
            "expected_document": exp_doc,
            "is_negative_or_out_of_scope": is_neg,
            "retrieved_documents": retrieved_docs,
            "top_chunk_id": retrieved_chunks[0].chunk_id if retrieved_chunks else None,
            "hit_at_1": hit_1,
            "hit_at_3": hit_3,
            "hit_at_5": hit_5,
            "reciprocal_rank": rr,
            "precision_at_5": p5,
            "recall_at_5": r5,
            "ndcg_at_5": ndcg_5,
            "keyword_coverage": kw_cov,
            "routing_latency_sec": round(routing_time, 4) if pipeline_cfg.get("use_fact_routing") else None,
            "routing_mode": routing_decision.routing_mode.value if routing_decision else None,
            "routing_fallback_used": routing_decision.fallback_used if routing_decision else None,
            "routing_selected_regimes": routing_decision.selected_regimes if routing_decision else None,
            "routing_confidence": round(routing_decision.confidence, 4) if routing_decision else None,
            "compatibility_latency_sec": round(compatibility_time, 6) if pipeline_cfg.get("use_compatibility_filter") else None,
            "evidence_compatibility": compat_result_dict,
            "retrieval_latency_sec": round(retrieval_time, 4),
            "total_latency_sec": round(e2e_time, 4),
            "production_total_latency_sec": prod_e2e_time,
            "is_mock_generation": is_mock_generation,
            "generated_answer_preview": generated_answer[:150] if generated_answer else "",
        }
        predictions.append(item_result)

        if exp_doc and exp_doc.lower() != "none" and not is_neg:
            evaluable_items.append(item_result)

        tag = "HIT" if hit_5 > 0.0 else ("OUT_OF_SCOPE" if is_neg else "MISS")
        log(f"  [{idx:02d}/{len(queries):02d}] {qid:<18}: {tag:<12} (RR={rr:.2f}, Lat={retrieval_time:.2f}s) | {qtext[:45]}...")

    # Compute Summary Metrics
    n_eval = len(evaluable_items)
    valid_prod_lats = [it["production_total_latency_sec"] for it in predictions if it["production_total_latency_sec"] is not None]
    avg_prod_total_lat = round(sum(valid_prod_lats) / len(valid_prod_lats), 4) if valid_prod_lats else None

    # Compute Bootstrap Confidence Intervals
    bootstrap_results = compute_experiment_bootstrap_cis(
        predictions=evaluable_items,
        num_bootstraps=2000,
        random_seed=42,
    )
    bootstrap_dict = {k: v.to_dict() for k, v in bootstrap_results.items()}

    summary_metrics = {
        "experiment_id": exp_id,
        "evaluation_track": "Track A — Retrieval Evaluation" if not eval_gen else "Track B — Generation Evaluation",
        "total_queries": len(queries),
        "statutory_evaluable_queries": n_eval,
        "out_of_scope_or_negative_queries": len(queries) - n_eval,
        "document_hit_at_1": round(sum(it["hit_at_1"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "document_hit_at_3": round(sum(it["hit_at_3"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "document_hit_at_5": round(sum(it["hit_at_5"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "mean_reciprocal_rank": round(sum(it["reciprocal_rank"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "average_precision_at_5": round(sum(it["precision_at_5"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "average_recall_at_5": round(sum(it["recall_at_5"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "mean_ndcg_at_5": round(sum(it["ndcg_at_5"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "average_keyword_coverage": round(sum(it["keyword_coverage"] for it in evaluable_items) / n_eval, 4) if n_eval else 0.0,
        "average_retrieval_latency_sec": round(sum(it["retrieval_latency_sec"] for it in predictions) / len(predictions), 4) if predictions else 0.0,
        "average_routing_latency_sec": (
            round(sum(it["routing_latency_sec"] for it in predictions if it["routing_latency_sec"] is not None) / len(predictions), 4)
            if pipeline_cfg.get("use_fact_routing") and predictions
            else None
        ),
        "average_compatibility_latency_sec": (
            round(sum(it["compatibility_latency_sec"] for it in predictions if it["compatibility_latency_sec"] is not None) / len(predictions), 6)
            if pipeline_cfg.get("use_compatibility_filter") and predictions
            else None
        ),
        "average_total_latency_sec": round(sum(it["total_latency_sec"] for it in predictions) / len(predictions), 4) if predictions else 0.0,
        "average_production_total_latency_sec": avg_prod_total_lat,
        "generation_metadata": {
            "generation_provider": generation_provider,
            "generation_mode": generation_mode,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
        "bootstrap_confidence_intervals": bootstrap_dict,
    }

    # Save outputs
    # 1. Config copy
    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        f.write(raw_config_text)

    # 2. Manifest
    manifest = {
        "experiment_id": exp_id,
        "timestamp": timestamp,
        "git_commit": get_git_commit(),
        "benchmark_file": str(bm_file),
        "benchmark_hash": hashlib.sha256(bm_raw.encode("utf-8")).hexdigest(),
        "configuration_hash": hashlib.sha256(raw_config_text.encode("utf-8")).hexdigest(),
        "queries_evaluated_count": len(queries),
        "embedding_model": retrieval_cfg.get("embedding_model"),
        "reranker_model": retrieval_cfg.get("reranker_model"),
        "top_k": top_k,
        "generation_metadata": summary_metrics["generation_metadata"],
        "summary_metrics": summary_metrics,
    }
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 3. Metrics JSON
    with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    # 4. Predictions JSONL
    with open(run_dir / "predictions.jsonl", "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")

    # 5. Logs
    with open(run_dir / "logs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(logs) + "\n")

    # 6. Environment
    with open(run_dir / "environment.txt", "w", encoding="utf-8") as f:
        json.dump(get_environment_info(), f, indent=2)

    h1_ci = bootstrap_dict.get("Hit@1", {})
    mrr_ci = bootstrap_dict.get("MRR", {})

    log(f"\n{'='*75}")
    log(f"EXPERIMENT COMPLETE: {exp_id}")
    log(f"  Track     : {summary_metrics['evaluation_track']}")
    log(f"  Gen Mode  : {generation_mode.upper()} (Fallback Used: {fallback_used})")
    log(f"  Hit@1     : {summary_metrics['document_hit_at_1']:.4f} (95% CI: [{h1_ci.get('ci_lower', 0):.4f}, {h1_ci.get('ci_upper', 0):.4f}])")
    log(f"  Hit@5     : {summary_metrics['document_hit_at_5']:.4f}")
    log(f"  MRR       : {summary_metrics['mean_reciprocal_rank']:.4f} (95% CI: [{mrr_ci.get('ci_lower', 0):.4f}, {mrr_ci.get('ci_upper', 0):.4f}])")
    log(f"  Prec@5    : {summary_metrics['average_precision_at_5']:.4f}")
    log(f"  Recall@5  : {summary_metrics['average_recall_at_5']:.4f}")
    log(f"  nDCG@5    : {summary_metrics['mean_ndcg_at_5']:.4f}")
    if summary_metrics.get("average_routing_latency_sec") is not None:
        log(f"  Rout. Lat.: {summary_metrics['average_routing_latency_sec']:.4f}s")
    log(f"  Retr. Lat.: {summary_metrics['average_retrieval_latency_sec']:.4f}s")
    if avg_prod_total_lat is not None:
        log(f"  Prod Total Lat.: {avg_prod_total_lat:.4f}s")
    else:
        log("  Prod Total Lat.: [UNAVAILABLE / MOCK NOT REPORTED]")
    log(f"  Artifacts : {run_dir}")
    log(f"{'='*75}\n")

    return summary_metrics


def main():
    parser = argparse.ArgumentParser(description="Run NyayaSetu research experiment.")
    parser.add_argument("--config", required=True, help="Path to YAML experiment config")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries for smoke testing")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    parser.add_argument("--retrieval_only", action="store_true", help="Execute Track A retrieval-only evaluation without LLM generation")
    args = parser.parse_args()

    run_experiment(
        args.config,
        limit=args.limit,
        output_dir=args.output_dir,
        retrieval_only=args.retrieval_only,
    )


if __name__ == "__main__":
    main()

