"""
NyayaSetu RAG Service — Application configuration.

Uses Pydantic Settings for type-safe environment variable management.
Configured with OpenAI as the primary production LLM provider.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "NyayaSetu RAG Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Chunking (Phase 4) ───────────────────────────────────────
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    # ── Embeddings & Vector Store (Phase 5) ──────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_BATCH_SIZE: int = 32
    VECTOR_DB_PATH: str = "vector_store/chroma_db"
    VECTOR_COLLECTION_NAME: str = "nyayasetu_legal_documents"

    # ── Advanced Retrieval & Reranking (Phase 6) ─────────────────
    INITIAL_RETRIEVAL_K: int = 20
    FINAL_RETRIEVAL_K: int = 5
    MAX_CHUNKS_PER_DOCUMENT: int = 5
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_BATCH_SIZE: int = 16

    # ── LLM & Answer Generation (Google Gemini Primary) ─────────
    LLM_PROVIDER: str = "gemini"  # Primary: "gemini" / "google" | Also supports: "openai", "mock"
    LLM_MODEL: str = "gemini-3.6-flash"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 3500
    LLM_TIMEOUT_SECONDS: float = 60.0
    MAX_CONTEXT_CHARS: int = 20000

    # ── Evaluation & Quality Assurance (Phase 8) ────────────────
    EVALUATION_TOP_K: int = 5
    EVALUATION_DATASET_PATH: str = "evaluation/test_questions.json"

    @property
    def effective_gemini_api_key(self) -> Optional[str]:
        """Resolve Gemini API key from GEMINI_API_KEY, GOOGLE_API_KEY, or LLM_API_KEY."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or self.LLM_API_KEY

    @property
    def effective_openai_api_key(self) -> Optional[str]:
        """Resolve OpenAI API key from OPENAI_API_KEY or LLM_API_KEY."""
        return self.OPENAI_API_KEY or self.LLM_API_KEY


# Singleton instance — import this everywhere
settings = Settings()
