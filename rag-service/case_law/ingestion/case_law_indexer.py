"""
Case-Law Indexer for NyayaSetu.

Orchestrates:
1. Loading verified Indian judgment documents
2. Paragraph-aware chunking preserving ratio decidendi and holdings
3. Embedding generation using BAAI/bge-small-en-v1.5
4. Vector storage in persistent ChromaDB collection 'nyayasetu_case_law'
5. Saving processed chunks to data/processed/case_law_chunks.jsonl
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from case_law.ingestion.case_law_chunker import CaseLawChunker
from case_law.ingestion.case_law_loader import CaseLawLoader
from embeddings.embedding_model import EmbeddingService
from schemas.case_law import CaseLawChunk
from utils.config import settings
from utils.logger import get_logger
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)

CASE_LAW_COLLECTION_NAME = "nyayasetu_case_law"


class CaseLawIndexer:
    """Embeds and indexes CaseLawChunk records into ChromaDB collection 'nyayasetu_case_law'."""

    def __init__(
        self,
        collection_name: str = CASE_LAW_COLLECTION_NAME,
        processed_dir: Optional[Path] = None,
    ) -> None:
        self.collection_name = collection_name
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.processed_dir = processed_dir or (base_dir / "data" / "processed")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_file = self.processed_dir / "case_law_chunks.jsonl"

        self.loader = CaseLawLoader()
        self.chunker = CaseLawChunker()
        self.embedder = EmbeddingService()
        self.chroma_store = ChromaStore(collection_name=self.collection_name)

    def run_indexing(self, reset: bool = False) -> Dict[str, Any]:
        """Execute case-law loading, chunking, embedding, and vector insertion."""
        logger.info("Starting Case-Law Indexing Pipeline (Collection: '%s')", self.collection_name)

        if reset:
            self.chroma_store.reset_collection()

        documents = self.loader.load_documents()
        if not documents:
            logger.warning("No verified case-law documents found to index.")
            return {"indexed_documents": 0, "indexed_chunks": 0}

        chunks = self.chunker.chunk_documents(documents)
        if not chunks:
            logger.warning("No case-law chunks generated.")
            return {"indexed_documents": len(documents), "indexed_chunks": 0}

        # Write chunks to JSONL
        with open(self.chunks_file, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(c.model_dump_json() + "\n")
        logger.info("Wrote %d CaseLawChunks to %s", len(chunks), self.chunks_file)

        # Generate embeddings
        texts = [c.text for c in chunks]
        logger.info("Generating dense embeddings for %d case-law passages...", len(texts))
        embeddings = self.embedder.embed_batch(texts)

        # Insert into ChromaDB
        existing_ids = self.chroma_store.get_existing_ids()
        new_chunks: List[CaseLawChunk] = []
        new_embeddings: List[List[float]] = []

        for c, emb in zip(chunks, embeddings):
            if c.chunk_id not in existing_ids:
                new_chunks.append(c)
                new_embeddings.append(emb)

        if new_chunks:
            logger.info("Inserting %d new case-law chunks into ChromaDB collection '%s'...", len(new_chunks), self.collection_name)
            self._insert_chunks_to_chroma(new_chunks, new_embeddings)
        else:
            logger.info("All %d case-law chunks already present in ChromaDB collection '%s'.", len(chunks), self.collection_name)

        total_in_collection = self.chroma_store.count()
        logger.info("Case-Law indexing complete. Total records in '%s': %d", self.collection_name, total_in_collection)

        return {
            "indexed_documents": len(documents),
            "indexed_chunks": len(chunks),
            "total_in_collection": total_in_collection,
            "collection_name": self.collection_name,
        }

    def _insert_chunks_to_chroma(self, chunks: List[CaseLawChunk], embeddings: List[List[float]]) -> None:
        """Batch-insert case-law chunks with rich metadata into ChromaDB."""
        ids = []
        documents = []
        metadatas = []

        for c in chunks:
            ids.append(c.chunk_id)
            documents.append(c.text)
            meta: Dict[str, Any] = {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "evidence_type": c.evidence_type.value,
                "case_name": c.case_name,
                "court": c.court,
                "court_level": c.court_level.value,
                "citation": c.citation,
                "judgment_date": c.judgment_date,
                "paragraph_number": str(c.paragraph_number),
                "passage_type": c.passage_type.value,
                "is_holding_or_ratio": bool(c.is_holding_or_ratio),
                "verified": bool(c.verified),
                "statutes_referred": json.dumps(c.statutes_referred),
                "sections_referred": json.dumps(c.sections_referred),
                "topics": json.dumps(c.topics),
                "documentName": f"{c.case_name} ({c.citation})",
                "actName": c.court,
                "document_name": c.case_name,
                "document_type": "Case Law",
                "source_filename": f"{c.document_id}.pdf",
                "page_numbers_json": json.dumps([int(c.paragraph_number) if c.paragraph_number.isdigit() else 1]),
            }
            metadatas.append(meta)

        # Batch insert to ChromaDB collection
        self.chroma_store.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )


if __name__ == "__main__":
    indexer = CaseLawIndexer()
    result = indexer.run_indexing(reset=True)
    print("Indexing Result:", result)
