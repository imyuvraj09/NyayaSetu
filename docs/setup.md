# NyayaSetu — Setup Guide

## Prerequisites

- **Node.js** ≥ 18.x (recommended: 20.x LTS)
- **Python** ≥ 3.10 (recommended: 3.11)
- **npm** ≥ 9.x
- **pip** ≥ 23.x
- **Docker** & **Docker Compose** (optional, for containerised deployment)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd NyayaSetu
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at **http://localhost:5173**.

### 3. Backend Setup

```bash
cd backend
cp .env.example .env
npm install
npm run dev
```

The backend runs at **http://localhost:3000**.

### 4. RAG Service Setup

```bash
cd rag-service
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The RAG service runs at **http://localhost:8000**.

### 5. Verify All Services

| Service     | Health Check URL                       |
| ----------- | -------------------------------------- |
| Frontend    | http://localhost:5173                  |
| Backend     | http://localhost:3000/api/health       |
| RAG Service | http://localhost:8000/health           |

## Docker Setup (Optional)

```bash
docker-compose up --build
```

## Environment Variables

Copy `.env.example` files in each service directory to `.env` and configure as needed. See each service's `.env.example` for available variables.
