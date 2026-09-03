"""
CLI Evaluation Runner for NyayaSetu RAG System.

Orchestrates:
1. Loading the 30-question legal benchmark dataset
2. Retrieval evaluation (Hit@K, MRR, keyword coverage, document distribution)
3. Generation evaluation (citation structure, grounding, source integrity)
4. Safety and failure modes battery
5. Artifact generation in evaluation/results/
6. Human-readable summary output
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.runners.generation_evaluator import GenerationEvaluator
from evaluation.runners.retrieval_evaluator import RetrievalEvaluator
from evaluation.runners.safety_evaluator import run_safety_and_failure_tests
from evaluation.schemas import (
    EvaluationSummary,
    GenerationEvaluationItem,
    RetrievalEvaluationItem,
)
from llm.provider import MockLLMProvider
from rag.rag_pipeline import LegalRAGPipeline
from utils.logger import setup_logging


def print_summary_report(summary: EvaluationSummary, safety_results: List[Dict[str, Any]]) -> None:
    """Print clean human-readable evaluation summary report to stdout."""
    print("=" * 80)
    print("NYAYASETU LEGAL RAG SYSTEM EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Benchmark Name           : {summary.benchmark_name}")
    print(f"Total Benchmark Queries  : {summary.total_queries}")
    print(f"Timestamp                : {summary.evaluation_timestamp}")
    print("-" * 80)

    print("DOCUMENT COVERAGE IN BENCHMARK:")
    for doc, cnt in sorted(summary.document_distribution.items()):
        print(f"  - {doc:<40}: {cnt} question(s)")

    print("-" * 80)
    print("RETRIEVAL EVALUATION METRICS:")
    print(f"  Retrieval Success Rate : {summary.retrieval_success_rate * 100:.1f}%")
    print(f"  Document Hit@1         : {summary.document_hit_at_1 * 100:.1f}%")
    print(f"  Document Hit@3         : {summary.document_hit_at_3 * 100:.1f}%")
    print(f"  Document Hit@5         : {summary.document_hit_at_5 * 100:.1f}%")
    print(f"  Mean Reciprocal Rank   : {summary.average_reciprocal_rank:.4f}")
    print(f"  Avg Keyword Coverage   : {summary.average_keyword_coverage * 100:.1f}%")

    if summary.generation_evaluated_count > 0:
        print("-" * 80)
        print("GENERATION & CITATION VALIDATION METRICS:")
        print(f"  Queries Evaluated      : {summary.generation_evaluated_count}")
        print(f"  Generation Success Rate: {summary.generation_success_rate * 100:.1f}%")
        print(f"  Citation Validation    : {summary.citation_validation_success_rate * 100:.1f}% passed")
        print(f"  Source Integrity       : {summary.source_integrity_success_rate * 100:.1f}% passed")

    print("-" * 80)
    print("SAFETY & FAILURE MODES BATTERY:")
    for test in safety_results:
        status_icon = "PASS [OK]" if test["passed"] else "FAIL [X]"
        print(f"  {status_icon:<10} | {test['test']:<45} | {test['detail']}")

    print("=" * 80)
    print("EVALUATION NOTICE:")
    print("  These metrics measure information retrieval behavior, metadata completeness,")
    print("  and citation syntax alignment. They do not claim or prove judicial or legal correctness.")
    print("=" * 80)


def run_evaluation(
    dataset_path: str,
    output_dir: str,
    skip_generation: bool = False,
    limit: Optional[int] = None,
) -> EvaluationSummary:
    """Execute complete evaluation suite against the specified dataset."""
    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {dataset_file}")

    with open(dataset_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    if limit is not None and limit > 0:
        questions = questions[:limit]

    total_q = len(questions)
    if total_q == 0:
        raise ValueError("No questions found in evaluation dataset.")

    retrieval_eval = RetrievalEvaluator()
    generation_eval = GenerationEvaluator(pipeline=LegalRAGPipeline(llm_provider=MockLLMProvider()))

    retrieval_items: List[RetrievalEvaluationItem] = []
    generation_items: List[GenerationEvaluationItem] = []

    print(f"\nRunning evaluation on {total_q} queries...")

    for i, item in enumerate(questions, start=1):
        # 1. Evaluate Retrieval
        r_item = retrieval_eval.evaluate_query(item, top_k=5)
        retrieval_items.append(r_item)

        hit_sym = "HIT" if r_item.hit_at_5 else "MISS"
        print(f"  [{i:02d}/{total_q:02d}] {item['id']}: {hit_sym} (RR={r_item.reciprocal_rank:.2f}, KW={r_item.keyword_coverage*100:.0f}%) | {item['question'][:65]}...")

        # 2. Evaluate Generation if enabled
        if not skip_generation:
            g_item = generation_eval.evaluate_query(item)
            generation_items.append(g_item)

    # Calculate Aggregate Retrieval Metrics
    hit1_count = sum(1 for r in retrieval_items if r.hit_at_1)
    hit3_count = sum(1 for r in retrieval_items if r.hit_at_3)
    hit5_count = sum(1 for r in retrieval_items if r.hit_at_5)
    success_count = sum(1 for r in retrieval_items if r.retrieved_chunks_count > 0)
    avg_mrr = sum(r.reciprocal_rank for r in retrieval_items) / total_q
    avg_kw = sum(r.keyword_coverage for r in retrieval_items) / total_q

    doc_counts = dict(Counter(q["expected_document"] for q in questions))
    diff_counts = dict(Counter(q.get("difficulty", "medium") for q in questions))

    # Calculate Aggregate Generation Metrics
    gen_success_rate = 0.0
    cite_val_rate = 0.0
    src_val_rate = 0.0

    if generation_items:
        gen_success_rate = sum(1 for g in generation_items if g.status in ("success", "unconfigured_llm")) / len(generation_items)
        cite_val_rate = sum(1 for g in generation_items if g.citation_validation_passed) / len(generation_items)
        src_val_rate = sum(1 for g in generation_items if g.source_integrity_passed) / len(generation_items)

    # Run Safety and Edge Case Tests
    safety_tests = run_safety_and_failure_tests()
    failed_safety = sum(1 for t in safety_tests if not t["passed"])

    summary = EvaluationSummary(
        total_queries=total_q,
        document_distribution=doc_counts,
        difficulty_distribution=diff_counts,
        retrieval_success_rate=round(success_count / total_q, 4),
        document_hit_at_1=round(hit1_count / total_q, 4),
        document_hit_at_3=round(hit3_count / total_q, 4),
        document_hit_at_5=round(hit5_count / total_q, 4),
        average_reciprocal_rank=round(avg_mrr, 4),
        average_keyword_coverage=round(avg_kw, 4),
        generation_evaluated_count=len(generation_items),
        generation_success_rate=round(gen_success_rate, 4),
        citation_validation_success_rate=round(cite_val_rate, 4),
        source_integrity_success_rate=round(src_val_rate, 4),
        total_warnings=sum(len(g.warnings) for g in generation_items),
        total_failures=failed_safety,
    )

    # Save Results to Output Directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with open(out_path / "retrieval_evaluation.json", "w", encoding="utf-8") as f:
        json.dump([item.model_dump() for item in retrieval_items], f, indent=2)

    if generation_items:
        with open(out_path / "generation_evaluation.json", "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in generation_items], f, indent=2)

    with open(out_path / "evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary.model_dump(), f, indent=2)

    # Print Summary Report
    print_summary_report(summary, safety_tests)

    print(f"\nArtifacts saved successfully to: {out_path.resolve()}\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="NyayaSetu RAG Evaluation Suite")
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/dataset/evaluation_questions.json",
        help="Path to the JSON evaluation dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="Directory to save evaluation artifacts",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Run retrieval-only evaluation without executing answer generation",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit evaluation to first N questions",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING)",
    )

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    try:
        run_evaluation(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            skip_generation=args.skip_generation,
            limit=args.limit,
        )
    except Exception as err:
        print(f"Evaluation error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
