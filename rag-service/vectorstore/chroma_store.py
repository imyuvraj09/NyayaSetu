"""
ChromaDB vector store adapter for NyayaSetu RAG Service.

Manages persistent on-disk embedding storage, collection lifecycle,
metadata serialization for ChromaDB compatibility, and semantic similarity search.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import chromadb
from chromadb.config import Settings as ChromaSettings

from schemas.chunk import LegalChunk
from schemas.retrieval import RetrievedChunk
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ChromaStore:
    """Persistent ChromaDB vector store wrapper for legal document chunks."""

    _client_cache: Dict[str, Any] = {}

    def __init__(
        self,
        persist_directory: Optional[Union[str, Path]] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.persist_directory = str(
            Path(persist_directory) if persist_directory else (base_dir / settings.VECTOR_DB_PATH)
        )
        self.collection_name = collection_name or settings.VECTOR_COLLECTION_NAME

        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Initializing ChromaDB client at '%s' (Collection: '%s')",
            self.persist_directory,
            self.collection_name,
        )

        if self.persist_directory in ChromaStore._client_cache:
            self._client = ChromaStore._client_cache[self.persist_directory]
        else:
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            ChromaStore._client_cache[self.persist_directory] = self._client

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "NyayaSetu Indian Legal Documents Collection", "hnsw:space": "cosine"},
        )

    @property
    def collection(self):
        """Return the underlying ChromaDB collection."""
        return self._collection

    def count(self) -> int:
        """Return the total number of vector records in the collection."""
        return self._collection.count()

    def get_existing_ids(self) -> Set[str]:
        """Fetch all existing chunk IDs in the collection for idempotency checking."""
        total = self.count()
        if total == 0:
            return set()

        # ChromaDB get() without where returns all IDs up to limit
        existing = self._collection.get(include=[])
        return set(existing.get("ids", []))

    def reset_collection(self) -> None:
        """Delete the current collection and recreate an empty one (Rebuild Mode)."""
        logger.warning(
            "Resetting ChromaDB collection '%s' at '%s'",
            self.collection_name,
            self.persist_directory,
        )
        try:
            self._client.delete_collection(name=self.collection_name)
        except Exception as err:
            logger.warning("Error deleting collection during reset: %s", err)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "NyayaSetu Indian Legal Documents Collection", "hnsw:space": "cosine"},
        )
        logger.info("Collection '%s' recreated successfully.", self.collection_name)

    def add_chunks_batch(
        self,
        chunks: List[LegalChunk],
        embeddings: List[List[float]],
    ) -> int:
        """Store a batch of chunks and their precomputed embeddings in ChromaDB.

        Args:
            chunks: List of LegalChunk data models.
            embeddings: Corresponding list of dense vector floats.

        Returns:
            Number of successfully inserted records.
        """
        if not chunks:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
            )

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Union[str, int, float, bool]]] = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)

            # ChromaDB supports str, int, float, bool in metadata
            first_page = chunk.page_numbers[0] if chunk.page_numbers else 1
            sec_num = str(chunk.metadata.get("section_number", ""))

            safe_meta: Dict[str, Union[str, int, float, bool]] = {
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "source_filename": chunk.source_filename,
                "document_type": chunk.document_type,
                "jurisdiction": chunk.jurisdiction,
                "language": chunk.language,
                "chunk_index": chunk.chunk_index,
                "character_count": chunk.character_count,
                "word_count": chunk.word_count,
                "page_numbers_json": json.dumps(chunk.page_numbers),
                "is_cross_page": bool(chunk.metadata.get("is_cross_page", False)),
                # Additional STEP 3 compatible metadata fields
                "documentName": chunk.document_name,
                "actName": chunk.document_name,
                "shortTitle": chunk.document_name,
                "legalDomain": chunk.document_type,
                "pageNumber": first_page,
                "sectionNumber": sec_num,
                "source_document_filename": chunk.source_filename,
            }
            metadatas.append(safe_meta)

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(ids)

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        """Query the vector database for the top-k most similar chunks.

        Args:
            query_embedding: L2-normalized query vector.
            top_k: Number of nearest neighbors to retrieve.

        Returns:
            List of validated RetrievedChunk instances ranked by score.
        """
        if self.count() == 0:
            logger.warning("Vector collection is empty. Query returned 0 results.")
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.count()),
            include=["documents", "metadatas", "distances"],
        )

        retrieved: List[RetrievedChunk] = []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
            # For cosine distance in ChromaDB: distance = 1 - cosine_similarity
            # Similarity = 1 - distance, clamped to [0.0, 1.0]
            similarity_score = max(0.0, min(1.0, 1.0 - dist))

            # Deserialize page_numbers from stored JSON
            page_numbers_raw = meta.get("page_numbers_json", "[]")
            try:
                page_numbers = json.loads(str(page_numbers_raw))
            except Exception:
                page_numbers = []

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_name=str(meta.get("document_name", "Unknown")),
                    document_type=str(meta.get("document_type", "Unknown")),
                    page_numbers=page_numbers,
                    text=text,
                    relevance_score=round(float(similarity_score), 4),
                    metadata=meta,
                )
            )

        return retrieved
