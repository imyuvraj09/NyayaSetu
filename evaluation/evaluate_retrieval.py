"""
Dense retrieval evaluation runner for NyayaSetu Legal Assistant.

Evaluates dense semantic vector search performance across benchmark queries:
- Hit@1, Hit@3, Hit@5
- Mean Reciprocal Rank (MRR)
- Precision@5, Recall@5
- Keyword coverage in retrieved passages
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.metrics import (
    calculate_hit_at_k,
    calculate_keyword_coverage,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from retrieval.similarity_search import SimilaritySearchService
from utils.logger import setup_logging


def evaluate_dense_retrieval(
    dataset_path: str = "evaluation/test_questions.json",
    top_k: int = 5,
    limit: Optional[int] = None,
    output_path: str = "evaluation/results/retrieval_results.json",
) -> Dict[str, Any]:
    """Execute dense retrieval evaluation across benchmark questions."""
    data_file = Path(dataset_path)
    if not data_file.exists():
        raise FileNotFoundError(f"Dataset not found at {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    if limit is not None and limit > 0:
        questions = questions[:limit]

    searcher = SimilaritySearchService()
    items: List[Dict[str, Any]] = []
    durations: List[float] = []

    print(f"\n[Dense Retrieval Evaluation] Running on {len(questions)} queries (Top-K={top_k})...\n")

    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        qtext = q["question"]
        expected_doc = q.get("expected_document", "")
        expected_kws = q.get("expected_keywords", [])
        category = q.get("category", "general")

        t0 = time.perf_counter()
        result = searcher.search(qtext, top_k=top_k)
        elapsed = time.perf_counter() - t0
        durations.append(elapsed)

        retrieved_docs = [c.document_name for c in result.results]
        combined_text = " ".join(c.text for c in result.results)

        hit_1 = calculate_hit_at_k(retrieved_docs, expected_doc, 1)
        hit_3 = calculate_hit_at_k(retrieved_docs, expected_doc, 3)
        hit_5 = calculate_hit_at_k(retrieved_docs, expected_doc, 5)
        rr = calculate_reciprocal_rank(retrieved_docs, expected_doc)
        p5 = calculate_precision_at_k(retrieved_docs, expected_doc, 5)
        r5 = calculate_recall_at_k(retrieved_docs, expected_doc, 5)
        kw_cov = calculate_keyword_coverage(combined_text, expected_kws)

        items.append({
            "id": qid,
            "question": qtext,
            "category": category,
            "expected_document": expected_doc,
            "retrieved_documents": retrieved_docs,
            "hit_at_1": hit_1,
            "hit_at_3": hit_3,
            "hit_at_5": hit_5,
            "reciprocal_rank": round(rr, 4),
            "precision_at_5": round(p5, 4),
            "recall_at_5": round(r5, 4),
            "keyword_coverage": kw_cov,
            "latency_seconds": round(elapsed, 4),
            "top_chunk_id": result.results[0].chunk_id if result.results else None,
            "top_score": round(result.results[0].relevance_score, 4) if result.results else None,
        })

        tag = "HIT" if hit_5 else ("OUT_OF_SCOPE" if expected_doc == "None" else "MISS")
        print(f"  [{idx:02d}/{len(questions):02d}] {qid:<18}: {tag:<12} (RR={rr:.2f}) | {qtext[:50]}...")

    # Filter out out-of-scope / ambiguous queries for target legal metrics
    evaluable = [it for it in items if it["expected_document"] and it["expected_document"].lower() != "none"]
    n_eval = len(evaluable)

    hit1_rate = sum(1 for it in evaluable if it["hit_at_1"]) / n_eval if n_eval else 0.0
    hit3_rate = sum(1 for it in evaluable if it["hit_at_3"]) / n_eval if n_eval else 0.0
    hit5_rate = sum(1 for it in evaluable if it["hit_at_5"]) / n_eval if n_eval else 0.0
    mean_rr = sum(it["reciprocal_rank"] for it in evaluable) / n_eval if n_eval else 0.0
    avg_p5 = sum(it["precision_at_5"] for it in evaluable) / n_eval if n_eval else 0.0
    avg_kw = sum(it["keyword_coverage"] for it in evaluable) / n_eval if n_eval else 0.0
    avg_lat = sum(durations) / len(durations) if durations else 0.0

    summary = {
        "evaluation_type": "dense_semantic_retrieval",
        "total_queries": len(questions),
        "statutory_target_queries": n_eval,
        "out_of_scope_or_ambiguous_queries": len(questions) - n_eval,
        "document_hit_at_1": round(hit1_rate, 4),
        "document_hit_at_3": round(hit3_rate, 4),
        "document_hit_at_5": round(hit5_rate, 4),
        "mean_reciprocal_rank": round(mean_rr, 4),
        "average_precision_at_5": round(avg_p5, 4),
        "average_keyword_coverage": round(avg_kw, 4),
        "average_latency_seconds": round(avg_lat, 4),
    }

    report = {
        "summary": summary,
        "results": items,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("DENSE RETRIEVAL SUMMARY METRICS")
    print("=" * 80)
    print(f"  Statutory Target Queries: {n_eval}")
    print(f"  Document Hit@1          : {hit1_rate * 100:.1f}%")
    print(f"  Document Hit@3          : {hit3_rate * 100:.1f}%")
    print(f"  Document Hit@5          : {hit5_rate * 100:.1f}%")
    print(f"  Mean Reciprocal Rank    : {mean_rr:.4f}")
    print(f"  Average Precision@5     : {avg_p5:.4f}")
    print(f"  Average Keyword Coverage: {avg_kw * 100:.1f}%")
    print(f"  Average Latency         : {avg_lat:.4f}s (Development Runtime Observation)")
    print("=" * 80 + "\n")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="NyayaSetu Dense Retrieval Evaluation CLI")
    parser.add_argument("--dataset", type=str, default="evaluation/test_questions.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=str, default="evaluation/results/retrieval_results.json")
    parser.add_argument("--log-level", type=str, default="WARNING")

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    try:
        evaluate_dense_retrieval(
            dataset_path=args.dataset,
            top_k=args.top_k,
            limit=args.limit,
            output_path=args.output,
        )
    except Exception as err:
        print(f"Evaluation error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
