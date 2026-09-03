# NyayaSetu — API Documentation

Comprehensive API documentation for the NyayaSetu application gateway (Node.js + Express) and the AI Retrieval-Augmented Generation microservice (Python + FastAPI).

---

## 🏛️ Application Architecture

```
React Frontend (Port 5173)
        ↓
Node.js + Express Gateway (Port 3000)
        ↓
MongoDB Database (Port 27017)
        ↓
Python FastAPI RAG Service (Port 8000)
```

---

## 🚀 Backend Gateway API (Node.js + Express — Port 3000)

Base URL: `http://localhost:3000`

### 1. Health & Status Check

Retrieves the runtime status of the backend gateway, active environment, and MongoDB connection state.

- **Method**: `GET`
- **Endpoint**: `/api/health`
- **Headers**: `Accept: application/json`

#### Response (200 OK):
```json
{
  "success": true,
  "service": "nyayasetu-backend",
  "status": "healthy",
  "environment": "development",
  "timestamp": "2026-09-03T02:30:00.000Z",
  "database": {
    "connected": true,
    "status": "connected",
    "name": "nyayasetu"
  }
}
```

---

### 2. Create Chat Session

Initializes a new legal inquiry session.

- **Method**: `POST`
- **Endpoint**: `/api/chats`
- **Headers**: `Content-Type: application/json`

#### Request Body (Optional):
```json
{
  "title": "Theft Penalties under BNS"
}
```
*(If `title` is omitted, the title defaults to `"New Legal Conversation"` and will automatically update based on the user's first query).*

#### Response (201 Created):
```json
{
  "success": true,
  "message": "Chat session created successfully",
  "data": {
    "_id": "66d66e2a1b9d4f0012345678",
    "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
    "title": "Theft Penalties under BNS",
    "lastActivityAt": "2026-09-03T02:30:00.000Z",
    "createdAt": "2026-09-03T02:30:00.000Z",
    "updatedAt": "2026-09-03T02:30:00.000Z"
  }
}
```

---

### 3. List Chat Sessions

Lists recently active conversation sessions with pagination.

- **Method**: `GET`
- **Endpoint**: `/api/chats?page=1&limit=20`

#### Query Parameters:
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `page` | integer | `1` | Page number (min: 1) |
| `limit` | integer | `20` | Items per page (min: 1, max: 100) |

#### Response (200 OK):
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "_id": "66d66e2a1b9d4f0012345678",
        "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
        "title": "Theft Penalties under BNS",
        "lastActivityAt": "2026-09-03T02:30:15.000Z",
        "createdAt": "2026-09-03T02:30:00.000Z",
        "updatedAt": "2026-09-03T02:30:15.000Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20,
    "totalPages": 1
  }
}
```

---

### 4. Get Chat Session & History

Retrieves the metadata of a specific session alongside its chronologically ordered message history.

- **Method**: `GET`
- **Endpoint**: `/api/chats/:sessionId`

#### URL Parameters:
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `sessionId` | string | UUID v4 session identifier |

#### Response (200 OK):
```json
{
  "success": true,
  "data": {
    "session": {
      "_id": "66d66e2a1b9d4f0012345678",
      "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
      "title": "What is the punishment for theft?",
      "lastActivityAt": "2026-09-03T02:30:15.000Z",
      "createdAt": "2026-09-03T02:30:00.000Z"
    },
    "messages": [
      {
        "_id": "66d66e301b9d4f0012345679",
        "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
        "role": "user",
        "content": "What is the punishment for theft?",
        "sources": [],
        "createdAt": "2026-09-03T02:30:10.000Z"
      },
      {
        "_id": "66d66e351b9d4f001234567a",
        "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
        "role": "assistant",
        "content": "## Answer\n\nUnder Section 303 of the Bharatiya Nyaya Sanhita, 2023...",
        "sources": [
          {
            "sourceNumber": 1,
            "sourceLabel": "[SOURCE 1]",
            "documentName": "Bharatiya Nyaya Sanhita, 2023",
            "chunkId": "bns_2023_c0258",
            "pageNumbers": [80],
            "relevanceScore": 0.0886,
            "snippet": "Whoever commits theft shall be punished..."
          }
        ],
        "ragMetadata": {
          "model": "gpt-5.6-terra",
          "provider": "openai",
          "totalDuration": 1240,
          "warnings": [],
          "status": "success"
        },
        "createdAt": "2026-09-03T02:30:15.000Z"
      }
    ]
  }
}
```

---

### 5. Send Legal Query Message

Submits a natural language legal inquiry to the session.
1. Validates the query.
2. Verifies session existence.
3. Persists the user message.
4. Contacts the Python FastAPI RAG microservice.
5. Normalizes and validates the response.
6. Persists the assistant message with statutory source citations.
7. Updates session activity and returns the response.

- **Method**: `POST`
- **Endpoint**: `/api/chats/:sessionId/messages`
- **Headers**: `Content-Type: application/json`

#### Request Body:
```json
{
  "query": "What is the punishment for theft?"
}
```

#### Response (200 OK):
```json
{
  "success": true,
  "data": {
    "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
    "userMessage": {
      "_id": "66d66e301b9d4f0012345679",
      "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
      "role": "user",
      "content": "What is the punishment for theft?",
      "sources": [],
      "createdAt": "2026-09-03T02:30:10.000Z"
    },
    "message": {
      "_id": "66d66e351b9d4f001234567a",
      "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
      "role": "assistant",
      "content": "## Answer\n\nUnder Section 303 of the Bharatiya Nyaya Sanhita, 2023, theft is punishable with imprisonment of either description for a term which may extend to three years, or with fine, or with both [Source 1].\n\n## Legal Basis\n\nSection 303 provides that whoever intends to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, commits theft.\n\n## Sources\n[Source 1]\n\n## Important Note\nThis summary is provided for educational and informational purposes only based on retrieved statutory records and does not constitute formal legal advice.",
      "sources": [
        {
          "sourceNumber": 1,
          "sourceLabel": "[SOURCE 1]",
          "documentName": "Bharatiya Nyaya Sanhita, 2023",
          "chunkId": "bns_2023_c0258",
          "pageNumbers": [80],
          "relevanceScore": 0.0886,
          "snippet": "Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years..."
        }
      ],
      "ragMetadata": {
        "model": "gpt-5.6-terra",
        "provider": "openai",
        "totalDuration": 1240,
        "warnings": [],
        "status": "success"
      },
      "createdAt": "2026-09-03T02:30:15.000Z"
    }
  }
}
```

---

### 6. Delete Chat Session

Deletes a chat session and all associated messages.

- **Method**: `DELETE`
- **Endpoint**: `/api/chats/:sessionId`

#### Response (200 OK):
```json
{
  "success": true,
  "message": "Chat session and messages deleted successfully",
  "data": {
    "sessionId": "4b5d28b1-3e42-4916-8f27-6f81a7b1892c",
    "deletedMessagesCount": 2
  }
}
```

---

## ⚠️ Centralized Error Contract

All error responses return HTTP error status codes with a consistent, security-conscious JSON structure. Internal stack traces and database credentials are never exposed.

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description of error"
  }
}
```

### Standard Error Codes:
| Code | HTTP Status | Trigger Scenario |
| :--- | :--- | :--- |
| `VALIDATION_ERROR` | 400 | Missing query, empty query, query > 2000 chars, or invalid sessionId format |
| `MALFORMED_JSON` | 400 | Syntax error in request body JSON |
| `NOT_FOUND` | 404 | Session does not exist in database |
| `ROUTE_NOT_FOUND` | 404 | Endpoint URL does not exist |
| `RAG_RESPONSE_ERROR` | 502 | FastAPI returned unexpected or malformed payload |
| `RAG_SERVICE_UNAVAILABLE`| 503 | Python RAG service is offline or connection refused |
| `RAG_SERVICE_TIMEOUT` | 504 | Python RAG service exceeded timeout limit (`RAG_SERVICE_TIMEOUT_MS`) |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled internal server exception |

---

## 🐍 Python FastAPI RAG Microservice API (Port 8000)

Base URL: `http://localhost:8000`

Interactive Documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Primary Endpoints:
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service status |
| `GET` | `/api/v1/health` | Service health & active LLM provider (`openai`) |
| `POST` | `/api/v1/query` | Complete grounded RAG query pipeline (two-stage retrieval + LLM synthesis + citation verification) |
