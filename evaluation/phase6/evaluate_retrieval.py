"""Retrieval Evaluation Module for NyayaSetu Phase 6.

Evaluates all primary retrieval metrics across candidate configurations:
- Recall@1, Recall@3, Recall@5, Recall@10
- Precision@1, Precision@5
- Mean Reciprocal Rank (MRR)
- nDCG@5, nDCG@10
- Keyword Coverage
- Retrieval Latency profiling (Mean, Median, P95, P99, StdDev)

Integrates B=10,000 bootstrap confidence intervals.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.metrics import (
    calculate_hit_at_k,
    calculate_keyword_coverage,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from evaluation.phase6.statistical_tests import compute_bootstrap_ci_10k
from retrieval.bm25_search import get_bm25_engine
from retrieval.similarity_search import SimilaritySearchService
from schemas.retrieval import RetrievedChunk


def evaluate_retrieval_split(
    benchmark_file: Path,
    mode: str = "dense",  # "dense", "hybrid", "hybrid_rrf", "routing_hybrid_rrf", "full_compatibility"
    top_k: int = 10,
    router: Any = None,
    compat_engine: Any = None,
) -> Dict[str, Any]:
    """Evaluate retrieval on a benchmark split."""
    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    sim_service = SimilaritySearchService()
    bm25_engine = get_bm25_engine() if "hybrid" in mode else None
    if bm25_engine:
        bm25_engine.build_index()

    # Pre-load routing if mode requires it
    if "routing" in mode and router is None:
        from research.issue_router import get_fact_first_router
        router = get_fact_first_router()

    if "compatibility" in mode and compat_engine is None:
        from research.evidence_compatibility.engine import get_evidence_compatibility_engine
        compat_engine = get_evidence_compatibility_engine()

    latencies: List[float] = []
    r1_list: List[float] = []
    r3_list: List[float] = []
    r5_list: List[float] = []
    r10_list: List[float] = []
    p1_list: List[float] = []
    p5_list: List[float] = []
    mrr_list: List[float] = []
    ndcg5_list: List[float] = []
    ndcg10_list: List[float] = []
    kw_cov_list: List[float] = []

    per_query_results: List[Dict[str, Any]] = []

    for q in queries:
        qid = q["id"]
        qtext = q["question"]
        exp_statutes = q.get("expected_statutes", [])
        is_oos = q.get("category") == "out_of_scope"

        t0 = time.perf_counter()

        routing_boosts = None
        routing_decision = None
        if "routing" in mode and router:
            routing_decision = router.route_query(qtext)
            if not routing_decision.fallback_used and routing_decision.selected_regimes:
                routing_boosts = {}
                reg_cfg = router.config.get("regimes", {})
                for reg_id in routing_decision.selected_regimes:
                    reg_info = reg_cfg.get(reg_id, {})
                    for df in reg_info.get("document_filter", []):
                        routing_boosts[df] = 1.35

        # Dense retrieval
        s_res = sim_service.search(qtext, top_k=20)
        dense_cands = s_res.results

        # BM25 retrieval if hybrid
        bm25_cands = []
        if "hybrid" in mode and bm25_engine:
            b_res = bm25_engine.search(qtext, top_k=20)
            for chunk, score in b_res:
                bm25_cands.append(
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

        # Fusion
        if mode == "dense":
            candidates = dense_cands
        elif mode == "hybrid":
            # Simple interleaving
            candidates = []
            seen = set()
            for d, b in zip(dense_cands, bm25_cands):
                if d.chunk_id not in seen:
                    seen.add(d.chunk_id)
                    candidates.append(d)
                if b.chunk_id not in seen:
                    seen.add(b.chunk_id)
                    candidates.append(b)
        else:
            # Reciprocal rank fusion
            from experiments.run_experiment import reciprocal_rank_fusion
            candidates = reciprocal_rank_fusion(
                [dense_cands, bm25_cands],
                k_const=60,
                top_k=20,
                routing_boosts=routing_boosts,
            )

        # Evidence compatibility filtering if required
        if "compatibility" in mode and compat_engine:
            facts = routing_decision.normalized_facts.raw_facts if routing_decision and routing_decision.normalized_facts else None
            candidates, _ = compat_engine.filter_and_rank_candidates(
                query=qtext,
                candidates=candidates,
                routing_decision=routing_decision,
                facts=facts,
                top_k=top_k,
            )

        retrieved_top_k = candidates[:top_k]
        lat = time.perf_counter() - t0
        latencies.append(lat)

        retrieved_docs = [c.document_name for c in retrieved_top_k]
        combined_text = " ".join(c.text for c in retrieved_top_k)

        if not is_oos and exp_statutes:
            r1 = calculate_recall_at_k(retrieved_docs, exp_statutes, 1, partial_match=True)
            r3 = calculate_recall_at_k(retrieved_docs, exp_statutes, 3, partial_match=True)
            r5 = calculate_recall_at_k(retrieved_docs, exp_statutes, 5, partial_match=True)
            r10 = calculate_recall_at_k(retrieved_docs, exp_statutes, 10, partial_match=True)
            p1 = calculate_precision_at_k(retrieved_docs, exp_statutes, 1, partial_match=True)
            p5 = calculate_precision_at_k(retrieved_docs, exp_statutes, 5, partial_match=True)
            rr = calculate_reciprocal_rank(retrieved_docs, exp_statutes, partial_match=True)
            ndcg5 = calculate_ndcg_at_k(retrieved_docs, exp_statutes, 5)
            ndcg10 = calculate_ndcg_at_k(retrieved_docs, exp_statutes, 10)
            kw = calculate_keyword_coverage(combined_text, q.get("expected_sections", []))

            r1_list.append(r1)
            r3_list.append(r3)
            r5_list.append(r5)
            r10_list.append(r10)
            p1_list.append(p1)
            p5_list.append(p5)
            mrr_list.append(rr)
            ndcg5_list.append(ndcg5)
            ndcg10_list.append(ndcg10)
            kw_cov_list.append(kw)

            per_query_results.append({
                "id": qid,
                "question": qtext,
                "category": q.get("category"),
                "difficulty": q.get("difficulty"),
                "expected_statutes": exp_statutes,
                "retrieved_documents": retrieved_docs[:5],
                "recall_at_1": r1,
                "recall_at_3": r3,
                "recall_at_5": r5,
                "recall_at_10": r10,
                "precision_at_1": p1,
                "precision_at_5": p5,
                "mrr": rr,
                "ndcg_at_5": ndcg5,
                "ndcg_at_10": ndcg10,
                "latency_sec": round(lat, 4),
            })
        else:
            # Out of scope query
            per_query_results.append({
                "id": qid,
                "question": qtext,
                "category": "out_of_scope",
                "is_out_of_scope": True,
                "retrieved_documents": retrieved_docs[:3],
                "latency_sec": round(lat, 4),
            })

    # Summary metrics and 10k bootstrap CIs
    cis = {
        "recall_at_1": compute_bootstrap_ci_10k(r1_list, "Recall@1").to_dict(),
        "recall_at_3": compute_bootstrap_ci_10k(r3_list, "Recall@3").to_dict(),
        "recall_at_5": compute_bootstrap_ci_10k(r5_list, "Recall@5").to_dict(),
        "recall_at_10": compute_bootstrap_ci_10k(r10_list, "Recall@10").to_dict(),
        "precision_at_1": compute_bootstrap_ci_10k(p1_list, "Precision@1").to_dict(),
        "precision_at_5": compute_bootstrap_ci_10k(p5_list, "Precision@5").to_dict(),
        "mrr": compute_bootstrap_ci_10k(mrr_list, "MRR").to_dict(),
        "ndcg_at_5": compute_bootstrap_ci_10k(ndcg5_list, "nDCG@5").to_dict(),
        "ndcg_at_10": compute_bootstrap_ci_10k(ndcg10_list, "nDCG@10").to_dict(),
    }

    lat_arr = np.asarray(latencies, dtype=np.float64)
    latency_profile = {
        "mean_latency_sec": round(float(np.mean(lat_arr)), 4),
        "median_latency_sec": round(float(np.median(lat_arr)), 4),
        "p95_latency_sec": round(float(np.percentile(lat_arr, 95)), 4),
        "p99_latency_sec": round(float(np.percentile(lat_arr, 99)), 4),
        "std_latency_sec": round(float(np.std(lat_arr, ddof=1)), 4),
    }

    return {
        "mode": mode,
        "benchmark_file": str(benchmark_file),
        "total_queries": len(queries),
        "evaluable_queries": len(r1_list),
        "out_of_scope_queries": len(queries) - len(r1_list),
        "bootstrap_cis": cis,
        "latency_profile": latency_profile,
        "per_query_results": per_query_results,
        "raw_vectors": {
            "recall_at_1": r1_list,
            "recall_at_5": r5_list,
            "recall_at_10": r10_list,
            "precision_at_5": p5_list,
            "mrr": mrr_list,
            "ndcg_at_5": ndcg5_list,
            "ndcg_at_10": ndcg10_list,
        },
    }
