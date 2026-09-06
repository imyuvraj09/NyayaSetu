# Phase 2 — Baseline Measurement and Experimental Report
## DEVELOPMENT BENCHMARK BASELINE RESULTS (PRELIMINARY / NOT FINAL PUBLICATION)

**Date**: September 6, 2026  
**Repository Branch**: `research-v2`  
**Evaluation Platform**: NyayaSetu Legal Information Retrieval & Question Answering Platform  
**Benchmark**: `evaluation/development/existing_questions.json` (N = 43 total queries, 39 evaluable statutory queries, 4 negative/ambiguous queries)  
**Status**: DEVELOPMENT BENCHMARK ONLY — NOT CLAIMED AS FINAL PUBLICATION RESULTS  
**Hardware Environment**: Intel 64-bit Architecture, Windows 11, PyTorch CPU Execution  
**Python Runtime**: `.\rag-service\venv\Scripts\python.exe` (Python 3.13.2)  
**Experiment Manifest Directory**: `results/experiments/`  
**Aggregated Results**: `results/baseline_comparison.csv` and `results/baseline_comparison.json`

---

## 1. Executive Summary and Critical Metric Disclaimer

> [!IMPORTANT]
> **DEVELOPMENT BENCHMARK CLARIFICATION**:
> The experimental results presented in this report reflect the **DEVELOPMENT BENCHMARK BASELINE RESULTS** evaluated against `evaluation/development/existing_questions.json` (N = 43 total queries, 39 evaluable statutory queries).
> **These results are preliminary engineering baselines used for regression testing, architectural isolation verification, and error analysis. They must NOT be described or cited as final publication results.**
> 
> The initial 3-query runs (`--limit 3`) reported during pipeline setup were **smoke tests for pipeline validation only**. The 100% scores obtained on those 3 questions were an artifact of small-sample saturation and must **never** be cited as evidence of NyayaSetu's retrieval quality.
> 
> The measurements presented below represent the **full evaluation of the complete development benchmark across all 43 queries**.

---

## 2. Experimental Configurations and Strict Architectural Isolation

To ensure scientific defensibility, each baseline was executed from an independent YAML configuration with strictly validated architectural flags. No baseline secretly accessed downstream or upstream research components.

```yaml
# Strict Architectural Isolation Matrix
| Feature Switch              | Baseline A (Direct LLM) | Baseline B (Dense RAG) | Baseline C (Hybrid RAG) | Baseline D (Hybrid RAG + Cross-Encoder Reranking) |
| :-------------------------- | :---------------------- | :--------------------- | :---------------------- | :------------------------------------------------ |
| `use_retrieval`             | false                   | true                   | true                    | true                                              |
| `use_dense_retrieval`       | false                   | true                   | true                    | true                                              |
| `use_bm25`                  | false                   | false                  | true                    | true                                              |
| `use_hybrid_fusion`         | false                   | false                  | true                    | true                                              |
| `use_reranker`              | false                   | false                  | false                   | true                                              |
| `use_fact_routing`          | false                   | false                  | false                   | false                                             |
| `use_compatibility_filter`  | false                   | false                  | false                   | false                                             |
| `use_claim_repair`          | false                   | false                  | false                   | false                                             |
```

### Baseline A: Direct LLM (Closed-Book Generation)
- **Architecture**: `Question → LLM → Answer`
- **Retrieval Engine**: Disabled (`top_k = 0`). No external evidence provided.
- **Model**: `google-gemini` (`gemini-3.6-flash`) with deterministic offline fallback (`MockLLMProvider`).
- **Prompt**: Direct statutory generation based exclusively on internal model parameters.

### Baseline B: Dense RAG (Single-Stage Dense Semantic Retrieval)
- **Architecture**: `Question → BAAI/bge-small-en-v1.5 Dense ChromaDB Retrieval → Top-5 Evidence → LLM → Answer`
- **Lexical BM25**: Disabled.
- **Reranking**: Disabled.
- **Retrieval Budget**: Exactly top $K=5$ nearest vectors via cosine distance.

### Baseline C: Hybrid RAG (Reciprocal Rank Fusion)
- **Architecture**: `Question → Dense Retrieval (Top 20) + BM25 Search (Top 20) → RRF Fusion (k=60) → Top-5 Evidence → LLM → Answer`
- **Lexical Engine**: Verified in-memory BM25 over 6,545 indexed statutory chunks.
- **Fusion Formula**: $RRF\_Score(d) = \sum_{m \in \{dense, bm25\}} \frac{1}{60 + r_m(d)}$.
- **Reranker**: Disabled.

### Baseline D: Hybrid RAG + Cross-Encoder Reranking
- **Architecture**: `Question → Hybrid Candidate Pool (Dense + BM25 + RRF Top 20) → BAAI/bge-reranker-base Cross-Encoder → Top-5 Evidence → LLM → Answer`
- **Candidate Pool Size**: 20 chunks generated via dual-stream RRF hybrid search.
- **Cross-Encoder Model**: `BAAI/bge-reranker-base` evaluated with batch size 16 on CPU.
- **Final Context Budget**: Top $K=5$ reranked passages.

---

## 3. Full Development Benchmark Results (N = 43 Queries)
### DEVELOPMENT BENCHMARK BASELINE RESULTS

The following results were generated automatically by `experiments/run_experiment.py` and synthesized via `experiments/aggregate_results.py`:

| Baseline Configuration | Evaluated Queries ($N$) | Hit@1 | Hit@3 | Hit@5 | Prec@5 | Recall@5 | MRR | nDCG@5 | Avg. Retr. Latency | Avg. Total Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline A: Direct LLM** | 43 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000s | 0.0531s |
| **Baseline B: Dense RAG** | 43 | 0.8974 | 0.9744 | 0.9744 | 0.8051 | 0.9744 | 0.9359 | 0.9649 | 1.8361s | 1.8819s |
| **Baseline C: Hybrid RAG** | 43 | **0.9231** | **1.0000** | **1.0000** | **0.8462** | **1.0000** | **0.9573** | **0.9872** | **0.3792s** | **0.4133s** |
| **Baseline D: Hybrid RAG + Cross-Encoder Reranking** | 43 | 0.8974 | 0.9487 | 0.9744 | 0.8359 | 0.9744 | 0.9295 | 0.9697 | 13.0859s | 13.1362s |

*Note: All retrieval metrics are calculated over the 39 evaluable statutory queries (excluding the 4 out-of-scope/ambiguous queries which have null target documents).*

---

## 4. Key Experimental Findings and Retrieval Dynamics

1. **Hybrid Retrieval Outperforms Dense Alone**:
   - **Dense RAG** achieved Hit@1 of 0.8974 and Hit@5 of 0.9744, missing `bns_001` ("What is the punishment for committing theft under the Bharatiya Nyaya Sanhita?").
   - **Hybrid RAG** achieved **Hit@1 of 0.9231 and Hit@5 of 1.0000 (MRR = 0.9573)**. The exact lexical match on statutory terms like *"Bharatiya Nyaya Sanhita"* and *"punishment for committing theft"* successfully rescued `bns_001` to rank 3.
   - Precision@5 increased from **0.8051 to 0.8462**, confirming higher document concentration among top-5 retrieved passages.

2. **Reranker Trade-off on CPU**:
   - **Baseline D (Hybrid RAG + Cross-Encoder Reranking)** successfully promoted specific hard queries: for example, query `bns_005` ("What constitutes criminal conspiracy?") was ranked at position 2 in Dense RAG ($RR=0.50$), but was correctly promoted to rank 1 ($RR=1.00$) by the cross-encoder.
   - However, on two specific legal queries (`bsa_006` and `it_003`), cross-encoder semantic scoring over-emphasized general legal terminology, slightly adjusting top-1 rank and yielding an overall MRR of 0.9295 vs 0.9573 for pure Hybrid RRF.
   - **Latency Trade-off**: Cross-encoder scoring of 20 long statutory passages on CPU introduced ~13.08s latency per query compared to ~0.38s for Hybrid RRF.

3. **Baseline A Demonstrates the Necessity of Retrieval**:
   - Closed-book Direct LLM has 0 retrieval evidence, scoring 0 across all retrieval metrics. Without retrieval grounding, generation relies entirely on pre-trained parametric weights, creating severe risks of hallucinated section numbers under newly enacted 2023 criminal codes (BNS, BNSS, BSA).

---

## 5. Statistical and Sample-Size Limitations

1. **Sample Size ($N=43$)**:
   - While adequate for distinguishing dense vs hybrid retrieval trends, $N=39$ evaluable queries is too small to claim statistically significant superiority (e.g., $p < 0.01$ via paired t-test or Wilcoxon signed-rank test). Differences of 1–2 queries represent a $\pm 2.5\%$ metric swing.
   - Findings must be interpreted as **preliminary development baselines**.
2. **Single Target Artifact**:
   - All 39 evaluable queries in the legacy benchmark specify a single target enactment. Consequently, **Recall@5 identically equals Hit@5** ($1.0000$). Multi-target recall differentiation will only become measurable once multi-statute queries are annotated in Phase 4.
3. **No Answer Accuracy Claims**:
   - In strict compliance with Part K of the specification, **no claims of "Answer Accuracy", "Legal Correctness", or "Factuality" are made** for generated completions, because sentence-level claim annotations and verified legal rubrics do not yet exist for the full dataset.

---

## 6. Reproducibility Manifest

All raw experiment artifacts are immutably archived and reproducible:

| Experiment Run | Output Directory | Artifacts Verified |
| :--- | :--- | :--- |
| **Baseline A: Direct LLM** | `results/experiments/baseline_direct_llm_20260905_214404` | `config.yaml`, `manifest.json`, `metrics.json`, `predictions.jsonl`, `logs.txt`, `environment.txt` |
| **Baseline B: Dense RAG** | `results/experiments/baseline_dense_rag_20260905_214433` | `config.yaml`, `manifest.json`, `metrics.json`, `predictions.jsonl`, `logs.txt`, `environment.txt` |
| **Baseline C: Hybrid RAG** | `results/experiments/baseline_hybrid_rag_20260905_214630` | `config.yaml`, `manifest.json`, `metrics.json`, `predictions.jsonl`, `logs.txt`, `environment.txt` |
| **Baseline D: Hybrid RAG + Cross-Encoder Reranking** | `results/experiments/baseline_reranked_rag_20260905_214807` | `config.yaml`, `manifest.json`, `metrics.json`, `predictions.jsonl`, `logs.txt`, `environment.txt` |

---

## 7. Recommended Next Phase

The baseline measurements provide a trustworthy, rigorous, reproducible baseline.

**Mandatory Stop Condition reached.**  
Awaiting review and approval to proceed to:
# PHASE 3 — FACT-FIRST LEGAL ISSUE ROUTING
