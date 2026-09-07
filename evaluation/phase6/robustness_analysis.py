"""Robustness Analysis Module for NyayaSetu Phase 6.

Evaluates system performance stratified across 6 distinct stress dimensions:
1. Difficulty (Easy, Medium, Hard)
2. Legal Domains (Criminal Substantive, Procedural, Evidence, Cyber Law, Constitutional, Special Statutes)
3. Temporal Conditions (Pre-2024, Post-2024, Ambiguous Date)
4. Query Length (Short < 12 words, Medium 12-25 words, Long > 25 words)
5. Retrieval Ambiguity (Low, Medium, High)
6. Multi-Statute Complexity (Single Statute, Two Statutes, Three or More Statutes)

Reports detailed per-stratum metrics (Recall@5, Precision@5, MRR, nDCG@5, Grounding Score).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def classify_query_length(text: str) -> str:
    """Classify query into short, medium, long by word count."""
    wc = len(text.strip().split())
    if wc < 12:
        return "short"
    elif wc <= 25:
        return "medium"
    else:
        return "long"


def classify_domain(q: Dict[str, Any]) -> str:
    """Map expected regimes or categories to high-level legal domains."""
    regimes = q.get("legal_regimes_expected", [])
    cat = q.get("category", "")
    if "CONSTITUTION" in regimes:
        return "Constitutional Law"
    elif "IT_ACT" in regimes:
        return "Cyber Law"
    elif "BSA_EVIDENCE" in regimes:
        return "Law of Evidence"
    elif "BNSS_PROCEDURAL" in regimes:
        return "Criminal Procedural Law"
    elif "BNS_SUBSTANTIVE" in regimes:
        return "Criminal Substantive Law"
    elif any(r in ("POSH_LABOUR", "POCSO_CHILD", "CONSUMER_PROTECTION", "MOTOR_VEHICLES") for r in regimes):
        return "Special Statutes"
    elif cat == "out_of_scope":
        return "Out of Scope"
    else:
        return "General Legal Corpus"


def classify_ambiguity_level(q: Dict[str, Any]) -> str:
    """Classify retrieval ambiguity level."""
    cat = q.get("category", "")
    t_ctx = q.get("temporal_context", "")
    if cat == "retrieval_ambiguity" or t_ctx == "ambiguous_date":
        return "high_ambiguity"
    elif cat in ("special_vs_general", "multi_statute", "claim_grounding_failures"):
        return "medium_ambiguity"
    else:
        return "low_ambiguity"


def classify_multi_statute_complexity(q: Dict[str, Any]) -> str:
    """Classify by number of expected statutes."""
    st_count = len(q.get("expected_statutes", []))
    if st_count <= 1:
        return "single_statute"
    elif st_count == 2:
        return "two_statutes"
    else:
        return "three_or_more_statutes"


def run_robustness_analysis(
    benchmark_file: Path,
    predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Slice experimental predictions across all 6 robustness dimensions."""
    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    q_map = {q["id"]: q for q in queries}

    # Slices
    slices: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "difficulty": {"easy": [], "medium": [], "hard": []},
        "legal_domain": {
            "Criminal Substantive Law": [],
            "Criminal Procedural Law": [],
            "Law of Evidence": [],
            "Cyber Law": [],
            "Constitutional Law": [],
            "Special Statutes": [],
            "General Legal Corpus": [],
            "Out of Scope": [],
        },
        "temporal_condition": {
            "pre_july_2024": [],
            "post_july_2024": [],
            "ambiguous_date": [],
            "not_applicable": [],
        },
        "query_length": {"short": [], "medium": [], "long": []},
        "retrieval_ambiguity": {"low_ambiguity": [], "medium_ambiguity": [], "high_ambiguity": []},
        "multi_statute_complexity": {"single_statute": [], "two_statutes": [], "three_or_more_statutes": []},
    }

    for pred in predictions:
        qid = pred.get("id") or pred.get("query_id")
        q = q_map.get(qid)
        if not q:
            continue

        diff = q.get("difficulty", "medium")
        slices["difficulty"].setdefault(diff, []).append(pred)

        dom = classify_domain(q)
        slices["legal_domain"].setdefault(dom, []).append(pred)

        temp = q.get("temporal_context", "not_applicable")
        slices["temporal_condition"].setdefault(temp, []).append(pred)

        ql = classify_query_length(q.get("question", ""))
        slices["query_length"].setdefault(ql, []).append(pred)

        amb = classify_ambiguity_level(q)
        slices["retrieval_ambiguity"].setdefault(amb, []).append(pred)

        msc = classify_multi_statute_complexity(q)
        slices["multi_statute_complexity"].setdefault(msc, []).append(pred)

    def aggregate_slice_metrics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not items:
            return {"sample_size": 0}
        n = len(items)
        r1 = [it.get("recall_at_1", it.get("hit_at_1", 0.0)) for it in items]
        r5 = [it.get("recall_at_5", it.get("hit_at_5", 0.0)) for it in items]
        p5 = [it.get("precision_at_5", 0.0) for it in items]
        mrr = [it.get("mrr", it.get("reciprocal_rank", 0.0)) for it in items]
        ndcg5 = [it.get("ndcg_at_5", 0.0) for it in items]
        lat = [it.get("latency_sec", 0.0) for it in items]

        return {
            "sample_size": n,
            "recall_at_1": round(float(np.mean(r1)), 4),
            "recall_at_5": round(float(np.mean(r5)), 4),
            "precision_at_5": round(float(np.mean(p5)), 4),
            "mrr": round(float(np.mean(mrr)), 4),
            "ndcg_at_5": round(float(np.mean(ndcg5)), 4),
            "mean_latency_sec": round(float(np.mean(lat)), 4),
        }

    robustness_report = {}
    for dim_name, strata in slices.items():
        robustness_report[dim_name] = {}
        for stratum_name, items in strata.items():
            robustness_report[dim_name][stratum_name] = aggregate_slice_metrics(items)

    return robustness_report
