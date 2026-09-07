"""Data Integrity and Leakage Detection Suite for NyayaSetu Phase 6.

Performs exhaustive audit checks:
1. Exact and normalized duplicate query detection across and within splits.
2. Near-duplicate detection (token Jaccard >= 0.70, char 3-gram Dice >= 0.75).
3. Cross-split data leakage (Dev <-> Validation, Dev <-> Test, Validation <-> Test).
4. Provenance audit (verifying source_origin for 100% of benchmark items).
5. Synthetic benchmark contamination analysis (identifying rule derivation risks).
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PHASE6_DIR = REPO_ROOT / "evaluation" / "phase6"


def normalize_query_text(text: str) -> str:
    """Normalize casing, whitespace, and punctuation."""
    lower = text.lower().strip()
    no_punct = re.sub(r"[^\w\s]", "", lower)
    return re.sub(r"\s+", " ", no_punct).strip()


def get_token_set(text: str) -> Set[str]:
    """Tokenize into significant lowercase words."""
    norm = normalize_query_text(text)
    return {t for t in norm.split() if len(t) > 2}


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity coefficient."""
    if not set_a or not set_b:
        return 0.0
    return round(len(set_a & set_b) / len(set_a | set_b), 4)


def char_ngram_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    """Compute character n-gram Dice similarity coefficient."""
    norm_a = normalize_query_text(text_a)
    norm_b = normalize_query_text(text_b)
    if not norm_a or not norm_b:
        return 0.0

    ngrams_a = {norm_a[i : i + n] for i in range(len(norm_a) - n + 1)}
    ngrams_b = {norm_b[i : i + n] for i in range(len(norm_b) - n + 1)}
    if not ngrams_a or not ngrams_b:
        return 0.0

    common = len(ngrams_a & ngrams_b)
    total = len(ngrams_a) + len(ngrams_b)
    return round((2.0 * common) / total, 4) if total > 0 else 0.0


def check_data_integrity(
    train_file: Path = PHASE6_DIR / "benchmark_train.json",
    val_file: Path = PHASE6_DIR / "benchmark_validation.json",
    test_file: Path = PHASE6_DIR / "benchmark_test.json",
    jaccard_threshold: float = 0.70,
    ngram_threshold: float = 0.75,
) -> Dict[str, Any]:
    """Execute complete data integrity audit."""
    partitions = {}
    with open(train_file, "r", encoding="utf-8") as f:
        partitions["train"] = json.load(f).get("queries", [])
    with open(val_file, "r", encoding="utf-8") as f:
        partitions["validation"] = json.load(f).get("queries", [])
    with open(test_file, "r", encoding="utf-8") as f:
        partitions["test"] = json.load(f).get("queries", [])

    all_queries: List[Tuple[str, Dict[str, Any]]] = []
    for split_name, q_list in partitions.items():
        for q in q_list:
            all_queries.append((split_name, q))

    total_queries = len(all_queries)

    # 1. Intra-split and Inter-split Duplicates
    exact_duplicates: List[Dict[str, Any]] = []
    near_duplicates: List[Dict[str, Any]] = []
    split_leakages: List[Dict[str, Any]] = []

    normalized_text_map: Dict[str, List[Tuple[str, str, str]]] = {}  # norm_text -> [(split, qid, text)]
    seen_ids: Dict[str, str] = {}  # qid -> split

    id_collisions: List[Dict[str, Any]] = []

    for split_name, q in all_queries:
        qid = q["id"]
        text = q["question"]
        norm = normalize_query_text(text)

        # Check ID collision
        if qid in seen_ids:
            id_collisions.append({
                "query_id": qid,
                "split_1": seen_ids[qid],
                "split_2": split_name,
            })
        else:
            seen_ids[qid] = split_name

        normalized_text_map.setdefault(norm, []).append((split_name, qid, text))

    # Identify exact duplicates and cross-split leakages
    for norm, entries in normalized_text_map.items():
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    sp_i, qid_i, text_i = entries[i]
                    sp_j, qid_j, text_j = entries[j]
                    rec = {
                        "query_a": {"id": qid_i, "split": sp_i, "text": text_i},
                        "query_b": {"id": qid_j, "split": sp_j, "text": text_j},
                        "type": "exact_match",
                    }
                    exact_duplicates.append(rec)
                    if sp_i != sp_j:
                        split_leakages.append({
                            **rec,
                            "severity": "CONFIRMED_CROSS_SPLIT_LEAKAGE",
                        })

    # 2. Near-duplicate scanning across splits
    n = len(all_queries)
    for i in range(n):
        split_i, q_i = all_queries[i]
        tokens_i = get_token_set(q_i["question"])
        for j in range(i + 1, n):
            split_j, q_j = all_queries[j]
            # If same split and already detected as exact duplicate, continue
            if normalize_query_text(q_i["question"]) == normalize_query_text(q_j["question"]):
                continue

            tokens_j = get_token_set(q_j["question"])
            jacc = jaccard_similarity(tokens_i, tokens_j)
            ngram_sim = char_ngram_similarity(q_i["question"], q_j["question"])

            if jacc >= jaccard_threshold or ngram_sim >= ngram_threshold:
                rec = {
                    "query_a": {"id": q_i["id"], "split": split_i, "text": q_i["question"]},
                    "query_b": {"id": q_j["id"], "split": split_j, "text": q_j["question"]},
                    "jaccard_similarity": jacc,
                    "char_ngram_similarity": ngram_sim,
                    "is_cross_split": split_i != split_j,
                }
                near_duplicates.append(rec)
                if split_i != split_j and jacc >= 0.85:
                    split_leakages.append({
                        **rec,
                        "severity": "HIGH_SIMILARITY_CROSS_SPLIT_NEAR_DUPLICATE",
                    })

    # 3. Provenance Audit
    missing_provenance: List[str] = []
    for split_name, q in all_queries:
        if not q.get("source_origin"):
            missing_provenance.append(q["id"])

    # 4. Synthetic Rule Contamination Analysis
    # Check if any questions derive directly from rule string constants
    rule_patterns = ["BNS_SUBSTANTIVE", "BNSS_PROCEDURAL", "BSA_EVIDENCE", "IT_ACT"]
    rule_token_hits: List[Dict[str, Any]] = []
    for split_name, q in all_queries:
        for rp in rule_patterns:
            if rp in q["question"]:
                rule_token_hits.append({"id": q["id"], "token": rp})

    is_clean = len(split_leakages) == 0 and len(id_collisions) == 0 and len(missing_provenance) == 0

    return {
        "total_queries_audited": total_queries,
        "is_data_clean": is_clean,
        "id_collisions_count": len(id_collisions),
        "id_collisions": id_collisions,
        "exact_duplicates_count": len(exact_duplicates),
        "exact_duplicates": exact_duplicates,
        "cross_split_leakage_count": len(split_leakages),
        "cross_split_leakages": split_leakages,
        "near_duplicates_count": len(near_duplicates),
        "near_duplicates_sample": near_duplicates[:10],
        "missing_provenance_count": len(missing_provenance),
        "missing_provenance_ids": missing_provenance,
        "rule_token_leakage_count": len(rule_token_hits),
        "rule_token_leakages": rule_token_hits,
    }


if __name__ == "__main__":
    report = check_data_integrity()
    print("=" * 60)
    print("NYAYASETU PHASE 6 DATA INTEGRITY AUDIT REPORT")
    print("=" * 60)
    print(f"Total Queries Audited: {report['total_queries_audited']}")
    print(f"Data Clean Status    : {'CLEAN / PASS' if report['is_data_clean'] else 'FAILED'}")
    print(f"ID Collisions        : {report['id_collisions_count']}")
    print(f"Cross-Split Leakages : {report['cross_split_leakage_count']}")
    print(f"Missing Provenance   : {report['missing_provenance_count']}")
    print(f"Exact Duplicates     : {report['exact_duplicates_count']}")
    print(f"Near Duplicates      : {report['near_duplicates_count']}")
    print(f"Rule Token Leaks     : {report['rule_token_leakage_count']}")
    print("=" * 60)
