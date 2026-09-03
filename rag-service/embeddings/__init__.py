"""
NyayaSetu Embedding Package.

Provides lazy-loaded dense vector embedding services powered by SentenceTransformers.
"""

from embeddings.embedding_model import EmbeddingService, get_embedding_service

__all__ = ["EmbeddingService", "get_embedding_service"]
