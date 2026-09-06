"""Benchmark partition leakage detector for NyayaSetu.

Analyzes cross-split data leakage across:
- Development <-> Validation
- Development <-> Test
- Validation <-> Test

Differentiates:
1. CONFIRMED LEAKAGE: Exact query text match or duplicate query_id across splits.
2. POSSIBLE LEAKAGE: High lexical/token similarity (near-duplicates) across splits.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def normalize_text(text: str) -> str:
    lower = text.lower().strip()
    no_punct = re.sub(r"[^\w\s]", "", lower)
    return re.sub(r"\s+", " ", no_punct).strip()


def get_token_set(text: str) -> Set[str]:
    cleaned = normalize_text(text)
    return {t for t in cleaned.split() if len(t) > 2}


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def load_partition(file_path: Path) -> List[Dict[str, Any]]:
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("queries") or data.get("questions", [])
    except Exception:
        return []


def check_split_pair(
    name_a: str,
    queries_a: List[Dict[str, Any]],
    name_b: str,
    queries_b: List[Dict[str, Any]],
    near_dup_threshold: float = 0.75,
) -> Dict[str, Any]:
    """Compare two partitions for confirmed and possible leakage."""
    confirmed_leakage: List[Dict[str, Any]] = []
    possible_leakage: List[Dict[str, Any]] = []

    # Map query_ids
    ids_a = {q.get("query_id") or q.get("id"): q for q in queries_a if (q.get("query_id") or q.get("id"))}
    ids_b = {q.get("query_id") or q.get("id"): q for q in queries_b if (q.get("query_id") or q.get("id"))}

    common_ids = set(ids_a.keys()) & set(ids_b.keys())
    for cid in common_ids:
        confirmed_leakage.append({
            "type": "DUPLICATE_QUERY_ID",
            "query_id": cid,
            "split_a": name_a,
            "split_b": name_b,
            "text_a": ids_a[cid].get("question"),
            "text_b": ids_b[cid].get("question"),
            "severity": "CONFIRMED LEAKAGE",
        })

    # Exact and near query text check
    for qa in queries_a:
        qid_a = qa.get("query_id") or qa.get("id")
        text_a = qa.get("question", "")
        norm_a = normalize_text(text_a)
        tokens_a = get_token_set(text_a)

        for qb in queries_b:
            qid_b = qb.get("query_id") or qb.get("id")
            text_b = qb.get("question", "")
            norm_b = normalize_text(text_b)
            tokens_b = get_token_set(text_b)

            if norm_a == norm_b:
                if qid_a != qid_b or qid_a not in common_ids:
                    confirmed_leakage.append({
                        "type": "EXACT_QUERY_TEXT_MATCH",
                        "query_id_a": qid_a,
                        "query_id_b": qid_b,
                        "split_a": name_a,
                        "split_b": name_b,
                        "text": text_a,
                        "severity": "CONFIRMED LEAKAGE",
                    })
            else:
                sim = jaccard_similarity(tokens_a, tokens_b)
                if sim >= near_dup_threshold:
                    possible_leakage.append({
                        "type": "NEAR_DUPLICATE_TEXT",
                        "query_id_a": qid_a,
                        "query_id_b": qid_b,
                        "split_a": name_a,
                        "split_b": name_b,
                        "similarity_score": round(sim, 4),
                        "text_a": text_a,
                        "text_b": text_b,
                        "severity": "POSSIBLE LEAKAGE",
                    })

    return {
        "comparison": f"{name_a} <-> {name_b}",
        "confirmed_leakage_count": len(confirmed_leakage),
        "possible_leakage_count": len(possible_leakage),
        "confirmed_leakage": confirmed_leakage,
        "possible_leakage": possible_leakage,
    }


def detect_all_leakage(
    dev_path: str = "evaluation/development/existing_questions.json",
    val_path: str = "evaluation/validation/validation_questions.json",
    test_path: str = "evaluation/test/test_questions.json",
) -> Dict[str, Any]:
    """Run pairwise leakage verification across all available splits."""
    dev_queries = load_partition(Path(dev_path))
    val_queries = load_partition(Path(val_path))
    test_queries = load_partition(Path(test_path))

    comparisons = []
    comparisons.append(check_split_pair("Development", dev_queries, "Validation", val_queries))
    comparisons.append(check_split_pair("Development", dev_queries, "Test", test_queries))
    comparisons.append(check_split_pair("Validation", val_queries, "Test", test_queries))

    total_confirmed = sum(c["confirmed_leakage_count"] for c in comparisons)
    total_possible = sum(c["possible_leakage_count"] for c in comparisons)

    return {
        "summary": {
            "total_confirmed_leakage": total_confirmed,
            "total_possible_leakage": total_possible,
            "dev_queries_count": len(dev_queries),
            "val_queries_count": len(val_queries),
            "test_queries_count": len(test_queries),
            "status": "PASS (0 Confirmed Leakage)" if total_confirmed == 0 else "FAIL (Leakage Detected)",
        },
        "comparisons": comparisons,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify zero cross-split leakage across benchmark partitions.")
    parser.add_argument("--dev", default="evaluation/development/existing_questions.json")
    parser.add_argument("--val", default="evaluation/validation/validation_questions.json")
    parser.add_argument("--test", default="evaluation/test/test_questions.json")
    parser.add_argument("--output", default="evaluation/results/leakage_report.json")
    args = parser.parse_args()

    print("\n[Leakage Detector] Analyzing cross-split overlap...")
    report = detect_all_leakage(dev_path=args.dev, val_path=args.val, test_path=args.test)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    summary = report["summary"]
    print(f"  Development Queries : {summary['dev_queries_count']}")
    print(f"  Validation Queries  : {summary['val_queries_count']}")
    print(f"  Test Queries        : {summary['test_queries_count']}")
    print(f"  Confirmed Leakage   : {summary['total_confirmed_leakage']}")
    print(f"  Possible Leakage    : {summary['total_possible_leakage']}")
    print(f"  Overall Status      : {summary['status']}")
    print(f"  Report saved to     : {out_path}\n")


if __name__ == "__main__":
    main()
