# NyayaSetu Evaluation & Quality Assurance Framework (Phase 8)

Comprehensive evaluation framework for measuring information retrieval quality, cross-encoder reranking efficacy, citation integrity, answer grounding, and system safety across Indian statutory law.

---

## 📊 Evaluation Architecture

```
evaluation/
├── test_questions.json          # 43 structured benchmark queries across 7 enactments + edge cases
├── metrics.py                   # IR metrics (Hit@K, MRR, Precision@K, Recall@K, Keyword Coverage)
├── evaluate_retrieval.py        # Dense semantic retrieval evaluator (Stage 1)
├── evaluate_reranking.py        # Cross-encoder comparative reranking evaluator (Stage 1 vs Stage 2)
├── evaluate_end_to_end.py       # Full pipeline evaluator with latency & safety testing
├── validators/
│   ├── citation_validator.py    # Structural & bound citation verification
│   └── source_validator.py      # Source chunk metadata and provenance validator
├── results/
│   ├── retrieval_results.json   # Dense retrieval performance log
│   ├── reranking_results.json   # Reranker rank-shift analysis
│   ├── end_to_end_results.json  # Full pipeline execution log
│   └── evaluation_summary.json  # Aggregated metrics & latency summary
└── README.md                    # Framework documentation
```

---

## 🔬 Benchmark Dataset (`test_questions.json`)

Contains **43 structured questions**:
- **39 Statutory Target Queries** distributed across all 7 indexed enactments:
  1. Constitution of India (6 queries)
  2. Bharatiya Nyaya Sanhita, 2023 (6 queries)
  3. Bharatiya Nagarik Suraksha Sanhita, 2023 (6 queries)
  4. Bharatiya Sakshya Adhiniyam, 2023 (6 queries)
  5. Consumer Protection Act (5 queries)
  6. Information Technology Act (5 queries)
  7. Motor Vehicles Act (5 queries)
- **4 Negative / Failure Test Queries**:
  - Out-of-Scope (e.g. *"What is the capital of France?"*, *"What is Newton's third law of motion?"*)
  - Ambiguous (e.g. *"Can I sue someone?"*, *"What is the limitation period?"*)

Each record includes:
`id`, `question`, `category`, `expected_document`, `expected_keywords`, `expected_section`, `difficulty`, `notes`.

---

## 📈 Metric Definitions & Mathematical Bounds

1. **Document Hit@K**:
   $$\text{Hit@K} = 1 \text{ if expected enactment} \in \text{retrieved\_docs}[0:K] \text{ else } 0$$
   *Limitation*: Measures document-level retrieval presence only; does not replace judicial interpretation.

2. **Mean Reciprocal Rank (MRR)**:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
   where $\text{rank}_i$ is the 1-based index of the first retrieved chunk belonging to the expected enactment.

3. **Precision@5**:
   $$\text{Precision@5} = \frac{\text{count of chunks in top 5 matching expected document}}{5}$$

4. **Keyword Coverage**:
   Fraction of statutory keywords identified within retrieved passages.

5. **Citation Format Correctness vs. Citation Relevance**:
   - **Format Correctness**: Answer cites valid `[Source N]` tags within the range of retrieved passages, without syntax errors or hallucinated numbers (`[Source 99]`).
   - **Citation Relevance**: The cited `[Source N]` chunk belongs to the legally expected enactment for the given question.

---

## 🚀 Running the Evaluation Suite

```powershell
# 1. Activate environment
cd "rag-service"
venv\Scripts\activate

# 2. Run Dense Retrieval Evaluation
python -m evaluation.evaluate_retrieval

# 3. Run Reranking Impact Comparison
python -m evaluation.evaluate_reranking

# 4. Run Complete End-to-End Pipeline Evaluation
python -m evaluation.evaluate_end_to_end
```

---

## ⚡ Development Runtime Observations (Latency)

All latency measurements are measured on standard CPU development environments and labeled strictly as **Development Runtime Observations**:
- **Two-Stage Retrieval (Dense + Rerank)**: ~4.7s
- **Context Assembly (20k chars budget)**: ~0.3ms
- **Deterministic Validation**: ~0.1ms
- **Total End-to-End**: ~4.7s
