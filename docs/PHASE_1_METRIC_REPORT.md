# Phase 1 Report: Metric and Evaluation Integrity

**Date:** 2026-09-06  
**Status:** Completed and Validated  
**Branch:** `research-v2`  
**Auditor/Engineer:** Senior AI Research Scientist & IR Systems Architect  

---

## 1. Original Metric Defect

In the legacy implementation (`evaluation/metrics.py`), `Recall@K` was defined as:

```python
def calculate_recall_at_k(retrieved_docs: List[str], expected_doc: str, k: int) -> float:
    return 1.0 if calculate_hit_at_k(retrieved_docs, expected_doc, k) else 0.0
```

### Mathematical & Methodological Flaws
1. **Conflation with Hit@K**: The metric calculated binary single-target discovery rather than recall. If an expected document appeared anywhere in the top $K$, the score was $1.0$; otherwise, $0.0$.
2. **Failure on Multi-Target Benchmarks**: In realistic legal inquiries (e.g. queries involving procedural requirements and substantive offences, or multiple relevant statutory sections such as Sections 62 and 63 of BSA), a system retrieving only 1 out of 3 relevant provisions would be falsely credited with $100\%$ recall.
3. **Misleading Research Baselines**: Conflating discovery rate with recall inflated reported retrieval recall numbers and disguised partial-retrieval failures.

---

## 2. New Metric Definitions

All metrics have been partitioned into dedicated, standalone modules under `evaluation/metrics/`:

### A. Hit@K (`evaluation/metrics/hit_at_k.py`)
Measures whether *at least one* ground-truth target appears in the top $K$:
$$\text{Hit@K} = \begin{cases} 1.0 & \text{if } |\text{Top}_K \cap \text{Relevant}| \ge 1 \\ 0.0 & \text{otherwise} \end{cases}$$
Mean Hit@K across $N$ queries: $\frac{1}{N} \sum_{i=1}^N \text{Hit@K}_i$.

### B. Precision@K (`evaluation/metrics/precision_at_k.py`)
Measures the density of relevant items within the evaluated retrieved positions:
$$\text{Precision@K} = \frac{|\text{Top}_K \cap \text{Relevant}|}{\text{evaluated\_positions}}$$
By default, $\text{evaluated\_positions} = \min(K, |\text{Retrieved}|)$ to prevent penalizing queries where fewer than $K$ candidates exist. A `strict_k=True` flag is supported for strict TREC-style denominator ($K$).

### C. True Multi-Target Recall@K (`evaluation/metrics/recall_at_k.py`)
Measures the proportion of unique relevant ground-truth items retrieved in the top $K$:
$$\text{Recall@K} = \frac{|\text{Top}_K \cap \text{Relevant}|}{|\text{Relevant}|}$$
Where $\text{Relevant}$ is the deduplicated set of true relevant items.

### D. Reciprocal Rank & MRR (`evaluation/metrics/mrr.py`)
Calculates the reciprocal of the rank at which the first relevant document is retrieved:
$$\text{RR} = \begin{cases} \frac{1}{\text{rank}_1} & \text{if a relevant item is found} \\ 0.0 & \text{otherwise} \end{cases}$$
$$\text{MRR} = \frac{1}{N} \sum_{i=1}^N \text{RR}_i$$

### E. Discounted Cumulative Gain & nDCG@K (`evaluation/metrics/ndcg.py`)
Supports graded relevance ($0 = \text{irrelevant}, 1 = \text{marginal}, 2 = \text{relevant}, 3 = \text{highly relevant}$):
$$\text{DCG@K} = \sum_{i=1}^{\min(K, |\text{Retrieved}|)} \frac{2^{rel_i} - 1}{\log_2(i + 1)}$$
$$\text{IDCG@K} = \sum_{i=1}^{\min(K, |\text{Relevant}|)} \frac{2^{rel^*_i} - 1}{\log_2(i + 1)}$$
$$\text{nDCG@K} = \begin{cases} \frac{\text{DCG@K}}{\text{IDCG@K}} & \text{if } \text{IDCG@K} > 0 \\ 0.0 & \text{otherwise} \end{cases}$$

---

## 3. Edge-Case Conventions

| Scenario | Handled By | Behavior | Mathematical Justification |
|---|---|---|---|
| Empty retrieved list (`[]`) | All metrics | Returns `0.0` | Nothing retrieved; zero success. |
| Empty relevant set (`[]`) | All metrics | Returns `0.0` | No ground truth available; avoids division by zero. |
| Cutoff $K \le 0$ | All metrics | Returns `0.0` | Invalid rank threshold. |
| $K > |\text{Retrieved}|$ | Hit, Recall, MRR | Evaluates all retrieved | Partial candidate sets evaluated on available output. |
| $K > |\text{Retrieved}|$ | Precision@K | Evaluates on $\min(K, |\text{Retrieved}|)$ | Avoids artificial penalty for compact candidate sets. |
| Duplicate retrieved IDs | Recall@K, Precision@K | Deduplicated via set intersection | Prevents retriever gaming via repeated identical chunks. |
| $\text{IDCG} = 0$ | nDCG@K | Returns `0.0` | Safe handling when all items have zero relevance. |

---

## 4. Backward Compatibility

1. **Package Re-export**: `evaluation/metrics/__init__.py` re-exports the complete suite, including `calculate_keyword_coverage`.
2. **Adapter Layer (`evaluation/metrics.py`)**: Converted into a compatibility facade. Any legacy script importing `calculate_hit_at_k`, `calculate_precision_at_k`, `calculate_recall_at_k`, `calculate_reciprocal_rank`, or `calculate_keyword_coverage` continues to function.
3. **Legacy Behavioral Correction**: `calculate_recall_at_k` now correctly returns true recall ($|Retrieved_K \cap Relevant| / |Relevant|$) rather than aliasing `calculate_hit_at_k`.
4. **Call Sites Updated**:
   - `evaluation/evaluate_retrieval.py`: Now calculates and reports `ndcg_at_5`, `average_recall_at_5`, `mean_ndcg_at_5`, `hit_at_k`, `precision_at_5`, and `mean_reciprocal_rank`.

---

## 5. Test Results

### A. New Metric Unit Tests (`tests/test_metrics.py`)
- **Total Tests:** 36
- **Passed:** 36
- **Failed:** 0
- **Execution Time:** 0.002s
- **Coverage:**
  - `Hit@K`: Rank 1, Rank K, not found, multiple targets, partial matching, mean hit.
  - `Precision@K`: All relevant, none relevant, partial relevance (documented 2/3 example), fewer results than K, mean precision.
  - `Recall@K`: Single target, multi-target (documented 1/3 and 2/3 examples), full retrieval, no targets, duplicate retrieved items, mean recall.
  - `MRR`: Rank 1, Rank 2, later rank (documented 1/3 example), not found, multi-query arithmetic mean.
  - `nDCG@K`: Perfect ranking (1.0), imperfect ranking (manually verified 0.6806), all zero relevance, binary relevance mapping, mean nDCG.
  - `Edge Cases`: Empty retrieved lists, empty target sets, $K \le 0$, $K = 1$, $K > \text{length}$.
  - `Legacy Compatibility`: Signature checks, truthiness, keyword coverage.

### B. Existing Regression Test Suite (`rag-service/tests/`)
- **Total Tests:** 11
- **Passed:** 11 (100%)
- **Failed:** 0
- **Execution Time:** 62.87s
- **Status:** **PASS** (Zero regression on BSA electronic records, provision relationship validation, answer consistency, and workplace sexual harassment).

### C. Dense Retrieval Smoke Test (`evaluation/evaluate_retrieval.py --limit 3`)

> [!WARNING]
> **PIPELINE SMOKE TEST ONLY**:
> The 3-query run below was conducted solely to verify end-to-end telemetry and metric calculation plumbing. It evaluated only 3 cherry-picked queries (`constitution_001`, `constitution_002`, `constitution_003`). These scores (Hit@1=1.0, MRR=1.0, nDCG@5=1.0) must **NOT** be interpreted as evidence of overall retrieval performance or general system quality. Statistically sound measurements require full benchmark evaluation under comparable baseline conditions.

- **Status:** **PIPELINE VALIDATION ONLY** (Non-representative sample size $N=3$)
- **Queries Evaluated:** 3 statutory target queries
- **Document Hit@1:** 100.0% (Smoke test only)
- **Document Hit@3:** 100.0% (Smoke test only)
- **Document Hit@5:** 100.0% (Smoke test only)
- **Mean Reciprocal Rank:** 1.0000 (Smoke test only)
- **Average Precision@5:** 1.0000 (Smoke test only)
- **Average Recall@5:** 1.0000 (Smoke test only)
- **Mean nDCG@5:** 1.0000 (Smoke test only)
- **Average Keyword Coverage:** 91.67%
- **Output Artifact:** Generated [evaluation/results/retrieval_results.json](file:///c:/Users/Yuvraj%20Singh/Downloads/NyayaSetu/evaluation/results/retrieval_results.json)
