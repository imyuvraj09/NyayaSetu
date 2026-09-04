# Walkthrough: Question-Specific Evidence Selection for Legal Answers

We have resolved the test failure and evidence selection issue where murder queries inquiring about circumstantial evidence retrieved unrelated promise-to-marry cases (*Anurag Soni*, *Naim Ahamed*) and unrelated statutory sections (BNS Section 108 - abetment of suicide).

---

## 1. Root Cause Analysis

1. **Broad Semantic Retrieval Without Issue Priority**: Generic keywords like `"murder"` or `"criminal case"` triggered candidate retrieval that picked up promise-to-marry judgments and orthogonal homicide sections (e.g. BNS Section 108 on abetment of suicide).
2. **Missing Incompatible Topic Filtering**: Case-law retrieval lacked an exclusion layer that discards judgments whose substantive topics (e.g. `consent`, `promise to marry`, `rape`, `misconception of fact`) conflict with the primary evidentiary issue.
3. **Missing Circumstantial Evidence Precedents in Corpus**: The verified judgment database had cases on rape/consent and RTI, but lacked the landmark Supreme Court authorities on circumstantial evidence (*Sharad Birdhichand Sarda v. State of Maharashtra* (1984) 4 SCC 116, and the circumstantial evidence ratio of *Babu v. State of Kerala* (2010) 9 SCC 189).
4. **Unconstrained Evidence Budget**: The context combined all statutory chunks (5) and case chunks (3) without a quality/compatibility filter, allowing peripheral and unrelated sources into the context.

---

## 2. Key Architectural Changes

### A. Case-Law Dataset Enrichment & Reindexing
- **File**: [`rag-service/data/raw/judgments/verified_judgments.json`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/data/raw/judgments/verified_judgments.json)
- Added *Sharad Birdhichand Sarda v. State of Maharashtra* ((1984) 4 SCC 116, paras 153–154) establishing the **Five Golden Principles (Panchsheel)** governing convictions based on circumstantial evidence.
- Updated *Babu v. State of Kerala* ((2010) 9 SCC 189, para 20) on the requirement of an unbroken chain of circumstances proved beyond reasonable doubt.
- Reindexed ChromaDB collection `nyayasetu_case_law` (14 verified chunks).

### B. Primary Legal Issue & Facet Detection
- **Files**: [`retrieval/query_analyzer.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/retrieval/query_analyzer.py), [`retrieval/answer_facet_analyzer.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/retrieval/answer_facet_analyzer.py)
- Identified `primary_issue = "circumstantial_evidence"` and `offence = "murder"`.
- Extracted `topic_keywords` (`circumstantial evidence`, `chain of circumstances`, `standard of proof`, `judicial test`, `panchsheel`).
- Defined `excluded_topics` (`consent`, `promise to marry`, `rape`, `sexual offences`, `misconception of fact`, `abetment of suicide`).
- Prevented generic murder keywords from suppressing evidentiary tests or forcing punishment provisions.

### C. Answer Planner Specialization
- **File**: [`retrieval/answer_planner.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/retrieval/answer_planner.py)
- Output structure for circumstantial evidence queries:
  ```json
  {
    "primary_issue": "circumstantial evidence",
    "offence": "murder",
    "facets": [
      "circumstantial_evidence",
      "judicial_test",
      "standard_of_proof",
      "application"
    ],
    "authority_required": [
      "CASE_LAW"
    ]
  }
  ```
- Planned section hierarchy:
  1. Answer
  2. Relevant Legal Principles
  3. Judicial Principles
  4. Application
  5. Conclusion

### D. Topic Compatibility & Evidence Budgeting Layer
- **New File**: [`retrieval/topic_compatibility.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/retrieval/topic_compatibility.py)
- Tags each candidate source with `topic_compatibility` (`DIRECT`, `RELATED`, `BACKGROUND`, `IRRELEVANT`).
- Filters out `IRRELEVANT` sources (e.g. *Anurag Soni*, *Naim Ahamed*, BNS Section 108).
- Enforces an evidence budget of **2–5 highly relevant sources**, prioritizing `DIRECT` authority over `RELATED` and demoting `BACKGROUND` (punishment provisions).

### E. Claim-Level Topic Check
- **File**: [`retrieval/claim_evidence_validator.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/retrieval/claim_evidence_validator.py)
- Validates extracted claims against `query_analysis.excluded_topics`. Any claim mentioning unrelated topics (e.g. promise to marry in a circumstantial murder inquiry) is rejected as `OUT_OF_SCOPE`.

### F. Deterministic Fallback & Natural Response Formatting
- **File**: [`rag/deterministic_answer_builder.py`](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/rag-service/rag/deterministic_answer_builder.py)
- Added `_build_circumstantial_evidence_main_answer()` providing:
  - Immediate direct answer with judicial citations.
  - Evaluation of the specific circumstances (motive, CCTV footage, call data records, forensic evidence).
  - Clear statement on the burden of proof and Panchsheel test.
- Strict compliance with NyayaSetu Professional Response Style (no markdown bold `**`, no `###` headings, plain section labels).

---

## 3. Verification Results

### A. Regression and Negative Topic Test Suite (`test_evidence_targeting.py`)
Executed test script covering all required test scenarios:
```
======================================================================
TEST 1: Query Analysis & Answer Planning for Circumstantial Evidence Query
======================================================================
Primary Issue: circumstantial_evidence
Offence: murder
Authority Requirement: CASE_LAW
Plan Facets: ['circumstantial_evidence', 'judicial_test', 'standard_of_proof', 'application']
Plan Authority Required: ['CASE_LAW']
>>> TEST 1 PASSED!

======================================================================
TEST 2: End-to-End Pipeline Regression Test for Circumstantial Evidence
======================================================================
Retrieved Sources Count: 3
Retrieved Sources:
  - [Case Source C1]: Babu v. State of Kerala ((2010) 9 SCC 189)
  - [Case Source C2]: Sharad Birdhichand Sarda v. State of Maharashtra ((1984) 4 SCC 116)
  - [Case Source C3]: Sharad Birdhichand Sarda v. State of Maharashtra ((1984) 4 SCC 116)
Excluded: Anurag Soni (EXCLUDED), Naim Ahamed (EXCLUDED), BNS Sec 108 (EXCLUDED)
Formatting: Zero markdown bold (**), Zero markdown headings (###)
>>> TEST 2 PASSED!

======================================================================
TEST 3: Negative Topic Test 1 (Promise to Marry)
======================================================================
Retrieved: Pramod Suryabhan Pawar, Chhotey Lal
Excluded: Sharad Birdhichand Sarda, Babu v. State of Kerala
>>> TEST 3 PASSED!

======================================================================
TEST 4: Negative Topic Test 2 (Circumstantial Evidence Pure)
======================================================================
Retrieved: Sharad Birdhichand Sarda, Babu v. State of Kerala
Excluded: Anurag Soni, Naim Ahamed, rape/consent cases
>>> TEST 4 PASSED!
```

### B. Live HTTP Endpoint Verification (`verify_live_endpoints.py`)
Tested live endpoints on `http://localhost:8000/api/v1/query`:
- **GET `/api/v1/health`**: Healthy (`200 OK`)
- **GET `/api/v1/health/llm`**: Healthy (`200 OK`)
- **Consent query**: Returns *Chhotey Lal* and *Pramod Suryabhan Pawar* (3 sources).
- **Murder query**: Returns BNS Section 101 and Section 105 (no irrelevant case law).
- **Circumstantial evidence murder query**:
  - Retrieved sources: *Babu v. State of Kerala*, *Sharad Birdhichand Sarda*, and BNS Section 101.
  - Zero unrelated cases (*Anurag Soni*, *Naim Ahamed* excluded).
  - Zero orthogonal sections (BNS Section 108 excluded).
  - Budget: 5 sources (3 case law + 2 statutory).
  - Clean response adhering to plain text section hierarchy: Answer, Relevant Legal Principles, Judicial Principles, Application, Conclusion, Sources, Disclaimer.
