"""
NyayaSetu Vector Database Pipeline.

Loads pre-chunked legal passages from data/processed/legal_chunks.jsonl,
computes dense vector representations via SentenceTransformers in batches,
and persists them into a local ChromaDB collection with complete metadata.

Supports:
- Idempotent incremental additions
- Complete rebuild mode (--rebuild)
- Collection inspection (--inspect)
- Progress tracking and manifest generation
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from embeddings.embedding_model import EmbeddingService, get_embedding_service
from schemas.chunk import LegalChunk
from schemas.retrieval import EmbeddingManifest
from utils.config import settings
from utils.logger import get_logger, setup_logging
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


def load_legal_chunks(chunks_file: Path) -> List[LegalChunk]:
    """Load and parse validated chunks from JSONL."""
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    chunks: List[LegalChunk] = []
    line_num = 0

    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                chunks.append(LegalChunk(**data))
            except Exception as err:
                logger.warning(
                    "Skipping malformed chunk at line %d in %s: %s",
                    line_num,
                    chunks_file.name,
                    err,
                )

    logger.info("Loaded %d legal chunk records from %s", len(chunks), chunks_file)
    return chunks


def run_vectorstore_pipeline(
    chunks_file: Optional[Union[str, Path]] = None,
    manifest_file: Optional[Union[str, Path]] = None,
    rebuild: bool = False,
    batch_size: Optional[int] = None,
) -> EmbeddingManifest:
    """Execute the vectorization and storage pipeline into ChromaDB.

    Args:
        chunks_file: Path to input legal_chunks.jsonl.
        manifest_file: Path to output embedding_manifest.json.
        rebuild: If True, resets collection and embeds all chunks cleanly.
        batch_size: Batch size for embedding and vector insertion.

    Returns:
        EmbeddingManifest detailing execution statistics.
    """
    base_dir = Path(__file__).resolve().parent.parent
    input_path = Path(chunks_file) if chunks_file else (base_dir / "data" / "processed" / "legal_chunks.jsonl")
    manifest_path = Path(manifest_file) if manifest_file else (base_dir / "data" / "processed" / "embedding_manifest.json")

    bs = batch_size or settings.EMBEDDING_BATCH_SIZE

    logger.info("=" * 60)
    logger.info("NyayaSetu Vector Database Pipeline")
    logger.info("Chunks input file   : %s", input_path)
    logger.info("Vector DB storage   : %s", settings.VECTOR_DB_PATH)
    logger.info("Vector collection   : %s", settings.VECTOR_COLLECTION_NAME)
    logger.info("Embedding model     : %s", settings.EMBEDDING_MODEL)
    logger.info("Batch size          : %d", bs)
    logger.info("Rebuild mode        : %s", rebuild)
    logger.info("=" * 60)

    # 1. Initialize store and embedding service
    store = ChromaStore()
    embedding_service = get_embedding_service()

    if rebuild:
        logger.info("Rebuild requested: clearing existing ChromaDB collection...")
        store.reset_collection()

    # 2. Load chunks
    chunks = load_legal_chunks(input_path)
    total_discovered = len(chunks)

    if total_discovered == 0:
        logger.warning("No chunks available for vectorization.")
        manifest = EmbeddingManifest(
            total_chunks_discovered=0,
            total_chunks_embedded=0,
            failed_chunks=0,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimension=embedding_service.dimension,
            batch_size=bs,
            vector_collection_name=settings.VECTOR_COLLECTION_NAME,
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest.model_dump(), mf, indent=2)
        return manifest

    # 3. Idempotency: filter out already embedded chunks if not rebuild
    if not rebuild:
        existing_ids = store.get_existing_ids()
        if existing_ids:
            logger.info("Found %d already indexed vector(s) in collection.", len(existing_ids))
            chunks_to_embed = [c for c in chunks if c.chunk_id not in existing_ids]
            logger.info("Chunks remaining to embed: %d (Skipping %d)", len(chunks_to_embed), len(chunks) - len(chunks_to_embed))
        else:
            chunks_to_embed = chunks
    else:
        chunks_to_embed = chunks

    # 4. Batch embedding and storage
    total_to_embed = len(chunks_to_embed)
    total_embedded = 0
    failed_chunks = 0

    if total_to_embed > 0:
        logger.info("Generating embeddings and inserting %d chunks in batches of %d...", total_to_embed, bs)

        for i in range(0, total_to_embed, bs):
            batch = chunks_to_embed[i : i + bs]
            batch_texts = [c.text for c in batch]

            try:
                # Generate embeddings for batch
                batch_embeddings = embedding_service.embed_batch(batch_texts, batch_size=bs)

                # Insert into ChromaDB
                store.add_chunks_batch(chunks=batch, embeddings=batch_embeddings)
                total_embedded += len(batch)

                pct = (total_embedded / total_to_embed) * 100
                logger.info(
                    "Progress: %d/%d chunks embedded and indexed (%.1f%%)",
                    total_embedded,
                    total_to_embed,
                    pct,
                )
            except Exception as batch_err:
                logger.error("Error processing batch %d-%d: %s", i, i + len(batch), batch_err, exc_info=True)
                failed_chunks += len(batch)

    # 5. Manifest creation
    current_collection_count = store.count()
    dimension = embedding_service.dimension

    manifest = EmbeddingManifest(
        total_chunks_discovered=total_discovered,
        total_chunks_embedded=current_collection_count,
        failed_chunks=failed_chunks,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimension=dimension,
        batch_size=bs,
        vector_collection_name=settings.VECTOR_COLLECTION_NAME,
        processing_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest.model_dump(), mf, indent=2)

    logger.info("=" * 60)
    logger.info("Vector Database Pipeline Summary:")
    logger.info("  Chunks discovered   : %d", manifest.total_chunks_discovered)
    logger.info("  Total vectors in DB : %d", manifest.total_chunks_embedded)
    logger.info("  Failed chunks       : %d", manifest.failed_chunks)
    logger.info("  Embedding model     : %s", manifest.embedding_model)
    logger.info("  Vector dimension    : %d", manifest.embedding_dimension)
    logger.info("  Manifest saved to   : %s", manifest_path)
    logger.info("=" * 60)

    return manifest


def inspect_vectorstore() -> None:
    """Inspect the ChromaDB collection status, vector count, and sample metadata."""
    store = ChromaStore()
    embedding_service = get_embedding_service()

    count = store.count()
    dimension = embedding_service.dimension

    print("=" * 80)
    print("NYAYASETU CHROMADB VECTOR DATABASE INSPECTION")
    print("=" * 80)
    print(f"  Storage Location     : {store.persist_directory}")
    print(f"  Collection Name      : {store.collection_name}")
    print(f"  Total Vectors Stored : {count}")
    print(f"  Embedding Model      : {settings.EMBEDDING_MODEL}")
    print(f"  Embedding Dimension  : {dimension}")
    print("-" * 80)

    if count > 0:
        # Sample one record from collection
        sample = store.collection.peek(limit=1)
        if sample and sample.get("ids") and sample["ids"]:
            print("SAMPLE RECORD IN COLLECTION:")
            print(f"  Chunk ID  : {sample['ids'][0]}")
            if sample.get("metadatas") and sample["metadatas"]:
                meta = sample["metadatas"][0]
                print(f"  Document  : {meta.get('document_name')}")
                print(f"  Type      : {meta.get('document_type')}")
                print(f"  Pages     : {meta.get('page_numbers_json')}")
            if sample.get("documents") and sample["documents"]:
                doc_snippet = sample["documents"][0][:180].replace("\n", " ")
                print(f"  Text      : \"{doc_snippet}...\"")
    else:
        print("  Notice: Collection is currently empty. Run vectorstore_pipeline to populate.")

    print("=" * 80)


def main() -> None:
    """CLI entry point for vectorstore pipeline and database inspection."""
    parser = argparse.ArgumentParser(
        description="NyayaSetu Vector Database Pipeline"
    )
    parser.add_argument(
        "--chunks-file",
        type=str,
        default=None,
        help="Path to legal_chunks.jsonl input file",
    )
    parser.add_argument(
        "--manifest-file",
        type=str,
        default=None,
        help="Path to embedding_manifest.json output file",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Batch size for embedding generation (default: {settings.EMBEDDING_BATCH_SIZE})",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Reset and rebuild the collection from scratch without duplicates",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect vector collection status, dimension, and sample metadata",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    if args.inspect:
        inspect_vectorstore()
        return

    try:
        manifest = run_vectorstore_pipeline(
            chunks_file=args.chunks_file,
            manifest_file=args.manifest_file,
            rebuild=args.rebuild,
            batch_size=args.batch_size,
        )
        if manifest.failed_chunks > 0 and manifest.total_chunks_embedded == 0:
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        logger.critical("Vectorstore pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
