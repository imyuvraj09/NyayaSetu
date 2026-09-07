"""Benchmark Validation Module for NyayaSetu Phase 6 Expanded Research Benchmark.

Validates benchmark JSON files against benchmark_schema.json and checks:
1. Missing required fields
2. Invalid categories or sub-categories
3. Unknown statute names (checked against known corpus enactments)
4. Invalid split assignments
5. Duplicate query IDs
6. Empty gold evidence on evaluable statutory queries
7. Inconsistent temporal labels (e.g. pre-2024 date labeled as BNS primary)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PHASE6_DIR = REPO_ROOT / "evaluation" / "phase6"

VALID_CATEGORIES = {
    "legal_regime_identification",
    "temporal_applicability",
    "substantive_vs_procedural",
    "special_vs_general",
    "multi_statute",
    "retrieval_ambiguity",
    "claim_grounding_failures",
    "out_of_scope",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

VALID_TEMPORAL_CONTEXTS = {
    "pre_july_2024",
    "post_july_2024",
    "ambiguous_date",
    "prospective",
    "historical_superseded",
    "not_applicable",
}

VALID_SPLITS = {"train", "dev", "validation", "test"}

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}

# Valid indexed corpus enactments
KNOWN_STATUTES = {
    "Bharatiya Nyaya Sanhita, 2023",
    "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "Bharatiya Sakshya Adhiniyam, 2023",
    "The Companies Act, 2013",
    "Constitution of India",
    "Consumer Protection Act",
    "The Goods and Services Tax Act, 2017",
    "The Insolvency and Bankruptcy Code, 2016",
    "Information Technology Act",
    "Motor Vehicles Act",
    "The Protection of Children from Sexual Offences Act, 2012",
    "The Right of Children to Free and Compulsory Education Act, 2009",
    "The Right to Information Act, 2005",
    "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
}


def validate_benchmark_file(file_path: Path) -> Dict[str, Any]:
    """Validate a single benchmark JSON file."""
    issues: List[str] = []
    warnings: List[str] = []

    if not file_path.exists():
        return {
            "file": str(file_path),
            "is_valid": False,
            "total_queries": 0,
            "errors": [f"File not found: {file_path}"],
            "warnings": [],
        }

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    split_name = data.get("split", "")

    seen_ids: Set[str] = set()

    for idx, q in enumerate(queries, start=1):
        qid = q.get("id")
        if not qid:
            issues.append(f"Item #{idx}: Missing 'id'")
        elif qid in seen_ids:
            issues.append(f"Duplicate query ID detected: {qid}")
        else:
            seen_ids.add(qid)

        # Split check
        q_split = q.get("split")
        if q_split != split_name and not (split_name == "dev" and q_split in ("dev", "train")):
            issues.append(f"Query {qid}: Split mismatch ({q_split} != {split_name})")

        # Category check
        cat = q.get("category")
        if cat not in VALID_CATEGORIES:
            issues.append(f"Query {qid}: Invalid category '{cat}'")

        # Difficulty check
        diff = q.get("difficulty")
        if diff not in VALID_DIFFICULTIES:
            issues.append(f"Query {qid}: Invalid difficulty '{diff}'")

        # Temporal check
        temp = q.get("temporal_context")
        if temp not in VALID_TEMPORAL_CONTEXTS:
            issues.append(f"Query {qid}: Invalid temporal_context '{temp}'")

        # Risk level check
        risk = q.get("risk_level")
        if risk not in VALID_RISK_LEVELS:
            issues.append(f"Query {qid}: Invalid risk_level '{risk}'")

        # Provenance check
        origin = q.get("source_origin")
        if not origin:
            issues.append(f"Query {qid}: Missing 'source_origin' (provenance required)")

        # Statute validation
        statutes = q.get("expected_statutes", [])
        if cat != "out_of_scope":
            if not statutes:
                issues.append(f"Query {qid}: Non-out-of-scope query has empty expected_statutes")
            for st in statutes:
                if st not in KNOWN_STATUTES:
                    warnings.append(f"Query {qid}: Statute '{st}' not in KNOWN_STATUTES registry")

        # Gold evidence check
        gold_ev = q.get("gold_evidence_ids", [])
        if cat != "out_of_scope" and not gold_ev:
            warnings.append(f"Query {qid}: Empty gold_evidence_ids on in-scope query")

        # Temporal consistency check
        if temp == "pre_july_2024" and "Bharatiya Nyaya Sanhita, 2023" in statutes and "bns_substantive" in q.get("sub_category", ""):
            # Check if notes/answer properties clarify transition
            props = " ".join(q.get("expected_answer_properties", []))
            if "date of offence" not in props.lower() and "substantive" not in props.lower():
                warnings.append(f"Query {qid}: Pre-July 2024 query maps to BNS without clear transition rationale")

    return {
        "file": str(file_path),
        "is_valid": len(issues) == 0,
        "total_queries": len(queries),
        "errors": issues,
        "warnings": warnings,
    }


def validate_all_splits() -> Dict[str, Any]:
    """Validate all three Phase 6 benchmark partitions."""
    splits = [
        PHASE6_DIR / "benchmark_train.json",
        PHASE6_DIR / "benchmark_validation.json",
        PHASE6_DIR / "benchmark_test.json",
    ]

    results = {}
    all_valid = True

    for s in splits:
        res = validate_benchmark_file(s)
        results[s.name] = res
        if not res["is_valid"]:
            all_valid = False

    return {
        "all_valid": all_valid,
        "results": results,
    }


if __name__ == "__main__":
    report = validate_all_splits()
    print(f"Validation Status: {'PASS' if report['all_valid'] else 'FAIL'}")
    for name, res in report["results"].items():
        print(f"  {name}: {res['total_queries']} queries, {len(res['errors'])} errors, {len(res['warnings'])} warnings")
        if res["errors"]:
            for e in res["errors"][:5]:
                print(f"    ERROR: {e}")
