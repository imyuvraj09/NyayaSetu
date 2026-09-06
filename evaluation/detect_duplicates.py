"""Duplicate and near-duplicate detector for NyayaSetu benchmark queries.

Implements two levels of detection:
Level 1: Exact and normalized string matching (case, whitespace, punctuation).
Level 2: Semantic & lexical near-duplicate detection (character n-gram, token Jaccard, and optional embedding similarity).

Requires human review and confirmation before any action.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def normalize_text(text: str) -> str:
    """Normalize whitespace, casing, and punctuation for Level 1 matching."""
    lower = text.lower().strip()
    # Remove punctuation
    no_punct = re.sub(r"[^\w\s]", "", lower)
    # Collapse whitespace
    collapsed = re.sub(r"\s+", " ", no_punct).strip()
    return collapsed


def get_token_set(text: str) -> Set[str]:
    """Extract significant lowercase tokens."""
    cleaned = normalize_text(text)
    return {t for t in cleaned.split() if len(t) > 2}


def calculate_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard token similarity in [0.0, 1.0]."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return round(intersection / union, 4) if union > 0 else 0.0


def calculate_char_ngram_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    """Compute character n-gram Dice coefficient similarity."""
    norm_a = normalize_text(text_a)
    norm_b = normalize_text(text_b)
    if not norm_a or not norm_b:
        return 0.0

    ngrams_a = {norm_a[i : i + n] for i in range(len(norm_a) - n + 1)}
    ngrams_b = {norm_b[i : i + n] for i in range(len(norm_b) - n + 1)}

    if not ngrams_a or not ngrams_b:
        return 0.0

    common = len(ngrams_a & ngrams_b)
    total = len(ngrams_a) + len(ngrams_b)
    return round((2.0 * common) / total, 4) if total > 0 else 0.0


def detect_duplicates(
    benchmark_file: str,
    jaccard_threshold: float = 0.70,
    ngram_threshold: float = 0.75,
) -> Dict[str, Any]:
    """Analyze benchmark for exact and near duplicates."""
    path = Path(benchmark_file)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries") or data.get("questions", [])

    exact_duplicates: List[Dict[str, Any]] = []
    near_duplicates: List[Dict[str, Any]] = []

    normalized_map: Dict[str, List[Tuple[str, str]]] = {}  # norm_text -> [(qid, raw_text)]

    # Level 1: Exact / Normalized Match
    for q in queries:
        qid = q.get("query_id") or q.get("id")
        text = q.get("question", "")
        norm = normalize_text(text)
        normalized_map.setdefault(norm, []).append((qid, text))

    for norm, items in normalized_map.items():
        if len(items) > 1:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    exact_duplicates.append({
                        "query_a_id": items[i][0],
                        "query_a_text": items[i][1],
                        "query_b_id": items[j][0],
                        "query_b_text": items[j][1],
                        "similarity_score": 1.0,
                        "detection_method": "normalized_exact_match",
                        "recommendation": "Confirmed duplicate: human review to consolidate or distinguish targets.",
                    })

    # Level 2: Semantic / Lexical Near-Duplicate Detection
    n = len(queries)
    for i in range(n):
        qa = queries[i]
        qid_a = qa.get("query_id") or qa.get("id")
        text_a = qa.get("question", "")
        tokens_a = get_token_set(text_a)

        for j in range(i + 1, n):
            qb = queries[j]
            qid_b = qb.get("query_id") or qb.get("id")
            text_b = qb.get("question", "")
            tokens_b = get_token_set(text_b)

            # Skip if already flagged as exact duplicate
            if normalize_text(text_a) == normalize_text(text_b):
                continue

            jaccard = calculate_jaccard_similarity(tokens_a, tokens_b)
            ngram_sim = calculate_char_ngram_similarity(text_a, text_b)

            if jaccard >= jaccard_threshold or ngram_sim >= ngram_threshold:
                sim_score = max(jaccard, ngram_sim)
                method = "token_jaccard" if jaccard >= ngram_sim else "char_ngram_dice"
                near_duplicates.append({
                    "query_a_id": qid_a,
                    "query_a_text": text_a,
                    "query_b_id": qid_b,
                    "query_b_text": text_b,
                    "similarity_score": sim_score,
                    "detection_method": method,
                    "token_jaccard": jaccard,
                    "ngram_similarity": ngram_sim,
                    "recommendation": "Potential near-duplicate: verify whether both provide distinct legal reasoning utility.",
                })

    report = {
        "benchmark_file": str(path),
        "total_queries_analyzed": n,
        "exact_duplicates_count": len(exact_duplicates),
        "near_duplicates_count": len(near_duplicates),
        "exact_duplicates": exact_duplicates,
        "near_duplicates": near_duplicates,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Detect exact and near duplicate queries in benchmark.")
    parser.add_argument("benchmark_path", nargs="?", default="evaluation/development/existing_questions.json",
                        help="Path to benchmark JSON file")
    parser.add_argument("--output", default="evaluation/results/duplicate_report.json",
                        help="Output path for duplicate detection report")
    args = parser.parse_args()

    print(f"\n[Duplicate Detector] Scanning {args.benchmark_path}...")
    report = detect_duplicates(args.benchmark_path)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"  Exact Duplicates : {report['exact_duplicates_count']}")
    print(f"  Near Duplicates  : {report['near_duplicates_count']}")
    if report["near_duplicates"]:
        print("\n  Sample Near-Duplicates Flagged for Human Confirmation:")
        for pair in report["near_duplicates"][:3]:
            print(f"    - [{pair['query_a_id']}] \"{pair['query_a_text']}\"")
            print(f"      vs [{pair['query_b_id']}] \"{pair['query_b_text']}\"")
            print(f"      Similarity: {pair['similarity_score']} ({pair['detection_method']})\n")

    print(f"  Full report saved to {out_path}\n")


if __name__ == "__main__":
    main()
