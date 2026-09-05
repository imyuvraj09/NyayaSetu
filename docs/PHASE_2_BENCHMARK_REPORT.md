# Phase 2 — Benchmark Integrity and Audit Report

**Date**: September 6, 2026  
**Repository Branch**: `research-v2`  
**Evaluation Target**: NyayaSetu Legal Information Retrieval & Question Answering Platform  
**Benchmark Artifact**: `evaluation/development/existing_questions.json` (Migrated from legacy `evaluation/test_questions.json`)  
**Validation Status**: PASSED (43 queries, 0 errors against `evaluation/benchmark_schema.json`)

---

## 1. Executive Summary

This report establishes the integrity, taxonomy, schema compliance, and statistical limitations of the development benchmark dataset for NyayaSetu. In compliance with Phase 2 requirements, the existing 43 queries have been preserved as a **Development / Legacy Benchmark** rather than prematurely claimed as an independently validated research test split.

Integrity tools developed and executed:
1. `evaluation/benchmark_schema.json`: Formal JSON Schema with typed query metadata.
2. `evaluation/validate_benchmark.py`: Automated schema and constraint validation.
3. `evaluation/detect_duplicates.py`: Exact and fuzzy n-gram duplicate detection.
4. `evaluation/detect_leakage.py`: Cross-split leakage detector between dev, val, and test partitions.
5. `evaluation/analyze_coverage.py`: Multi-dimensional distribution and taxonomy analyzer.

---

## 2. Benchmark Audit (14 Mandatory Inspection Points)

| Audit Point | Finding | Notes & Implications |
| :--- | :--- | :--- |
| **1. Exact Number of Questions** | **43** | Sufficient for initial development baselines; statistically insufficient for final publication claims without confidence intervals or expanded test benchmarks. |
| **2. Existing Fields** | `id`, `question`, `expected_document`, `expected_keywords`, `category` | Preserved identically in `evaluation/development/existing_questions.json` with added schema-conforming fields. |
| **3. Legal Statutes Covered** | **7 Major Acts** | Constitution of India (6), Bharatiya Nyaya Sanhita 2023 (6), Bharatiya Nagarik Suraksha Sanhita 2023 (6), Bharatiya Sakshya Adhiniyam 2023 (6), Consumer Protection Act 2019 (5), Information Technology Act 2000 (5), Motor Vehicles Act 1988 (5). |
| **4. Legal Domains Covered** | **7 Domains** | Constitutional Law (13.95%), Criminal Law (13.95%), Criminal Procedure (13.95%), Law of Evidence (13.95%), Consumer Protection (11.63%), Cyber Law (11.63%), Motor Vehicles Law (11.63%), Plus General/Out-of-scope (9.30%). |
| **5. Direct Statutory Questions** | **31 (72.09%)** | Dominant question type. Inquiries asking for explicit statutory provisions, definitions, or punishments. |
| **6. Section Identification Questions** | **4 (9.30%)** | Questions asking which section covers a specific doctrine (e.g., snatching, theft, anticipatory bail). |
| **7. Fact-Pattern Questions** | **2 (4.65%)** | Scenario-based inquiries (e.g., defective product redressal, zero FIR procedure). Critically underrepresented. |
| **8. Multi-Part Questions** | **2 (4.65%)** | Inquiries requiring conjunction of multiple statutory sections or facets. |
| **9. Ambiguous Questions** | **2 (4.65%)** | Intentionally underspecified queries ("Can I sue someone?", "What is the limitation period?"). |
| **10. Negative / Out-of-Scope Questions** | **2 (4.65%)** | General knowledge questions outside Indian law ("What is the capital of France?", "What is Newton's third law?"). |
| **11. Single Relevant Targets** | **39 (100.0% of answerable)** | Every statutory question currently maps to exactly **one** canonical enactment. |
| **12. Multiple Relevant Targets** | **0 (0.00%)** | **Critical limitation**: In single-target benchmarks, multi-target Recall@K degenerates to Hit@K. Expanding to multi-statute targets is required in future annotation phases. |
| **13. Duplicate or Near-Duplicate Queries** | **0 Exact, 2 Near-Duplicates** | Flagged for human review: `constitution_001` vs `constitution_002` (Dice sim: 0.789); `bns_001` vs `bns_006` (Dice sim: 0.763). Both preserved without deletion. |
| **14. Possible Information Leakage** | **0 Confirmed Leakage** | Development: 43 queries; Validation: 0 queries; Test: 0 queries. No cross-partition pollution detected. |

---

## 3. Benchmark Schema Architecture

The formal schema is saved at `evaluation/benchmark_schema.json`.

```json
{
  "query_id": "bns_001",
  "question": "What is the punishment for committing theft under the Bharatiya Nyaya Sanhita?",
  "query_type": "direct_statutory",
  "difficulty": "medium",
  "statute": ["Bharatiya Nyaya Sanhita, 2023"],
  "legal_domain": ["Criminal Law"],
  "facts": null,
  "legal_issue": "Punishment for theft under new criminal code",
  "relevant_sections": ["Section 303"],
  "relevant_chunk_ids": [],
  "negative_or_ambiguous": false,
  "annotation_source": "legacy_test_questions",
  "review_status": "development_legacy"
}
```

*Scientific Principle Enforced*: No fields have been populated with fabricated ground truth. Where chunk-level IDs are not rigorously annotated by legal domain experts, they remain empty lists (`[]`) or `null` rather than simulated strings.

---

## 4. Benchmark Preservation and Partitioning

The filesystem structure has been preserved with clean research partitions:

```text
evaluation/
├── benchmark_schema.json
├── validate_benchmark.py
├── detect_duplicates.py
├── detect_leakage.py
├── analyze_coverage.py
├── test_questions.json          [Original legacy file preserved unmodified]
├── development/
│   └── existing_questions.json  [Preserved legacy dev benchmark with schema fields]
├── validation/
│   └── README.md                [Reserved for held-out tuning partition]
├── test/
│   └── README.md                [Reserved for blind held-out evaluation]
├── annotation_templates/
│   ├── question_annotation_template.json
│   ├── relevance_annotation_template.json
│   ├── compatibility_annotation_template.json
│   └── claim_grounding_annotation_template.json
└── results/
    ├── benchmark_coverage.json
    ├── benchmark_coverage.md
    ├── duplicate_report.json
    └── leakage_report.json
```

---

## 5. Duplicate and Near-Duplicate Detection Findings

Run via `evaluation/detect_duplicates.py`:

1. **Exact Matches**: 0
2. **Flagged Near-Duplicates** (Human Confirmation Required):
   - **Pair 1**:
     - *Query A*: `constitution_001`: "What fundamental rights are guaranteed by the Constitution of India?"
     - *Query B*: `constitution_002`: "What rights are guaranteed by the Constitution?"
     - *Similarity*: 0.789 (Character N-gram Dice)
     - *Recommendation*: Preserve both in development set; `constitution_002` evaluates robustness to underspecified queries.
   - **Pair 2**:
     - *Query A*: `bns_001`: "What is the punishment for committing theft under the Bharatiya Nyaya Sanhita?"
     - *Query B*: `bns_006`: "What is the punishment for organized crime under the Bharatiya Nyaya Sanhita?"
     - *Similarity*: 0.763 (Syntactic template overlap)
     - *Recommendation*: Keep both; they address completely distinct statutory offences (Theft vs. Organized Crime).

---

## 6. Leakage Detection Findings

Run via `evaluation/detect_leakage.py`:
- Cross-split query string overlap: **0**
- Cross-split query ID collision: **0**
- Leakage status: **PASSED (No leakage detected)**

---

## 7. Limitations and Recommendations for Future Annotation

1. **Statutory Imbalance**: 72% direct statutory questions vs 4.6% fact-pattern questions. Future phases should source realistic scenario-based legal prompts.
2. **Single Target Artifact**: All answerable questions have only one target enactment. Real Indian legal inquiries routinely involve overlapping procedural and substantive acts (e.g., BNS + BNSS, or IT Act + BNS).
3. **No Claim-Level Ground Truth**: The legacy benchmark contains document titles and keywords, but no sentence-level claim annotations. Phase 4 and beyond will use `claim_grounding_annotation_template.json` for manual legal verification.
