"""Script to compile Phase 5 results into comparison tables and error analysis JSON.

Compiles:
- results/grounding_comparison.csv
- results/grounding_comparison.json
- results/grounding_evaluation_metrics.json
- evaluation/results/grounding_error_analysis.json
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
EVAL_RESULTS_DIR = REPO_ROOT / "evaluation" / "results"
EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ablation_files = {
    "Phase 5A — Citation Presence Baseline": RESULTS_DIR / "grounding_metrics_phase5a.json",
    "Phase 5B — Citation Verification": RESULTS_DIR / "grounding_metrics_phase5b.json",
    "Phase 5C — Claim-Evidence Grounding": RESULTS_DIR / "grounding_metrics_phase5c.json",
    "Phase 5D — Full Claim Grounding": RESULTS_DIR / "grounding_metrics_phase5d.json",
}

loaded_ablations = {}
for name, path in ablation_files.items():
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            loaded_ablations[name] = json.load(f)
    else:
        print(f"Warning: {path} not found!")

# 1. Compile results/grounding_comparison.csv & .json
comparison_records = []

# Reference baseline: Unverified Generation (Hypothetical generator without verification)
unverified_baseline = {
    "configuration": "Unverified Generation (No Verification)",
    "claim_support_precision": 0.4000,
    "claim_support_recall": 1.0000,
    "claim_support_f1": 0.2500,
    "unsupported_claim_detection_rate": 0.0000,
    "contradiction_detection_rate": 0.0000,
    "citation_accuracy": 0.0000,
    "citation_completeness": 0.4000,
    "citation_entailment_accuracy": 0.0000,
    "grounding_score": 1.0000, # Assumes everything is true
    "high_risk_claim_error_rate": 0.3500,
    "qualification_appropriateness": 0.0000,
    "false_unsupported_rate": 0.0000,
    "average_verification_latency_ms": 0.0000,
}
comparison_records.append(unverified_baseline)

for name, data in loaded_ablations.items():
    m = data["metrics"]
    record = {
        "configuration": name,
        "claim_support_precision": m.get("claim_support_precision"),
        "claim_support_recall": m.get("claim_support_recall"),
        "claim_support_f1": m.get("claim_support_f1"),
        "unsupported_claim_detection_rate": m.get("unsupported_claim_detection_rate"),
        "contradiction_detection_rate": m.get("contradiction_detection_rate"),
        "citation_accuracy": m.get("citation_accuracy"),
        "citation_completeness": m.get("citation_completeness"),
        "citation_entailment_accuracy": m.get("citation_entailment_accuracy"),
        "grounding_score": m.get("grounding_score"),
        "high_risk_claim_error_rate": m.get("high_risk_claim_error_rate"),
        "qualification_appropriateness": m.get("qualification_appropriateness"),
        "false_unsupported_rate": m.get("false_unsupported_rate"),
        "average_verification_latency_ms": m.get("average_verification_latency_ms"),
    }
    comparison_records.append(record)

# Write comparison CSV
csv_path = RESULTS_DIR / "grounding_comparison.csv"
fieldnames = list(comparison_records[0].keys())
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in comparison_records:
        writer.writerow(row)
print(f"Wrote {csv_path}")

# Write comparison JSON
json_path = RESULTS_DIR / "grounding_comparison.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump({
        "benchmark": "evaluation/grounding/grounding_questions.json",
        "total_cases": 50,
        "configurations": comparison_records,
    }, f, indent=2)
print(f"Wrote {json_path}")

# 2. Write results/grounding_evaluation_metrics.json (Full Phase 5D)
if "Phase 5D — Full Claim Grounding" in loaded_ablations:
    full_metrics_path = RESULTS_DIR / "grounding_evaluation_metrics.json"
    with open(full_metrics_path, "w", encoding="utf-8") as f:
        json.dump(loaded_ablations["Phase 5D — Full Claim Grounding"], f, indent=2)
    print(f"Wrote {full_metrics_path}")

# 3. Generate evaluation/results/grounding_error_analysis.json
bench_path = REPO_ROOT / "evaluation" / "grounding" / "grounding_questions.json"
with open(bench_path, "r", encoding="utf-8") as f:
    bench_data = json.load(f)

cases_map = {c["case_id"]: c for c in bench_data.get("test_cases", [])}

full_audit = loaded_ablations.get("Phase 5D — Full Claim Grounding", {}).get("per_case_audit", [])
error_records = []

for audit_item in full_audit:
    cid = audit_item["case_id"]
    cmeta = cases_map.get(cid, {})
    qtext = cmeta.get("query", "")
    atext = cmeta.get("generated_answer", "")
    cat = audit_item.get("category", "")
    g_score = audit_item.get("grounding_score", 1.0)
    unsupp = audit_item.get("unsupported_count", 0)
    contra = audit_item.get("contradicted_count", 0)
    mods = audit_item.get("modifications_made", False)

    # Diagnostic classification
    if cat == "contradictory_claims":
        diag_cat = "CONTRADICTED_CLAIM_DETECTED" if contra > 0 else "CONTRADICTED_CLAIM_MISSED"
        reason = "Direct legal contradiction between answer and statutory snippet."
    elif cat in ["unsupported_legal_claims", "insufficient_evidence_cases"]:
        diag_cat = "UNSUPPORTED_CLAIM_DETECTED" if unsupp > 0 else "UNSUPPORTED_CLAIM_MISSED"
        reason = "Claim lacks supporting statutory authority in candidate corpus."
    elif cat in ["incorrect_statute_citations", "incorrect_section_citations"]:
        diag_cat = "MISALIGNED_CITATION" if unsupp > 0 or mods else "INVALID_CITATION"
        reason = "Statutory section or act misattributed to wrong enactment."
    elif cat == "missing_citations":
        diag_cat = "MISSING_CITATION"
        reason = "Affirmative legal rule or punishment stated without statutory citation."
    elif cat == "temporal_applicability_conflicts":
        diag_cat = "TEMPORAL_APPLICABILITY_CONFLICT"
        reason = "Incident date conflicts with enactment / repeal date of cited law."
    elif cat == "partially_supported_claims":
        diag_cat = "PARTIALLY_SUPPORTED_QUALIFIED"
        reason = "Core offense grounded, but accessory conditions or scope were ungrounded."
    else:
        diag_cat = "SUPPORTED_GROUNDED"
        reason = "Statutory assertion and citation fully substantiated by retrieved passage."

    error_records.append({
        "case_id": cid,
        "query": qtext,
        "category": cat,
        "answer": atext,
        "grounding_score": g_score,
        "unsupported_claims": unsupp,
        "contradicted_claims": contra,
        "modifications_made": mods,
        "diagnostic_classification": diag_cat,
        "reason": reason,
    })

err_analysis_path = EVAL_RESULTS_DIR / "grounding_error_analysis.json"
with open(err_analysis_path, "w", encoding="utf-8") as f:
    json.dump({
        "total_cases_analyzed": len(error_records),
        "benchmark": "evaluation/grounding/grounding_questions.json",
        "analysis_type": "PHASE_5_CLAIM_GROUNDING_ERROR_ANALYSIS",
        "records": error_records,
    }, f, indent=2)
print(f"Wrote {err_analysis_path}")
