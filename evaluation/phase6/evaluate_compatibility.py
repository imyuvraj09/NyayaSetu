"""Evidence Compatibility Evaluation Module for NyayaSetu Phase 6.

Evaluates Evidence Compatibility Filtering (Phase 4):
1. Compatibility Precision (P_compat)
2. Compatibility Recall (R_compat)
3. Compatibility F1 (F1_compat)
4. Incompatible Evidence Rejection Rate (IRR)
5. False Rejection Rate (FRR)
6. Regime Coherence (RC)
7. Multi-Statute Coverage (MSC)
8. Temporal Compatibility Accuracy (TCA)
9. Mean Rank Improvement (ΔRank)
10. Compatibility Latency Profile (Mean, Median, P95, P99, StdDev)
11. 95% Bootstrap Confidence Intervals (B=10,000)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.phase6.statistical_tests import compute_bootstrap_ci_10k
from research.evidence_compatibility.engine import EvidenceCompatibilityEngine, get_evidence_compatibility_engine
from research.evidence_compatibility.models import CompatibilityStatus, LegalRole, TemporalStatus
from research.issue_router import FactFirstRouter, get_fact_first_router
from retrieval.bm25_search import get_bm25_engine
from retrieval.similarity_search import SimilaritySearchService
from schemas.retrieval import RetrievedChunk


def evaluate_compatibility_split(
    benchmark_file: Path,
    engine: Optional[EvidenceCompatibilityEngine] = None,
    router: Optional[FactFirstRouter] = None,
    sim_service: Optional[SimilaritySearchService] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Run evidence compatibility evaluation across a benchmark partition."""
    if engine is None:
        engine = get_evidence_compatibility_engine()
    if router is None:
        router = get_fact_first_router()
    if sim_service is None:
        sim_service = SimilaritySearchService()

    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    bm25_engine = get_bm25_engine()
    bm25_engine.build_index()

    latencies: List[float] = []
    p_compat_list: List[float] = []
    r_compat_list: List[float] = []
    f1_compat_list: List[float] = []
    delta_rank_list: List[float] = []
    regime_coherence_list: List[float] = []

    incompatible_penalized = 0
    incompatible_total = 0
    false_rejections = 0
    true_compatibles_total = 0

    temporal_correct = 0
    temporal_evaluable = 0

    multi_statute_covered = 0
    multi_statute_total = 0

    per_query_audit: List[Dict[str, Any]] = []

    for q in queries:
        qid = q["id"]
        qtext = q["question"]
        expected_statutes = q.get("expected_statutes", [])
        expected_temporal = q.get("temporal_context", "not_applicable")
        is_multi = len(expected_statutes) > 1

        # Step 1: Route query
        routing_decision = router.route_query(qtext)

        # Step 2: Dense + Lexical Candidate Retrieval
        dense_cands = sim_service.search(qtext, top_k=20).results
        bm25_res = bm25_engine.search(qtext, top_k=20)
        bm25_cands = [
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
            for c, sc in bm25_res
        ]

        from experiments.run_experiment import reciprocal_rank_fusion
        base_candidates = reciprocal_rank_fusion([dense_cands, bm25_cands], top_k=20)

        # Record baseline rank of target document
        baseline_rank = None
        for r_idx, c in enumerate(base_candidates, start=1):
            if any(st.lower() in (c.document_name or "").lower() for st in expected_statutes):
                baseline_rank = r_idx
                break

        # Step 3: Run Compatibility Engine
        t0 = time.perf_counter()
        facts = routing_decision.normalized_facts.raw_facts if routing_decision and routing_decision.normalized_facts else None
        filtered_cands, comp_res = engine.filter_and_rank_candidates(
            query=qtext,
            candidates=base_candidates,
            routing_decision=routing_decision,
            facts=facts,
            top_k=top_k,
        )
        lat = time.perf_counter() - t0
        latencies.append(lat)

        # Post-filter rank of target document
        post_rank = None
        for r_idx, c in enumerate(filtered_cands, start=1):
            if any(st.lower() in (c.document_name or "").lower() for st in expected_statutes):
                post_rank = r_idx
                break

        # Rank delta (positive = improvement)
        b_r = baseline_rank if baseline_rank is not None else 21
        p_r = post_rank if post_rank is not None else 21
        delta_rank = float(b_r - p_r)
        delta_rank_list.append(delta_rank)

        # Compatibility Precision, Recall, F1 for top-K
        retrieved_top = filtered_cands[:top_k]
        compat_in_top = sum(
            1 for c in retrieved_top
            if any(st.lower() in (c.document_name or "").lower() for st in expected_statutes)
        )
        p_comp = compat_in_top / len(retrieved_top) if retrieved_top else 0.0
        r_comp = min(1.0, compat_in_top / max(1, len(expected_statutes)))
        f1_comp = (2.0 * p_comp * r_comp) / (p_comp + r_comp) if (p_comp + r_comp) > 0 else 0.0

        p_compat_list.append(p_comp)
        r_compat_list.append(r_comp)
        f1_compat_list.append(f1_comp)
        regime_coherence_list.append(comp_res.regime_coherence_score)

        # Incompatible Rejection Rate & False Rejection Rate from audit decisions
        for dec in comp_res.decisions:
            doc_name = dec.document_name or ""
            is_truth_target = any(st.lower() in doc_name.lower() for st in expected_statutes)
            if not is_truth_target:
                incompatible_total += 1
                if dec.compatibility_status in (CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.PARTIALLY_COMPATIBLE):
                    incompatible_penalized += 1
            else:
                true_compatibles_total += 1
                if dec.compatibility_status == CompatibilityStatus.INCOMPATIBLE:
                    false_rejections += 1

        # Temporal accuracy
        if expected_temporal in ("pre_july_2024", "post_july_2024"):
            temporal_evaluable += 1
            has_temp_match = False
            for dec in comp_res.decisions:
                doc_l = (dec.document_name or "").lower()
                if expected_temporal == "pre_july_2024" and any(k in doc_l for k in ["ipc", "crpc", "evidence"]):
                    if dec.temporal_status in (TemporalStatus.APPLICABLE, TemporalStatus.SUPERSEDED):
                        has_temp_match = True
                        break
                elif expected_temporal == "post_july_2024" and any(k in doc_l for k in ["bns", "bnss", "bsa"]):
                    if dec.temporal_status == TemporalStatus.APPLICABLE:
                        has_temp_match = True
                        break
            if has_temp_match:
                temporal_correct += 1

        # Multi-statute coverage
        if is_multi:
            multi_statute_total += 1
            ret_statutes = {c.document_name for c in retrieved_top}
            if all(any(st.lower() in (rs or "").lower() for rs in ret_statutes) for st in expected_statutes):
                multi_statute_covered += 1

        per_query_audit.append({
            "id": qid,
            "baseline_rank": baseline_rank,
            "post_rank": post_rank,
            "delta_rank": delta_rank,
            "p_compat": round(p_comp, 4),
            "r_compat": round(r_comp, 4),
            "f1_compat": round(f1_comp, 4),
            "coherence_score": round(comp_res.regime_coherence_score, 4),
            "temporal_status": comp_res.decisions[0].temporal_status.value if comp_res.decisions else "UNKNOWN",
            "latency_sec": round(lat, 6),
        })

    # Aggregations & CIs
    irr = (incompatible_penalized / incompatible_total) if incompatible_total > 0 else 1.0
    frr = (false_rejections / true_compatibles_total) if true_compatibles_total > 0 else 0.0
    tca = (temporal_correct / temporal_evaluable) if temporal_evaluable > 0 else 1.0
    msc = (multi_statute_covered / multi_statute_total) if multi_statute_total > 0 else 1.0

    p_ci = compute_bootstrap_ci_10k(p_compat_list, "compatibility_precision").to_dict()
    r_ci = compute_bootstrap_ci_10k(r_compat_list, "compatibility_recall").to_dict()
    f1_ci = compute_bootstrap_ci_10k(f1_compat_list, "compatibility_f1").to_dict()
    dr_ci = compute_bootstrap_ci_10k(delta_rank_list, "rank_improvement").to_dict()

    lat_arr = np.asarray(latencies, dtype=np.float64)
    latency_profile = {
        "mean_latency_sec": round(float(np.mean(lat_arr)), 6),
        "median_latency_sec": round(float(np.median(lat_arr)), 6),
        "p95_latency_sec": round(float(np.percentile(lat_arr, 95)), 6),
        "p99_latency_sec": round(float(np.percentile(lat_arr, 99)), 6),
        "std_latency_sec": round(float(np.std(lat_arr, ddof=1)), 6),
    }

    return {
        "benchmark_file": str(benchmark_file),
        "total_queries": len(queries),
        "compatibility_precision": round(float(np.mean(p_compat_list)), 4),
        "compatibility_precision_ci": p_ci,
        "compatibility_recall": round(float(np.mean(r_compat_list)), 4),
        "compatibility_recall_ci": r_ci,
        "compatibility_f1": round(float(np.mean(f1_compat_list)), 4),
        "compatibility_f1_ci": f1_ci,
        "incompatible_rejection_rate": round(irr, 4),
        "false_rejection_rate": round(frr, 4),
        "mean_rank_improvement": round(float(np.mean(delta_rank_list)), 4),
        "mean_rank_improvement_ci": dr_ci,
        "regime_coherence": round(float(np.mean(regime_coherence_list)), 4),
        "temporal_compatibility_accuracy": round(tca, 4),
        "multi_statute_coverage": round(msc, 4),
        "latency_profile": latency_profile,
        "per_query_audit": per_query_audit,
        "raw_vectors": {
            "p_compat": p_compat_list,
            "r_compat": r_compat_list,
            "f1_compat": f1_compat_list,
            "delta_rank": delta_rank_list,
        },
    }
