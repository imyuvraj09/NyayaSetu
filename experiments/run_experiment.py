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


def reciprocal_rank_fusion(
    ranked_lists: List[List[RetrievedChunk]],
    k_const: int = 60,
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """Fuse multiple ranked lists using standard Reciprocal Rank Fusion."""
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, RetrievedChunk] = {}

    for r_list in ranked_lists:
        for rank, chunk in enumerate(r_list, start=1):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            score = 1.0 / (k_const + rank)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score

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
) -> Dict[str, Any]:
    """Execute experiment defined by config_path."""
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
    llm_provider = get_llm_provider()

    log(f"\n{'='*75}")
    log(f"EXPERIMENT EXECUTION: {exp_id}")
    log(f"Benchmark File: {bm_file} | Queries: {len(queries)}")
    log(f"Pipeline Config: {pipeline_cfg}")
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
        e2e_t0 = time.perf_counter()

        # Step 1: Retrieval
        if pipeline_cfg.get("use_retrieval", True):
            ret_t0 = time.perf_counter()

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
                    top_k=initial_k if pipeline_cfg.get("use_reranker") else top_k,
                )
            else:
                candidates = dense_candidates

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
        if config.get("benchmark", {}).get("eval_generation_metrics", True):
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
            except Exception as e:
                if "QUOTA_EXCEEDED" in str(e) or "429" in str(e) or "quota" in str(e).lower():
                    # Fallback to MockLLMProvider to prevent stalling full benchmark runs
                    from llm.provider import MockLLMProvider
                    log(f"    [NOTICE] LLM Quota exceeded: Engaging deterministic MockLLM fallback for query {qid}")
                    try:
                        mock_p = MockLLMProvider()
                        llm_provider = mock_p
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
                    generated_answer = f"[LLM GENERATION ERROR: {str(e)}]"

        e2e_time = time.perf_counter() - e2e_t0

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
            "retrieval_latency_sec": round(retrieval_time, 4),
            "total_latency_sec": round(e2e_time, 4),
            "generated_answer_preview": generated_answer[:150] if generated_answer else "",
        }
        predictions.append(item_result)

        if exp_doc and exp_doc.lower() != "none" and not is_neg:
            evaluable_items.append(item_result)

        tag = "HIT" if hit_5 > 0.0 else ("OUT_OF_SCOPE" if is_neg else "MISS")
        log(f"  [{idx:02d}/{len(queries):02d}] {qid:<18}: {tag:<12} (RR={rr:.2f}, Lat={retrieval_time:.2f}s) | {qtext[:45]}...")

    # Compute Summary Metrics
    n_eval = len(evaluable_items)
    summary_metrics = {
        "experiment_id": exp_id,
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
        "average_total_latency_sec": round(sum(it["total_latency_sec"] for it in predictions) / len(predictions), 4) if predictions else 0.0,
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

    log(f"\n{'='*75}")
    log(f"EXPERIMENT COMPLETE: {exp_id}")
    log(f"  Hit@1     : {summary_metrics['document_hit_at_1']:.4f}")
    log(f"  Hit@5     : {summary_metrics['document_hit_at_5']:.4f}")
    log(f"  MRR       : {summary_metrics['mean_reciprocal_rank']:.4f}")
    log(f"  Prec@5    : {summary_metrics['average_precision_at_5']:.4f}")
    log(f"  Recall@5  : {summary_metrics['average_recall_at_5']:.4f}")
    log(f"  nDCG@5    : {summary_metrics['mean_ndcg_at_5']:.4f}")
    log(f"  Retr. Lat.: {summary_metrics['average_retrieval_latency_sec']:.4f}s")
    log(f"  Artifacts : {run_dir}")
    log(f"{'='*75}\n")

    return summary_metrics


def main():
    parser = argparse.ArgumentParser(description="Run NyayaSetu research experiment.")
    parser.add_argument("--config", required=True, help="Path to YAML experiment config")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries for smoke testing")
    parser.add_argument("--output_dir", default=None, help="Custom output directory")
    args = parser.parse_args()

    run_experiment(args.config, limit=args.limit, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
