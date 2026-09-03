# NyayaSetu RAG Service

AI-powered Retrieval-Augmented Generation service for Indian legal knowledge.

---

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# 4. Start the FastAPI service
uvicorn main:app --reload --port 8000
```

---

## 📜 Legal Document Ingestion (Phase 3)

Extracts, cleans, and structures raw statutory PDFs into serialized page records.
- Raw PDFs: `rag-service/data/raw/`
- Output: `rag-service/data/processed/legal_documents.jsonl`
- CLI:
```bash
python -m ingestion.ingestion_pipeline
```

---

## 🧩 Legal Text Chunking (Phase 4)

Transforms page records into context-preserving retrieval chunks (`~1200 chars`).
- Input: `rag-service/data/processed/legal_documents.jsonl`
- Output: `rag-service/data/processed/legal_chunks.jsonl` (4,184 chunks)
- CLI:
```bash
python -m ingestion.chunking_pipeline
python -m ingestion.chunking_pipeline --inspect 3
```

---

## 🔍 Embedding & Vector Store (Phase 5)

Generates dense semantic vector embeddings for all legal chunks and indexes them into a persistent local ChromaDB collection for nearest-neighbor search.
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (384 dimensions)
- **Vector Database**: `ChromaDB` (`vector_store/chroma_db/`)
- **Collection**: `nyayasetu_legal_documents`
- CLI:
```bash
python -m vectorstore.vectorstore_pipeline
python -m vectorstore.vectorstore_pipeline --inspect
python -m retrieval.similarity_search "What is the punishment for theft?" --top-k 3
```

---

## ⚡ Advanced Retrieval & Cross-Encoder Reranking (Phase 6)

Two-stage legal retrieval combining candidate generation with cross-attention reranking for statutory precision.
- **Reranker Model**: `BAAI/bge-reranker-base` (CrossEncoder)
- CLI:
```bash
python -m retrieval.retrieval_pipeline "What is the punishment for theft?"
python -m retrieval.retrieval_pipeline "What is the punishment for theft?" --compare
```

---

## 🤖 Grounded LLM Answer Generation (OpenAI Primary)

Generates factual, grounded, and cited natural language legal answers using retrieved and reranked statutory sources with OpenAI as the primary production provider.

### 1. RAG Pipeline Flow
```
User Query
    ↓
Phase 6 Advanced Retriever (Initial K=20, Capping=5)
    ↓
Top-Ranked Statutory Sources
    ↓
Legal Context Builder ([SOURCE 1] ... [SOURCE 5] formatting, MAX_CONTEXT_CHARS=20000)
    ↓
Grounded Prompt Construction (Mandatory 4-Section Output: Answer, Legal Basis, Sources, Important Note)
    ↓
OpenAI LLM Provider (gpt-5.6-terra primary / official openai SDK)
    ↓
Deterministic Citation & Safety Validator
    ↓
Structured Response with Full Provenance
```

### 2. Configuration Settings (.env)
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-terra
OPENAI_API_KEY=your-api-key-here
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1500
LLM_TIMEOUT_SECONDS=60
MAX_CONTEXT_CHARS=20000
```

### 3. Graceful Behavior Without API Key
If no API key is configured:
- The system successfully performs retrieval and reranking.
- Returns `status: "unconfigured_llm"` with HTTP 200.
- Does NOT fabricate answers.
- Formats structured 4-section fallback text.
- Preserves and delivers all retrieved statutory sources with page numbers and relevance scores.

---

## 🔗 API Endpoints

| Method | Endpoint            | Description                  | Status |
| :----- | :------------------ | :--------------------------- | :----- |
| `GET`  | `/`                 | Root — service status        | Operational |
| `GET`  | `/api/v1/health`    | Health check & LLM config    | Operational |
| `POST` | `/api/v1/query`     | Submit a legal question      | Operational (OpenAI Grounded RAG) |
| `GET`  | `/docs`             | Swagger UI documentation     | Operational |
| `GET`  | `/redoc`            | ReDoc documentation          | Operational |

### Request Format (`POST /api/v1/query`):
```json
{
  "query": "What is the punishment for theft?",
  "session_id": "optional-uuid"
}
```

---

## 📁 Project Structure

```
rag-service/
├── api/
│   ├── __init__.py
│   └── routes.py              # Health check and RAG query endpoints
├── schemas/
│   ├── __init__.py
│   ├── query.py               # QueryRequest schema
│   ├── response.py            # QueryResponse & SourceDocument schemas
│   ├── document.py            # DocumentPageRecord & IngestionManifest
│   ├── chunk.py               # LegalChunk & ChunkingManifest
│   ├── retrieval.py           # RetrievedChunk, RerankedChunk, AdvancedRetrievalResult
│   └── generation.py          # SourceReference & RAGResponse
├── ingestion/
│   ├── __init__.py
│   ├── document_loader.py     # PDF discovery & page extraction
│   ├── text_cleaner.py        # Conservative text cleaner
│   ├── metadata_extractor.py  # Canonical Indian statutory metadata
│   ├── ingestion_pipeline.py  # Page-level ingestion pipeline & CLI
│   ├── chunker.py             # Hybrid legal text chunker
│   └── chunking_pipeline.py   # Chunking pipeline & inspector CLI
├── embeddings/
│   ├── __init__.py            # Embedding package exports
│   └── embedding_model.py     # BAAI/bge-small-en-v1.5 wrapper & service
├── vectorstore/
│   ├── __init__.py            # Vectorstore package exports
│   ├── chroma_store.py        # ChromaDB store adapter
│   └── vectorstore_pipeline.py# Batch vectorization & rebuild pipeline
├── retrieval/
│   ├── __init__.py            # Retrieval package exports
│   ├── similarity_search.py   # Dense semantic retrieval
│   ├── query_processor.py     # Query validation and normalizer
│   ├── metadata_filter.py     # Deduplication & doc capping filter
│   ├── reranker.py            # BAAI/bge-reranker-base cross-encoder
│   ├── advanced_retriever.py  # 2-stage retrieval orchestrator
│   └── retrieval_pipeline.py  # CLI search & comparison evaluation tool
├── llm/
│   ├── __init__.py            # LLM provider exports
│   ├── base.py                # BaseLLMProvider & LLMResponse ABC
│   └── provider.py            # OpenAIProvider (Primary), GoogleGemini, Mock
├── prompts/
│   ├── __init__.py            # Prompt exports
│   └── prompts.py             # Grounded 4-section prompt templates
├── rag/
│   ├── __init__.py            # RAG package exports
│   ├── context_builder.py     # Context assembling (MAX_CONTEXT_CHARS=20000)
│   ├── answer_validator.py    # Deterministic citation & safety checks
│   └── rag_pipeline.py        # Complete RAG orchestrator
├── utils/
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings with OpenAI parameters
│   └── logger.py              # Structured logging
├── data/
│   ├── raw/                   # Source legal PDFs
│   └── processed/
│       ├── legal_documents.jsonl  # 1,386 page records
│       ├── ingestion_manifest.json# Ingestion summary
│       ├── legal_chunks.jsonl     # 4,184 legal chunks
│       ├── chunking_manifest.json # Chunking summary
│       └── embedding_manifest.json# Embedding & vectorstore summary
├── vector_store/
│   └── chroma_db/             # Persistent ChromaDB SQLite & vector index
├── main.py                    # FastAPI application entry
└── requirements.txt           # Python dependencies
```
