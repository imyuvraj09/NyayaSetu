# NyayaSetu — Architecture

## System Overview

NyayaSetu is a three-tier application composed of:

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Frontend   │────▶│   Backend    │────▶│  RAG Service  │
│  React+Vite  │◀────│ Node+Express │◀────│ Python+FastAPI│
└─────────────┘     └──────────────┘     └───────────────┘
     :5173              :3000                  :8000
```

## Service Responsibilities

### Frontend (React + Vite)
- Chat-based user interface
- Displays AI responses with legal citations
- Communicates with the backend API gateway

### Backend (Node.js + Express)
- API gateway and request orchestration
- Authentication & session management (future)
- Proxies queries to the RAG service

### RAG Service (Python + FastAPI)
- Document ingestion and preprocessing
- Embedding generation and vector storage
- Semantic retrieval and context assembly
- LLM-powered answer generation with citations

## Data Flow

1. User submits a legal question via the frontend
2. Frontend sends the query to the backend API
3. Backend forwards the query to the RAG service
4. RAG service:
   a. Embeds the query
   b. Retrieves relevant document chunks from the vector store
   c. Constructs a prompt with retrieved context
   d. Sends the prompt to the LLM (Google Gemini)
   e. Extracts and formats legal citations
5. Response flows back through the backend to the frontend

## Technology Decisions

| Layer        | Technology                  | Rationale                              |
| ------------ | --------------------------- | -------------------------------------- |
| Frontend     | React + Vite                | Fast dev experience, component model   |
| Backend      | Node.js + Express           | Lightweight API gateway, JS ecosystem  |
| RAG Service  | Python + FastAPI            | ML/AI ecosystem, async support         |
| LLM          | Google Gemini (planned)     | Strong reasoning, free tier available  |
| Embeddings   | Sentence Transformers       | Open-source, high quality              |
| Vector Store | ChromaDB / FAISS (planned)  | Local-first, no external dependencies  |
