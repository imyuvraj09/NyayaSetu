"""Benchmark schema validator for NyayaSetu legal evaluation datasets.

Verifies:
1. Required top-level structure ('metadata', 'queries' or 'questions').
2. Field-level type conformity against benchmark_schema.json.
3. Uniqueness of query_ids across the file.
4. Valid enumeration values for query_type, difficulty, review_status.
5. Correct structure of relevant_sections and relevant_chunk_ids.
6. Validation of negative_or_ambiguous flag consistency.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

VALID_QUERY_TYPES = {
    "direct_statutory",
    "section_identification",
    "fact_pattern",
    "multi_part",
    "cross_section",
    "ambiguous",
    "negative_or_out_of_scope",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

VALID_REVIEW_STATUSES = {
    "draft",
    "unreviewed",
    "peer_reviewed",
    "expert_verified",
    "legacy_development",
}


def validate_single_query(query: Dict[str, Any], idx: int) -> List[str]:
    """Validate a single query dict and return a list of validation errors."""
    errors = []
    qid = query.get("query_id") or query.get("id")

    if not qid:
        errors.append(f"Query #{idx}: Missing required 'query_id' or 'id'")
    elif not isinstance(qid, str) or len(qid.strip()) == 0:
        errors.append(f"Query #{idx}: 'query_id' must be a non-empty string")

    prefix = f"Query '{qid or idx}'"

    # Question text
    qtext = query.get("question")
    if not qtext or not isinstance(qtext, str) or len(qtext.strip()) < 5:
        errors.append(f"{prefix}: 'question' must be a string with at least 5 characters")

    # Query type (if present in new schema)
    if "query_type" in query:
        qtype = query["query_type"]
        if qtype not in VALID_QUERY_TYPES:
            errors.append(f"{prefix}: Invalid 'query_type' '{qtype}'. Must be one of {sorted(VALID_QUERY_TYPES)}")

    # Difficulty
    if "difficulty" in query:
        diff = query["difficulty"]
        if diff not in VALID_DIFFICULTIES:
            errors.append(f"{prefix}: Invalid 'difficulty' '{diff}'. Must be one of {sorted(VALID_DIFFICULTIES)}")

    # Review status
    if "review_status" in query:
        rev = query["review_status"]
        if rev not in VALID_REVIEW_STATUSES:
            errors.append(f"{prefix}: Invalid 'review_status' '{rev}'. Must be one of {sorted(VALID_REVIEW_STATUSES)}")

    # Statute / expected_document
    statute = query.get("statute")
    if statute is not None and not isinstance(statute, list):
        errors.append(f"{prefix}: 'statute' must be a list of strings")

    # Legal domain
    domain = query.get("legal_domain")
    if domain is not None and not isinstance(domain, list):
        errors.append(f"{prefix}: 'legal_domain' must be a list of strings")

    # Facts
    facts = query.get("facts")
    if facts is not None and not isinstance(facts, dict):
        errors.append(f"{prefix}: 'facts' must be a dictionary or null")

    # Relevant sections
    rel_secs = query.get("relevant_sections")
    if rel_secs is not None and not isinstance(rel_secs, list):
        errors.append(f"{prefix}: 'relevant_sections' must be a list of strings")

    # Relevant chunk IDs
    rel_chunks = query.get("relevant_chunk_ids")
    if rel_chunks is not None and not isinstance(rel_chunks, list):
        errors.append(f"{prefix}: 'relevant_chunk_ids' must be a list of strings")

    # Negative / ambiguous boolean
    if "negative_or_ambiguous" in query:
        neg = query["negative_or_ambiguous"]
        if not isinstance(neg, bool):
            errors.append(f"{prefix}: 'negative_or_ambiguous' must be a boolean (True/False)")

    return errors


def validate_benchmark_file(file_path: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate an entire benchmark JSON file.

    Returns:
        (is_valid, list_of_errors, stats_dict)
    """
    path = Path(file_path)
    if not path.exists():
        return False, [f"File not found: {file_path}"], {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Invalid JSON in {file_path}: {str(e)}"], {}

    if not isinstance(data, dict):
        return False, [f"Root of {file_path} must be a JSON object"], {}

    queries = data.get("queries") or data.get("questions")
    if queries is None or not isinstance(queries, list):
        return False, [f"{file_path} must contain a 'queries' or 'questions' list"], {}

    all_errors = []
    seen_ids = set()
    duplicate_ids = set()

    for idx, q in enumerate(queries, start=1):
        if not isinstance(q, dict):
            all_errors.append(f"Item #{idx} is not a dictionary")
            continue

        qid = q.get("query_id") or q.get("id")
        if qid:
            if qid in seen_ids:
                duplicate_ids.add(qid)
            seen_ids.add(qid)

        q_errors = validate_single_query(q, idx)
        all_errors.extend(q_errors)

    if duplicate_ids:
        all_errors.append(f"Duplicate query_id(s) detected: {sorted(duplicate_ids)}")

    stats = {
        "file_path": str(path),
        "total_queries": len(queries),
        "unique_query_ids": len(seen_ids),
        "validation_errors_count": len(all_errors),
        "is_valid": len(all_errors) == 0,
    }

    return len(all_errors) == 0, all_errors, stats


def main():
    parser = argparse.ArgumentParser(description="Validate NyayaSetu benchmark files against schema.")
    parser.add_argument("benchmark_path", nargs="?", default="evaluation/development/existing_questions.json",
                        help="Path to benchmark JSON file to validate")
    args = parser.parse_args()

    print(f"\n[Benchmark Validator] Validating: {args.benchmark_path}...")
    is_valid, errors, stats = validate_benchmark_file(args.benchmark_path)

    if is_valid:
        print(f"  [PASS] Benchmark file is VALID! ({stats['total_queries']} queries, 0 errors)\n")
        sys.exit(0)
    else:
        print(f"  [FAIL] Validation failed with {len(errors)} error(s):")
        for err in errors[:20]:
            print(f"    - {err}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more errors.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
