"""
NyayaSetu Vector Store Package.

Provides local persistent ChromaDB storage and similarity search for legal document chunks.
"""

from vectorstore.chroma_store import ChromaStore

__all__ = ["ChromaStore"]
