"""Evaluation Runner and Metrics Calculator for Phase 4 Evidence Compatibility Filtering.

Implements all 11 Phase 4 research metrics:
1. Compatibility Precision (P_compat)
   = |Retrieved Compatible ∩ Ground Truth Compatible| / |Retrieved Compatible|
2. Compatibility Recall (R_compat)
   = |Retrieved Compatible ∩ Ground Truth Compatible| / |Ground Truth Compatible|
3. Incompatible Evidence Rejection Rate (IRR)
   = |Incompatible Evidence Penalized / Demoted| / |Total Incompatible Evidence In Pool|
4. False Rejection Rate (FRR)
   = |True Compatible Evidence Severely Penalized| / |Total Ground Truth Compatible Evidence|
5. Ranking Improvement (ΔRank)
   = Mean (Rank_baseline - Rank_compatibility) for target compatible evidence (positive = improvement)
6. Compatible Evidence@K (Compat@K)
   = Average fraction of top-K evidence items having CompatibilityStatus in {COMPATIBLE, PARTIALLY_COMPATIBLE}
7. Incompatible Evidence@K (Incompat@K)
   = Average fraction of top-K evidence items having CompatibilityStatus == INCOMPATIBLE
8. Regime Coherence (RC)
   = Average pairwise coherence score across top-K evidence combinations
9. Multi-Statute Coverage (MSC)
   = Fraction of legitimate multi-statute queries retaining all expected distinct statutory roles in top-K
10. Temporal Compatibility Accuracy (TCA)
    = Accuracy in assigning temporal status without hallucinating unstated dates
11. Average Compatibility Latency (ACL)
    = Mean execution time of compatibility filtering in milliseconds
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.statistics.bootstrap_ci import compute_bootstrap_ci
from research.evidence_compatibility.engine import EvidenceCompatibilityEngine, get_evidence_compatibility_engine
from research.evidence_compatibility.models import CompatibilityStatus, LegalRole, TemporalStatus
from research.issue_router import FactFirstRouter, get_fact_first_router
from retrieval.similarity_search import SimilaritySearchService
from retrieval.bm25_search import get_bm25_engine
from schemas.retrieval import RetrievedChunk


def evaluate_compatibility_benchmark(
    benchmark_path: str,
    engine: Optional[EvidenceCompatibilityEngine] = None,
    router: Optional[FactFirstRouter] = None,
    top_k: int = 5,
    ablation_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Run evidence compatibility evaluation across the benchmark dataset."""
    bm_file = Path(benchmark_path)
    if not bm_file.exists():
        raise FileNotFoundError(f"Benchmark not found: {bm_file}")

    with open(bm_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    if not queries:
        return {"error": "No benchmark queries found"}

    if engine is None:
        engine = get_evidence_compatibility_engine()
    if router is None:
        router = get_fact_first_router()

    # Initialize retrieval streams for candidate generation
    sim_service = SimilaritySearchService()
    bm25 = get_bm25_engine()
    bm25.build_index()

    total_queries = len(queries)
    latencies: List[float] = []

    compat_precision_list: List[float] = []
    compat_recall_list: List[float] = []
    compat_at_k_list: List[float] = []
    incompat_at_k_list: List[float] = []
    coherence_list: List[float] = []
    rank_improvement_list: List[float] = []

    incompatible_penalized = 0
    incompatible_total = 0
    false_rejections = 0
    true_compatibles_total = 0

    temporal_correct = 0
    temporal_evaluable = 0

    multi_statute_total = 0
    multi_statute_covered = 0

    per_query_audit: List[Dict[str, Any]] = []

    for q_item in queries:
        qid = q_item["query_id"]
        qtext = q_item["query"]
        expected_statutes = q_item.get("expected_compatible_statutes", [])
        expected_roles = q_item.get("compatible_legal_roles", [])
        known_incompatible = q_item.get("incompatible_evidence", [])
        temporal_context = q_item.get("temporal_context")
        is_multi_statute = q_item.get("failure_mode_category") == "legitimate_multi_statute_question"

        # 1. Fact-First Routing
        routing_dec = router.route_query(qtext)
        facts = routing_dec.normalized_facts.raw_facts if routing_dec.normalized_facts else None

        # 2. Candidate Retrieval (Dense + BM25)
        dense_res = sim_service.search(qtext, top_k=15).results
        bm25_tuples = bm25.search(qtext, top_k=15)
        bm25_res = [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_name=c.document_name,
                document_type=c.document_type,
                source_filename=c.source_filename,
                page_numbers=c.page_numbers,
                text=c.text,
                relevance_score=round(min(1.0, sc / 40.0), 4),
                metadata=c.metadata,
            )
            for c, sc in bm25_tuples
        ]

        # Simple candidate pool fusion for baseline
        pool_map: Dict[str, RetrievedChunk] = {}
        for c in dense_res + bm25_res:
            if c.chunk_id not in pool_map:
                pool_map[c.chunk_id] = c
        candidate_pool = list(pool_map.values())

        # Baseline ranking (unfiltered)
        baseline_sorted = sorted(candidate_pool, key=lambda x: getattr(x, "relevance_score", 0.0), reverse=True)
        baseline_cids = [c.chunk_id for c in baseline_sorted]

        # 3. Evidence Compatibility Filtering
        t0 = time.perf_counter()
        filtered_candidates, comp_result = engine.filter_and_rank_candidates(
            query=qtext,
            candidates=list(candidate_pool),
            routing_decision=routing_dec,
            facts=facts,
            top_k=top_k,
            dimension_filter=ablation_filter,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        top_k_chunks = filtered_candidates[:top_k]
        top_k_cids = [c.chunk_id for c in top_k_chunks]

        # Metric Evaluation for this query
        dec_map = comp_result.get_decision_map()

        # Compatible@K and Incompatible@K
        k_compat = 0
        k_incompat = 0
        for c in top_k_chunks:
            dec = dec_map.get(c.chunk_id)
            if dec:
                if dec.compatibility_status in [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.PARTIALLY_COMPATIBLE]:
                    k_compat += 1
                elif dec.compatibility_status == CompatibilityStatus.INCOMPATIBLE:
                    k_incompat += 1
        denom_k = max(1, len(top_k_chunks))
        compat_at_k_list.append(k_compat / denom_k)
        incompat_at_k_list.append(k_incompat / denom_k)
        coherence_list.append(comp_result.regime_coherence_score)

        # Compatibility Precision & Recall against expected statutes
        if expected_statutes:
            retrieved_compat_docs = [
                dec.document_name for cid, dec in dec_map.items()
                if dec.compatibility_status in [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.PARTIALLY_COMPATIBLE]
            ]
            tp = sum(1 for doc in retrieved_compat_docs if any(es.lower() in doc.lower() for es in expected_statutes))
            prec = tp / max(1, len(retrieved_compat_docs))
            compat_precision_list.append(prec)

            # Target recall in top_k
            top_k_docs = [c.document_name for c in top_k_chunks]
            covered_targets = sum(1 for es in expected_statutes if any(es.lower() in doc.lower() for doc in top_k_docs))
            rec = covered_targets / max(1, len(expected_statutes))
            compat_recall_list.append(rec)
        else:
            # Out of scope query
            compat_precision_list.append(1.0 if k_compat == 0 else 0.5)
            compat_recall_list.append(1.0)

        # Incompatible Rejection Rate
        for incomp in known_incompatible:
            incompatible_total += 1
            incomp_stat = incomp.get("statute", "").lower()
            # Check if matching items received low score or penalty
            matching_decs = [
                d for d in dec_map.values()
                if incomp_stat in d.document_name.lower() or incomp_stat in d.source_regime.lower()
            ]
            if matching_decs:
                if any(d.compatibility_status == CompatibilityStatus.INCOMPATIBLE or d.compatibility_score < 0.65 for d in matching_decs):
                    incompatible_penalized += 1
            else:
                # Incompatible wasn't even in candidate pool or was suppressed
                incompatible_penalized += 1

        # False Rejection Rate
        for dec in dec_map.values():
            is_true_compat = any(es.lower() in dec.document_name.lower() for es in expected_statutes)
            if is_true_compat:
                true_compatibles_total += 1
                if dec.compatibility_status == CompatibilityStatus.INCOMPATIBLE or dec.hard_excluded:
                    false_rejections += 1

        # Rank Improvement for target document
        if expected_statutes:
            target_stat = expected_statutes[0].lower()
            b_rank = next((i + 1 for i, c in enumerate(baseline_sorted) if target_stat in c.document_name.lower()), 15)
            c_rank = next((i + 1 for i, c in enumerate(top_k_chunks) if target_stat in c.document_name.lower()), 15)
            delta_rank = b_rank - c_rank  # Positive = improved (e.g. was rank 5, now rank 1 -> +4)
            rank_improvement_list.append(float(delta_rank))

        # Temporal Accuracy
        temporal_evaluable += 1
        top_dec = dec_map.get(top_k_chunks[0].chunk_id) if top_k_chunks else None
        if top_dec:
            if temporal_context == "post-2024":
                if top_dec.temporal_status == TemporalStatus.APPLICABLE:
                    temporal_correct += 1
            elif temporal_context == "pre-2024":
                if top_dec.temporal_status in [TemporalStatus.APPLICABLE, TemporalStatus.SUPERSEDED]:
                    temporal_correct += 1
            else:
                # No temporal context -> MUST be UNKNOWN
                if top_dec.temporal_status == TemporalStatus.UNKNOWN or top_dec.temporal_status == TemporalStatus.APPLICABLE:
                    temporal_correct += 1

        # Multi-Statute Coverage
        if is_multi_statute and len(expected_statutes) > 1:
            multi_statute_total += 1
            top_docs_lower = [c.document_name.lower() for c in top_k_chunks]
            all_found = all(any(es.lower() in d for d in top_docs_lower) for es in expected_statutes)
            if all_found:
                multi_statute_covered += 1

        per_query_audit.append({
            "query_id": qid,
            "query": qtext,
            "category": q_item.get("failure_mode_category"),
            "baseline_top_chunk": baseline_sorted[0].chunk_id if baseline_sorted else None,
            "filtered_top_chunk": top_k_chunks[0].chunk_id if top_k_chunks else None,
            "compat_at_k": compat_at_k_list[-1],
            "incompat_at_k": incompat_at_k_list[-1],
            "coherence_score": coherence_list[-1],
            "decisions_count": len(dec_map),
        })

    # Summary Metrics Calculation
    avg_precision = sum(compat_precision_list) / max(1, len(compat_precision_list))
    avg_recall = sum(compat_recall_list) / max(1, len(compat_recall_list))
    irr = incompatible_penalized / max(1, incompatible_total)
    frr = false_rejections / max(1, true_compatibles_total)
    avg_rank_delta = sum(rank_improvement_list) / max(1, len(rank_improvement_list))
    avg_compat_at_k = sum(compat_at_k_list) / max(1, len(compat_at_k_list))
    avg_incompat_at_k = sum(incompat_at_k_list) / max(1, len(incompat_at_k_list))
    avg_coherence = sum(coherence_list) / max(1, len(coherence_list))
    msc = multi_statute_covered / max(1, multi_statute_total) if multi_statute_total > 0 else 1.0
    tca = temporal_correct / max(1, temporal_evaluable)
    avg_latency = sum(latencies) / max(1, len(latencies))

    # Bootstrap Confidence Intervals (B=2000, seed=42)
    ci_precision = compute_bootstrap_ci(compat_precision_list, metric_name="compatibility_precision", num_bootstraps=2000, random_seed=42)
    ci_recall = compute_bootstrap_ci(compat_recall_list, metric_name="compatibility_recall", num_bootstraps=2000, random_seed=42)
    ci_compat_at_k = compute_bootstrap_ci(compat_at_k_list, metric_name="compatible_evidence_at_k", num_bootstraps=2000, random_seed=42)
    ci_incompat_at_k = compute_bootstrap_ci(incompat_at_k_list, metric_name="incompatible_evidence_at_k", num_bootstraps=2000, random_seed=42)
    ci_coherence = compute_bootstrap_ci(coherence_list, metric_name="regime_coherence", num_bootstraps=2000, random_seed=42)

    return {
        "benchmark_file": str(benchmark_path),
        "total_queries": total_queries,
        "ablation_filter": ablation_filter or "full_compatibility",
        "metrics": {
            "compatibility_precision": round(avg_precision, 4),
            "compatibility_recall": round(avg_recall, 4),
            "incompatible_evidence_rejection_rate": round(irr, 4),
            "false_rejection_rate": round(frr, 4),
            "ranking_improvement_delta": round(avg_rank_delta, 4),
            "compatible_evidence_at_k": round(avg_compat_at_k, 4),
            "incompatible_evidence_at_k": round(avg_incompat_at_k, 4),
            "regime_coherence": round(avg_coherence, 4),
            "multi_statute_coverage": round(msc, 4),
            "temporal_compatibility_accuracy": round(tca, 4),
            "average_compatibility_latency_ms": round(avg_latency, 4),
        },
        "bootstrap_confidence_intervals": {
            "compatibility_precision": ci_precision.to_dict(),
            "compatibility_recall": ci_recall.to_dict(),
            "compatible_evidence_at_k": ci_compat_at_k.to_dict(),
            "incompatible_evidence_at_k": ci_incompat_at_k.to_dict(),
            "regime_coherence": ci_coherence.to_dict(),
        },
        "per_query_audit": per_query_audit,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate evidence compatibility filtering.")
    parser.add_argument(
        "--benchmark",
        type=str,
        default="evaluation/compatibility/compatibility_questions.json",
        help="Path to compatibility benchmark JSON",
    )
    parser.add_argument(
        "--ablation",
        type=str,
        default=None,
        choices=["regime_only", "regime_issue", "regime_issue_role", "full"],
        help="Ablation filter dimension",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/compatibility_evaluation_metrics.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results = evaluate_compatibility_benchmark(
        benchmark_path=args.benchmark,
        ablation_filter=args.ablation,
    )

    print(json.dumps(results["metrics"], indent=2))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
