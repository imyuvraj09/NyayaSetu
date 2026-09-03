"""
Reranking evaluation module for NyayaSetu Legal Assistant.

Compares retrieval quality before and after CrossEncoder reranking:
- Measures whether reranking improves or degrades expected document ranks
- Evaluates Hit@1, Hit@3, and MRR before vs. after reranking
- Quantifies queries improved, unchanged, and degraded
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from retrieval.advanced_retriever import AdvancedRetriever
from utils.logger import setup_logging


def evaluate_reranking(
    dataset_path: str = "evaluation/test_questions.json",
    initial_k: int = 20,
    final_k: int = 5,
    limit: Optional[int] = None,
    output_path: str = "evaluation/results/reranking_results.json",
) -> Dict[str, Any]:
    """Compare dense retrieval against two-stage cross-encoder reranked retrieval."""
    data_file = Path(dataset_path)
    if not data_file.exists():
        raise FileNotFoundError(f"Dataset not found at {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    if limit is not None and limit > 0:
        questions = questions[:limit]

    retriever = AdvancedRetriever(initial_k=initial_k, final_k=final_k)

    results: List[Dict[str, Any]] = []
    improved_count = 0
    unchanged_count = 0
    degraded_count = 0

    dense_rrs: List[float] = []
    rerank_rrs: List[float] = []
    dense_hit1s: List[bool] = []
    rerank_hit1s: List[bool] = []
    dense_hit3s: List[bool] = []
    rerank_hit3s: List[bool] = []

    print(f"\n[Reranking Comparison Evaluation] Evaluating {len(questions)} queries...")
    print(f"  Stage 1 (Dense): Top-{initial_k} -> Filtering -> Stage 2 (CrossEncoder): Top-{final_k}\n")

    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        qtext = q["question"]
        expected_doc = q.get("expected_document", "")

        t0 = time.perf_counter()
        adv_res = retriever.retrieve(qtext, initial_k=initial_k, final_k=final_k)
        t_total = time.perf_counter() - t0

        dense_top_docs = [c.document_name for c in adv_res.initial_results[:final_k]]
        dense_first_rank = 0
        for r_idx, doc in enumerate(dense_top_docs, 1):
            if expected_doc and expected_doc.lower() in doc.lower():
                dense_first_rank = r_idx
                break

        reranked_docs = [c.document_name for c in adv_res.results]
        reranked_first_rank = 0
        for r_idx, doc in enumerate(reranked_docs, 1):
            if expected_doc and expected_doc.lower() in doc.lower():
                reranked_first_rank = r_idx
                break

        # Analyze Rank Change
        is_statutory = bool(expected_doc and expected_doc.lower() != "none")

        if not is_statutory:
            change = "out_of_scope"
        elif dense_first_rank == 0 and reranked_first_rank > 0:
            change = "improved"
            improved_count += 1
        elif dense_first_rank > 0 and reranked_first_rank == 0:
            change = "degraded"
            degraded_count += 1
        elif reranked_first_rank > 0 and reranked_first_rank < dense_first_rank:
            change = "improved"
            improved_count += 1
        elif reranked_first_rank > 0 and reranked_first_rank > dense_first_rank:
            change = "degraded"
            degraded_count += 1
        else:
            change = "unchanged"
            unchanged_count += 1

        if is_statutory:
            d_rr = 1.0 / dense_first_rank if dense_first_rank > 0 else 0.0
            r_rr = 1.0 / reranked_first_rank if reranked_first_rank > 0 else 0.0
            dense_rrs.append(d_rr)
            rerank_rrs.append(r_rr)
            dense_hit1s.append(dense_first_rank == 1)
            rerank_hit1s.append(reranked_first_rank == 1)
            dense_hit3s.append(0 < dense_first_rank <= 3)
            rerank_hit3s.append(0 < reranked_first_rank <= 3)

        results.append({
            "id": qid,
            "question": qtext,
            "expected_document": expected_doc,
            "dense_top_document": dense_top_docs[0] if dense_top_docs else None,
            "dense_rank": dense_first_rank if dense_first_rank > 0 else None,
            "reranked_top_document": reranked_docs[0] if reranked_docs else None,
            "reranked_rank": reranked_first_rank if reranked_first_rank > 0 else None,
            "rank_change": change,
            "top_reranker_score": round(adv_res.results[0].reranker_score, 4) if adv_res.results else None,
            "duration_seconds": round(t_total, 4),
        })

        tag = change.upper()
        print(f"  [{idx:02d}/{len(questions):02d}] {qid:<18}: {tag:<10} (Dense Rank: {dense_first_rank} -> Reranked: {reranked_first_rank})")

    n_eval = len(dense_rrs)
    summary = {
        "evaluation_type": "cross_encoder_reranking_comparison",
        "total_statutory_queries": n_eval,
        "queries_improved": improved_count,
        "queries_unchanged": unchanged_count,
        "queries_degraded": degraded_count,
        "dense_hit_at_1": round(sum(dense_hit1s) / n_eval, 4) if n_eval else 0.0,
        "reranked_hit_at_1": round(sum(rerank_hit1s) / n_eval, 4) if n_eval else 0.0,
        "dense_hit_at_3": round(sum(dense_hit3s) / n_eval, 4) if n_eval else 0.0,
        "reranked_hit_at_3": round(sum(rerank_hit3s) / n_eval, 4) if n_eval else 0.0,
        "dense_mrr": round(sum(dense_rrs) / n_eval, 4) if n_eval else 0.0,
        "reranked_mrr": round(sum(rerank_rrs) / n_eval, 4) if n_eval else 0.0,
        "mrr_delta": round((sum(rerank_rrs) - sum(dense_rrs)) / n_eval, 4) if n_eval else 0.0,
    }

    report = {
        "summary": summary,
        "results": results,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("RERANKING IMPACT COMPARISON SUMMARY")
    print("=" * 80)
    print(f"  Queries Improved        : {improved_count} ({improved_count / n_eval * 100:.1f}%)" if n_eval else "")
    print(f"  Queries Unchanged       : {unchanged_count} ({unchanged_count / n_eval * 100:.1f}%)" if n_eval else "")
    print(f"  Queries Degraded        : {degraded_count} ({degraded_count / n_eval * 100:.1f}%)" if n_eval else "")
    print(f"  Hit@1 (Before -> After) : {summary['dense_hit_at_1'] * 100:.1f}% -> {summary['reranked_hit_at_1'] * 100:.1f}%")
    print(f"  Hit@3 (Before -> After) : {summary['dense_hit_at_3'] * 100:.1f}% -> {summary['reranked_hit_at_3'] * 100:.1f}%")
    print(f"  MRR   (Before -> After) : {summary['dense_mrr']:.4f} -> {summary['reranked_mrr']:.4f} (Delta: {summary['mrr_delta']:+.4f})")
    print("=" * 80 + "\n")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="NyayaSetu Reranking Comparison Evaluation CLI")
    parser.add_argument("--dataset", type=str, default="evaluation/test_questions.json")
    parser.add_argument("--initial-k", type=int, default=20)
    parser.add_argument("--final-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=str, default="evaluation/results/reranking_results.json")
    parser.add_argument("--log-level", type=str, default="WARNING")

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    try:
        evaluate_reranking(
            dataset_path=args.dataset,
            initial_k=args.initial_k,
            final_k=args.final_k,
            limit=args.limit,
            output_path=args.output,
        )
    except Exception as err:
        print(f"Evaluation error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
