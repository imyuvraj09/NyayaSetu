"""
NyayaSetu Legal Text Chunking Pipeline.

Orchestrates:
1. Ingestion of page-level records from data/processed/legal_documents.jsonl.
2. Grouping and ordering of pages by document.
3. Hybrid, legal-aware text chunking with cross-page continuity.
4. Comprehensive quality validation (non-empty, unique IDs, complete metadata).
5. Deterministic serialization to data/processed/legal_chunks.jsonl.
6. Execution summary generation in data/processed/chunking_manifest.json.
7. Representative chunk inspection CLI utility.

Can be run standalone via CLI:
    python -m ingestion.chunking_pipeline
    python -m ingestion.chunking_pipeline --inspect 5
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ingestion.chunker import LegalChunker
from schemas.chunk import ChunkingManifest, LegalChunk
from schemas.document import DocumentPageRecord
from utils.config import settings
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def load_page_records(input_path: Path) -> List[DocumentPageRecord]:
    """Load and parse page-level records from JSONL."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    records: List[DocumentPageRecord] = []
    line_num = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(DocumentPageRecord(**data))
            except Exception as err:
                logger.warning(
                    "Skipping malformed record at line %d in %s: %s",
                    line_num,
                    input_path.name,
                    err,
                )

    logger.info("Loaded %d page records from %s", len(records), input_path)
    return records


def validate_chunk_quality(chunks: List[LegalChunk]) -> List[str]:
    """Validate that generated chunks meet strict quality standards.

    Returns:
        List of validation error strings. If empty, all checks passed.
    """
    errors: List[str] = []
    seen_ids: set = set()

    for idx, chunk in enumerate(chunks):
        # 1. Non-empty text
        if not chunk.text or not chunk.text.strip():
            errors.append(f"Chunk at index {idx} ({chunk.chunk_id}) is empty or whitespace.")

        # 2. Document identification
        if not chunk.document_id:
            errors.append(f"Chunk at index {idx} ({chunk.chunk_id}) lacks document_id.")
        if not chunk.document_name:
            errors.append(f"Chunk at index {idx} ({chunk.chunk_id}) lacks document_name.")

        # 3. Source traceability
        if not chunk.page_numbers:
            errors.append(f"Chunk at index {idx} ({chunk.chunk_id}) has no page_numbers.")

        # 4. ID uniqueness
        if chunk.chunk_id in seen_ids:
            errors.append(f"Duplicate chunk_id detected: {chunk.chunk_id}")
        seen_ids.add(chunk.chunk_id)

    return errors


def run_chunking_pipeline(
    input_file: Optional[Union[str, Path]] = None,
    output_file: Optional[Union[str, Path]] = None,
    manifest_file: Optional[Union[str, Path]] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> ChunkingManifest:
    """Execute the end-to-end legal document chunking pipeline.

    Args:
        input_file: Path to input JSONL with page records. Defaults to data/processed/legal_documents.jsonl.
        output_file: Path to output JSONL for chunks. Defaults to data/processed/legal_chunks.jsonl.
        manifest_file: Path to output manifest JSON. Defaults to data/processed/chunking_manifest.json.
        chunk_size: Target character count per chunk. Defaults to settings.CHUNK_SIZE.
        chunk_overlap: Overlap character count. Defaults to settings.CHUNK_OVERLAP.

    Returns:
        ChunkingManifest detailing execution statistics.
    """
    base_dir = Path(__file__).resolve().parent.parent
    input_path = Path(input_file) if input_file else (base_dir / "data" / "processed" / "legal_documents.jsonl")
    output_path = Path(output_file) if output_file else (base_dir / "data" / "processed" / "legal_chunks.jsonl")
    manifest_path = Path(manifest_file) if manifest_file else (base_dir / "data" / "processed" / "chunking_manifest.json")

    target_chunk_size = chunk_size or settings.CHUNK_SIZE
    target_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    logger.info("=" * 60)
    logger.info("NyayaSetu Legal Text Chunking Pipeline")
    logger.info("Input source     : %s", input_path)
    logger.info("Output target    : %s", output_path)
    logger.info("Target chunk size: %d chars", target_chunk_size)
    logger.info("Target overlap   : %d chars", target_overlap)
    logger.info("=" * 60)

    if not input_path.exists():
        logger.error("Input file %s does not exist. Run document ingestion first.", input_path)
        manifest = ChunkingManifest(
            total_documents=0,
            total_input_pages=0,
            total_chunks=0,
            average_chunk_size=0.0,
            minimum_chunk_size=0,
            maximum_chunk_size=0,
            documents_processed=[],
            failed_documents=[{"error": f"Input file not found: {input_path}"}],
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            chunk_size_configuration=target_chunk_size,
            overlap_configuration=target_overlap,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest.model_dump(), mf, indent=2)
        return manifest

    # Step 1: Load page records
    page_records = load_page_records(input_path)

    if not page_records:
        logger.warning("No page records found in %s.", input_path)
        manifest = ChunkingManifest(
            total_documents=0,
            total_input_pages=0,
            total_chunks=0,
            average_chunk_size=0.0,
            minimum_chunk_size=0,
            maximum_chunk_size=0,
            documents_processed=[],
            failed_documents=[],
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            chunk_size_configuration=target_chunk_size,
            overlap_configuration=target_overlap,
        )
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest.model_dump(), mf, indent=2)
        return manifest

    # Step 2: Group records by document
    docs_map = defaultdict(list)
    for pr in page_records:
        key = pr.source_filename
        docs_map[key].append(pr)

    logger.info("Identified %d unique document(s) across %d pages", len(docs_map), len(page_records))

    # Step 3: Initialize chunker
    chunker = LegalChunker(
        chunk_size=target_chunk_size,
        chunk_overlap=target_overlap,
    )

    all_chunks: List[LegalChunk] = []
    processed_doc_names: List[str] = []
    failed_docs = []

    for filename, pages in docs_map.items():
        doc_name = pages[0].document_name
        logger.info("Chunking document: %s (%d pages)", doc_name, len(pages))

        try:
            doc_chunks = chunker.chunk_document(pages)
            all_chunks.extend(doc_chunks)
            processed_doc_names.append(doc_name)
        except Exception as exc:
            logger.error("Failed to chunk document '%s': %s", doc_name, exc, exc_info=True)
            failed_docs.append({"filename": filename, "document_name": doc_name, "error": str(exc)})

    # Step 4: Quality validation
    validation_errors = validate_chunk_quality(all_chunks)
    if validation_errors:
        logger.error("Chunk quality validation found %d error(s):", len(validation_errors))
        for err in validation_errors[:10]:
            logger.error("  - %s", err)
        if len(validation_errors) > 10:
            logger.error("  ... and %d more errors", len(validation_errors) - 10)
        raise ValueError(f"Chunk quality validation failed with {len(validation_errors)} error(s).")

    # Step 5: Atomic write to output JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output_path = output_path.with_suffix(".tmp")

    try:
        with open(temp_output_path, "w", encoding="utf-8") as f_out:
            for chunk in all_chunks:
                f_out.write(json.dumps(chunk.model_dump()) + "\n")

        if temp_output_path.exists():
            if output_path.exists():
                output_path.unlink()
            temp_output_path.rename(output_path)
    except Exception as write_err:
        logger.error("Failed writing chunk output: %s", write_err, exc_info=True)
        if temp_output_path.exists():
            temp_output_path.unlink()
        raise

    # Step 6: Compute statistics
    chunk_lengths = [c.character_count for c in all_chunks]
    avg_len = float(sum(chunk_lengths) / len(chunk_lengths)) if chunk_lengths else 0.0
    min_len = min(chunk_lengths) if chunk_lengths else 0
    max_len = max(chunk_lengths) if chunk_lengths else 0

    manifest = ChunkingManifest(
        total_documents=len(docs_map),
        total_input_pages=len(page_records),
        total_chunks=len(all_chunks),
        average_chunk_size=round(avg_len, 2),
        minimum_chunk_size=min_len,
        maximum_chunk_size=max_len,
        documents_processed=processed_doc_names,
        failed_documents=failed_docs,
        processing_timestamp=datetime.now(timezone.utc).isoformat(),
        chunk_size_configuration=target_chunk_size,
        overlap_configuration=target_overlap,
    )

    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest.model_dump(), mf, indent=2)

    logger.info("=" * 60)
    logger.info("Chunking Pipeline Summary:")
    logger.info("  Documents processed   : %d", manifest.total_documents)
    logger.info("  Input pages evaluated : %d", manifest.total_input_pages)
    logger.info("  Total chunks produced : %d", manifest.total_chunks)
    logger.info("  Average chunk size    : %.1f chars", manifest.average_chunk_size)
    logger.info("  Min / Max chunk size  : %d / %d chars", manifest.minimum_chunk_size, manifest.maximum_chunk_size)
    logger.info("  Output saved to       : %s", output_path)
    logger.info("  Manifest saved to     : %s", manifest_path)
    logger.info("=" * 60)

    return manifest


def inspect_chunks(
    chunks_path: Optional[Union[str, Path]] = None,
    sample_count: int = 5,
) -> None:
    """Inspect sample generated chunks across different documents."""
    base_dir = Path(__file__).resolve().parent.parent
    path = Path(chunks_path) if chunks_path else (base_dir / "data" / "processed" / "legal_chunks.jsonl")

    if not path.exists():
        print(f"Error: Chunks file not found at {path}")
        return

    chunks_by_doc = defaultdict(list)
    total_loaded = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            chunk = LegalChunk(**data)
            chunks_by_doc[chunk.document_name].append(chunk)
            total_loaded += 1

    print("=" * 80)
    print(f"NYAYASETU LEGAL CHUNKS INSPECTION (Total Chunks Available: {total_loaded})")
    print(f"Sampling up to {sample_count} chunk(s) per document")
    print("=" * 80)

    for doc_name, doc_chunks in chunks_by_doc.items():
        print(f"\nDOCUMENT: {doc_name} (Total: {len(doc_chunks)} chunks)")
        print("-" * 80)

        # Pick representative samples: first, middle, last
        indices = [0]
        if len(doc_chunks) > 2:
            indices.append(len(doc_chunks) // 2)
        if len(doc_chunks) > 1:
            indices.append(len(doc_chunks) - 1)

        samples = [doc_chunks[i] for i in indices[:sample_count]]

        for sample in samples:
            snippet = sample.text[:180].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
            safe_doc_name = sample.document_name.encode("ascii", errors="replace").decode("ascii")
            print(f"  ID       : {sample.chunk_id}")
            print(f"  Pages    : {sample.page_numbers} (Cross-page: {sample.metadata.get('is_cross_page', False)})")
            print(f"  Size     : {sample.character_count} chars ({sample.word_count} words)")
            if sample.metadata.get("headings"):
                safe_headings = [h.encode("ascii", errors="replace").decode("ascii") for h in sample.metadata["headings"]]
                print(f"  Headings : {safe_headings}")
            print(f"  Snippet  : \"{snippet}...\"")
            print()

    print("=" * 80)


def main() -> None:
    """CLI entry point for chunking pipeline and sample inspection."""
    parser = argparse.ArgumentParser(
        description="NyayaSetu Legal Text Chunking Pipeline"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to legal_documents.jsonl input file",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Path to legal_chunks.jsonl output file",
    )
    parser.add_argument(
        "--manifest-file",
        type=str,
        default=None,
        help="Path to chunking_manifest.json output file",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help=f"Target chunk size in characters (default: {settings.CHUNK_SIZE})",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help=f"Chunk overlap in characters (default: {settings.CHUNK_OVERLAP})",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--inspect",
        type=int,
        nargs="?",
        const=3,
        default=None,
        help="Inspect sample chunks (optional count per doc, default: 3)",
    )

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    # If --inspect requested, run inspector and exit
    if args.inspect is not None:
        inspect_chunks(
            chunks_path=args.output_file,
            sample_count=args.inspect,
        )
        return

    try:
        manifest = run_chunking_pipeline(
            input_file=args.input_file,
            output_file=args.output_file,
            manifest_file=args.manifest_file,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        if manifest.failed_documents and not manifest.documents_processed:
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        logger.critical("Chunking pipeline execution failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
