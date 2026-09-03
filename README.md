# NyayaSetu ⚖️

**An AI-Powered RAG-Based Legal Assistant for Accessible and Explainable Legal Knowledge in India**

> B.Tech Final Year Project

---

## Overview

NyayaSetu is an AI-powered legal assistant that uses Retrieval-Augmented Generation (RAG) to provide accurate, explainable, and citation-backed answers to legal questions based on Indian law. The system retrieves relevant legal documents and generates contextual responses with proper legal citations.

## Architecture

```
NyayaSetu/
├── frontend/          # React + Vite — User Interface
├── backend/           # Node.js + Express — API Gateway
├── rag-service/       # Python + FastAPI — RAG Pipeline
├── evaluation/        # RAG evaluation scripts & test data
├── docker/            # Dockerfiles for all services
├── docs/              # Project documentation
└── docker-compose.yml
```

## Tech Stack

| Layer        | Technology              |
| ------------ | ----------------------- |
| Frontend     | React 19, Vite 6        |
| Backend      | Node.js 20, Express 4   |
| RAG Service  | Python 3.11, FastAPI    |
| LLM          | Google Gemini (planned) |
| Embeddings   | Sentence Transformers   |
| Vector Store | ChromaDB / FAISS        |
| Deployment   | Docker Compose          |

## Quick Start

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && npm install && npm run dev

# RAG Service
cd rag-service
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

See [docs/setup.md](docs/setup.md) for detailed instructions.

## Documentation

- [Architecture](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [API Reference](docs/api.md)

## Project Status

🟢 Phase 1 — Project scaffolding & initial structure (complete)
🔲 Phase 2 — Data ingestion pipeline
🔲 Phase 3 — Embedding generation & vector store
🔲 Phase 4 — RAG pipeline implementation
🔲 Phase 5 — Frontend chat UI
🔲 Phase 6 — Evaluation & testing
🔲 Phase 7 — Deployment & documentation

## License

MIT
