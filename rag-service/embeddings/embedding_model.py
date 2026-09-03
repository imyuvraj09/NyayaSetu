"""
SentenceTransformers embedding model wrapper for NyayaSetu RAG Service.

Provides lazy-loading, singleton caching, GPU autodetection, batch encoding,
and L2-normalized vector representations using BAAI/bge-small-en-v1.5 by default.
"""

from typing import List, Optional, Union
import numpy as np

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Global singleton cache for the loaded model
_MODEL_INSTANCE: Optional["SentenceTransformer"] = None


def get_device() -> str:
    """Detect available hardware accelerator, falling back safely to CPU."""
    try:
        import torch
        if torch.cuda.is_available():
            dev = "cuda"
            logger.info("CUDA GPU acceleration detected: %s", torch.cuda.get_device_name(0))
            return dev
    except Exception:
        pass
    return "cpu"


class EmbeddingService:
    """Service class for generating dense vector embeddings from text."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or get_device()
        self._dimension: Optional[int] = None

    def _load_model(self):
        """Lazily load and cache the SentenceTransformer model instance."""
        global _MODEL_INSTANCE
        if _MODEL_INSTANCE is None:
            logger.info(
                "Loading embedding model '%s' on device '%s'...",
                self.model_name,
                self.device,
            )
            from sentence_transformers import SentenceTransformer

            _MODEL_INSTANCE = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
            # Determine vector dimension from model's output configuration
            dim = _MODEL_INSTANCE.get_sentence_embedding_dimension()
            logger.info(
                "Embedding model '%s' loaded successfully. Vector dimension: %d",
                self.model_name,
                dim,
            )

        return _MODEL_INSTANCE

    @property
    def dimension(self) -> int:
        """Return the vector embedding dimensionality."""
        if self._dimension is None:
            model = self._load_model()
            self._dimension = model.get_sentence_embedding_dimension()
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate a normalized embedding vector for a single text string."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")

        model = self._load_model()
        vector = model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vector.tolist()

    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """Generate normalized embedding vectors for a batch of text strings.

        Args:
            texts: List of text passages to embed.
            batch_size: Number of items per forward pass (defaults to settings.EMBEDDING_BATCH_SIZE).
            show_progress: Whether to display sentence_transformers progress bar.

        Returns:
            List of float vector lists corresponding to each input text.
        """
        if not texts:
            return []

        model = self._load_model()
        bs = batch_size or settings.EMBEDDING_BATCH_SIZE

        vectors = model.encode(
            texts,
            batch_size=bs,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return vectors.tolist()


# Convenience singleton accessor
def get_embedding_service(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
) -> EmbeddingService:
    """Factory helper returning an EmbeddingService instance."""
    return EmbeddingService(model_name=model_name, device=device)
