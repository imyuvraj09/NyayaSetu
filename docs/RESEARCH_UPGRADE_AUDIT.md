# NyayaSetu Research Upgrade Repository Audit (Phase 0)

**Date:** 2026-09-06  
**Status:** Completed Phase 0 Audit & Verification  
**Auditor:** Senior AI Research Engineer & Systems Architect  
**Branch:** `research-v2` (checked out from `main` commit `008de31e7a243522cf88f7ad4c95b9eee0d175e4`)  
**Scope:** Complete Codebase (Frontend, Backend, RAG Service, Evaluation, Ingestion, Tests, Deployment)

---

## 1. Current System Architecture

NyayaSetu is structured as a production-grade, three-tier legal research assistant:

```text
┌──────────────────────────────┐
│  Frontend (React 19 + Vite)  │  Port 5173
│  Chat UI, Citations & Badges │
└──────────────┬───────────────┘
               │ HTTP / JSON
┌──────────────▼───────────────┐
│  Backend (Node.js + Express) │  Port 3000
│  API Gateway & Orchestration │
└──────────────┬───────────────┘
               │ HTTP / JSON
┌──────────────▼───────────────┐
│  RAG Service (Python FastAPI)│  Port 8000
│  Retrieval, Rerank, LLM, RAG │
└──────────────────────────────┘
```

### Component Details
1. **Frontend (`frontend/`)**: React 19 SPA with modern UI tokens, responsive layouts, legal citation modals, contributor provenance, and chat streaming support.
2. **Backend (`backend/`)**: Express.js API gateway acting as a proxy and session manager. Routes `/api/chat` and `/api/query` requests to the Python RAG service via `ragService.js`.
3. **RAG Service (`rag-service/`)**: FastAPI application containing text processing, dense and lexical indexing, hybrid retrieval, cross-encoder reranking, LLM answer synthesis, citation validation, and fallback handling.
4. **Evaluation Engine (`evaluation/`)**: Evaluation suite containing benchmark datasets, retrieval evaluators, end-to-end evaluators, and validation runners.

---

## 2. Current Request Flow

```text
User enters legal question in React Frontend UI
    │
    ▼ POST /api/chat or /api/query
Node.js Express Backend (backend/src/services/ragService.js)
    │
    ▼ POST http://localhost:8000/api/v1/query (QueryRequest)
FastAPI Route Handler (rag-service/api/routes.py:query)
    │
    ▼ LegalRAGPipeline.query() (rag-service/rag/rag_pipeline.py)
    ├─ 1. AdvancedRetriever.retrieve()
    │     ├─ LegalQueryAnalyzer: extracts act candidates, intent, concepts
    │     ├─ Dense Search (ChromaDB + bge-small-en-v1.5)
    │     ├─ Lexical Search (In-memory BM25Okapi)
    │     ├─ Section / Title exact matching
    │     ├─ RRF Fusion with Statute Purity Boosting
    │     ├─ UniversalEvidenceFilter (unit & scope validation)
    │     └─ Cross-Encoder Reranker (bge-reranker-base)
    ├─ 2. CaseLawRetriever.retrieve() (if authority requirement includes case law)
    ├─ 3. LegalContextBuilder.build_context() -> formats [SOURCE 1] ... [SOURCE K]
    ├─ 4. LLM Generation (Google Gemini / OpenAI / DeterministicAnswerBuilder fallback)
    ├─ 5. ClaimEvidenceValidator & LegalAnswerValidator
    │     ├─ Extracts claims via regex
    │     ├─ Verifies citations match source labels
    │     └─ Checks for disallowed out-of-scope topics
    └─ 6. Sanitization & Serialization into RAGResponse
    │
    ▼ QueryResponse (JSON: answer, sources, citations, session_id)
Forwarded through Express Gateway to Frontend React UI
```

---

## 3. Current Retrieval Pipeline

The existing retrieval pipeline in `rag-service/retrieval/advanced_retriever.py` follows a multi-strategy architecture:
- **Dense Semantic Retrieval**: `SimilaritySearchService` using ChromaDB (`chroma_store.py`) with cosine similarity and `BAAI/bge-small-en-v1.5` embeddings (384-dimensional).
- **Lexical Keyword Search**: `retrieval/bm25_search.py` implementing in-memory BM25Okapi over 6,545 pre-indexed chunks.
- **Section & Title Exact Indexing**: `retrieval/section_indexer.py` with canonical titles.
- **Evidence Fusion**: Reciprocal Rank Fusion (RRF) with statute purity boosting.
- **Candidate Filtering**: `retrieval/evidence_relevance_filter.py` classifies chunks into DIRECT, RELATED, BACKGROUND, IRRELEVANT, CONTRADICTORY.
- **Reranking**: `retrieval/reranker.py` with `BAAI/bge-reranker-base` and sigmoid logit scaling.

---

## 4. Current Evaluation Metrics

Located in `evaluation/metrics.py`:
- `calculate_hit_at_k`: Binary check whether the target enactment appears in the top $K$ results.
- `calculate_reciprocal_rank`: Reciprocal rank $\frac{1}{\text{rank}}$ of the first occurrence of the expected document.
- `calculate_precision_at_k`: Fraction of top $K$ documents matching the expected document.
- `calculate_recall_at_k`: **CRITICAL FLAW DETECTED**:
  ```python
  def calculate_recall_at_k(retrieved_docs: List[str], expected_doc: str, k: int) -> float:
      return 1.0 if calculate_hit_at_k(retrieved_docs, expected_doc, k) else 0.0
  ```
  The existing codebase equated Recall@K to Hit@K (single-target discovery rate), conflating discovery with multi-target recall.
- `calculate_keyword_coverage`: Lexical overlap of expected statutory terms.

---

## 5. Current Benchmark Structure

- **Benchmark Dataset**: `evaluation/test_questions.json` (43 questions across 7 statutes).
- **Current Fields**:
  ```json
  {
    "id": "constitution_001",
    "question": "What fundamental rights are guaranteed by the Constitution of India?",
    "category": "constitutional_law",
    "expected_document": "Constitution of India",
    "expected_keywords": ["Fundamental Rights", "Part III", "Article", "freedom"],
    "expected_section": "Part III",
    "difficulty": "medium",
    "notes": "Core fundamental rights query across Part III."
  }
  ```
- **Limitations**:
  - Single unstratified file (no split into development, validation, test).
  - Only specifies single `expected_document` and `expected_section`, which prevented true Recall@K and graded nDCG calculation.
  - Lacks fine-grained query taxonomy (direct statutory, section identification, fact-pattern, multi-part, cross-section, ambiguous, out-of-scope).
  - No automated schema validation, duplicate detection, or test-leakage detection.

---

## 6. Existing Baselines

Currently, the evaluation scripts (`evaluate_retrieval.py`, `evaluate_reranking.py`, `evaluate_end_to_end.py`) only test the full composite pipeline or isolated dense retrieval:
- There is no Direct LLM (Zero-Retrieval) baseline runner.
- There is no isolated Dense RAG baseline (no routing, no filter, no reranking).
- There is no isolated Hybrid RAG baseline (Dense + BM25 fusion directly into LLM).
- Ablation experiments cannot be run via command-line flags or configuration files because pipeline components are coupled in `LegalRAGPipeline`.

---

## 7. Existing Claim Validation Mechanism

Located in `rag-service/retrieval/claim_evidence_validator.py` and `rag/answer_validator.py`:
- Extracts legal claims from generated answers using regex sentence splitting.
- Detects negative assertions (e.g., "sources do not contain") and disclaimers.
- Matches extracted claims to retrieved sources using:
  - Mentioned statutory sections
  - Cited labels (`[Source N]`, `[Case Source C1]`)
  - Jaccard token overlap
  - Excluded topic violations
- Limitations:
  - Lacks structured 3-state classification: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`.
  - Does not provide generalized claim repair (conservative rewriting) or principled abstention.

---

## 8. Existing Hard-Coded or Domain-Specific Logic

The repository contains several brittle domain-specific shortcuts that will be generalized:
1. **Act Regex Hardcoding** (`claim_evidence_validator.py` lines 140–152): Explicit hardcoded strings for BNS, BNSS, BSA, RTI, Consumer Protection, and POCSO.
2. **Facet Override Rules** (`claim_evidence_validator.py` line 179): `if sec_ref and sec_ref.startswith("103"): assigned_facet = "punishment"`.
3. **Provision Relationship Shortcuts** (`provision_relationship_validator.py`): Explicitly couples BSA Section 62 and Section 63 while lacking a general graph/schema for other statutory relationships.
4. **Deterministic Fallback Answers** (`deterministic_answer_builder.py`): 141 KB of static rule-based answer templates for specific questions when external LLM providers are unavailable.

---

## 9. Files That Require Modification

1. `evaluation/metrics.py`: Refactored to import and re-export the new mathematically rigorous metric suite for backward compatibility.
2. `evaluation/evaluate_retrieval.py`: Updated to report true Recall@K, Precision@K, Hit@K, MRR, and nDCG@K.
3. `evaluation/evaluate_end_to_end.py`: Updated to support multi-target metric reporting.
4. `evaluation/schemas.py`: Extended to support the enhanced benchmark query schema.
5. `rag-service/rag/rag_pipeline.py`: Updated to accept modular research pipeline configuration switches.

---

## 10. Existing Modules That Can Be Reused

The existing codebase contains solid foundational modules that should be **reused and enhanced**, rather than duplicated:
1. **`retrieval.bm25_search.BM25SearchEngine`**: In-memory BM25Okapi implementation with legal tokenization.
2. **`retrieval.similarity_search.SimilaritySearchService`**: ChromaDB vector store wrapper with bge-small-en-v1.5 embeddings.
3. **`retrieval.reranker.LegalReranker`**: Cross-encoder service using BAAI/bge-reranker-base with sigmoid calibration.
4. **`retrieval.section_indexer.SectionIndexer`**: Chunk mapping and section number indexing over all 6,545 statutory chunks.
5. **`retrieval.legal_question.LegalQuestionAnalyzer`**: Initial question parsing concepts.
6. **`rag.context_builder.LegalContextBuilder`**: Source labelling and context budgeting.
7. **`rag.answer_validator.LegalAnswerValidator`**: Citation existence and formatting verification.
8. **`utils.config.settings`**: Centralized configuration management.

---

## 11. Potential Backward Compatibility Risks

1. **API Response Contract**: Frontend and Node.js backend rely on `QueryResponse` (`answer`, `sources`, `citations`, `session_id`). All research components must serialize cleanly into this existing contract.
2. **Deterministic Fallback**: When LLM keys are absent, fallback generation must gracefully provide retrieved statutory provisions.
3. **Regression Test Integrity**: Existing test suites (`test_issue12_regression.py`, `test_legal_rag_improvements.py`) must continue to pass 100% without breakage.
4. **Import Stability**: Any code importing `calculate_recall_at_k` or other functions from `evaluation.metrics` must remain fully supported via forwarders.

---

## Verification Against Real Repository (Mismatch Analysis)

| Plan Assumption | Actual Repository State | Impact & Alignment Decision |
|---|---|---|
| Python in PATH | Python 3.14 on system lacks packages; `rag-service/venv` has all dependencies (`sentence-transformers`, `chromadb`, `torch`, `pydantic-settings`). | Use `.\rag-service\venv\Scripts\python.exe` for all pipeline and test executions. |
| BM25 existence | BM25 is already implemented in `rag-service/retrieval/bm25_search.py`. | Reuse `BM25SearchEngine` directly for Baseline C (Hybrid RAG). |
| PyYAML availability | PyYAML is installed in `rag-service/venv`. | YAML configs can be parsed and validated without extra installs. |
| Existing Tests | 11 existing unit/regression tests in `rag-service/tests/` take ~95s on CPU and pass 100%. | Keep test suite as a hard non-regression gate after every phase. |
