"""
NyayaSetu Legal Document Ingestion Pipeline.

Orchestrates:
1. Discovery of raw Indian legal PDF statutes.
2. Metadata inference and canonical mapping.
3. Page-by-page text extraction.
4. Conservative text cleaning.
5. Writing page-level records to data/processed/legal_documents.jsonl.
6. Generating an ingestion manifest summary in data/processed/ingestion_manifest.json.

Can be run standalone via CLI:
    python -m ingestion.ingestion_pipeline
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from ingestion.document_loader import discover_pdf_files, load_pdf_pages
from ingestion.metadata_extractor import extract_metadata_for_file
from ingestion.text_cleaner import clean_text
from schemas.document import DocumentPageRecord, IngestionManifest
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def run_ingestion(
    raw_dir: Optional[Union[str, Path]] = None,
    processed_dir: Optional[Union[str, Path]] = None,
    output_filename: str = "legal_documents.jsonl",
    manifest_filename: str = "ingestion_manifest.json",
) -> IngestionManifest:
    """Execute the end-to-end legal document ingestion pipeline.

    Args:
        raw_dir: Path to directory containing raw PDFs. Defaults to rag-service/data/raw.
        processed_dir: Path to directory for processed outputs. Defaults to rag-service/data/processed.
        output_filename: Name of the output JSONL file.
        manifest_filename: Name of the ingestion manifest JSON file.

    Returns:
        IngestionManifest detailing counts and results of the pipeline run.
    """
    base_dir = Path(__file__).resolve().parent.parent
    raw_path = Path(raw_dir) if raw_dir else (base_dir / "data" / "raw")
    processed_path = Path(processed_dir) if processed_dir else (base_dir / "data" / "processed")

    processed_path.mkdir(parents=True, exist_ok=True)
    output_file = processed_path / output_filename
    manifest_file = processed_path / manifest_filename

    logger.info("=" * 60)
    logger.info("NyayaSetu Document Ingestion Pipeline")
    logger.info("Raw documents source : %s", raw_path)
    logger.info("Processed destination : %s", processed_path)
    logger.info("=" * 60)

    # 1. Discover PDFs
    pdf_files = discover_pdf_files(raw_path)

    if not pdf_files:
        logger.warning(
            "No PDF documents discovered in %s. Ingestion finished with 0 documents.",
            raw_path,
        )
        empty_manifest = IngestionManifest(
            total_files_discovered=0,
            successfully_processed_files=0,
            failed_files=0,
            total_pages=0,
            pages_containing_text=0,
            empty_pages=0,
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            processed_documents=[],
            failed_documents=[],
        )
        # Write empty manifest for traceability
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(empty_manifest.model_dump(), mf, indent=2)
        return empty_manifest

    # 2. Process each discovered file
    total_pages_count = 0
    pages_with_text_count = 0
    empty_pages_count = 0
    processed_docs: List[str] = []
    failed_docs = []

    # Temporary write to ensure atomic/non-duplicated replacement
    temp_output_file = processed_path / f"{output_filename}.tmp"

    try:
        with open(temp_output_file, "w", encoding="utf-8") as out_f:
            for pdf_path in pdf_files:
                logger.info("Processing document: %s", pdf_path.name)
                metadata = extract_metadata_for_file(pdf_path)

                load_result = load_pdf_pages(pdf_path)

                if not load_result.is_success:
                    logger.error(
                        "Skipping %s due to fatal loading error: %s",
                        pdf_path.name,
                        load_result.error_message,
                    )
                    failed_docs.append({
                        "filename": pdf_path.name,
                        "error": load_result.error_message or "Unknown error",
                    })
                    continue

                doc_slug = metadata.get("slug", pdf_path.stem.lower())
                doc_name = metadata.get("document_name", pdf_path.stem)
                doc_type = metadata.get("document_type", "Unknown")
                jurisdiction = metadata.get("jurisdiction", "India")
                language = metadata.get("language", "English")

                for page in load_result.pages:
                    total_pages_count += 1
                    cleaned = clean_text(page.raw_text)
                    has_text = len(cleaned) > 0

                    if has_text:
                        pages_with_text_count += 1
                    else:
                        empty_pages_count += 1

                    page_record = DocumentPageRecord(
                        document_id=f"{doc_slug}_p{page.page_number}",
                        document_name=doc_name,
                        source_filename=pdf_path.name,
                        source_path=f"data/raw/{pdf_path.name}",
                        page_number=page.page_number,
                        document_type=doc_type,
                        jurisdiction=jurisdiction,
                        language=language,
                        extracted_at=datetime.now(timezone.utc).isoformat(),
                        text=cleaned,
                        character_count=len(cleaned),
                        has_text=has_text,
                    )

                    out_f.write(json.dumps(page_record.model_dump()) + "\n")

                processed_docs.append(pdf_path.name)
                logger.info(
                    "Completed %s (%d pages)",
                    pdf_path.name,
                    len(load_result.pages),
                )

        # Atomically replace final file
        if temp_output_file.exists():
            if output_file.exists():
                output_file.unlink()
            temp_output_file.rename(output_file)

    except Exception as exc:
        logger.error("Fatal error during pipeline processing: %s", exc, exc_info=True)
        if temp_output_file.exists():
            temp_output_file.unlink()
        raise

    manifest = IngestionManifest(
        total_files_discovered=len(pdf_files),
        successfully_processed_files=len(processed_docs),
        failed_files=len(failed_docs),
        total_pages=total_pages_count,
        pages_containing_text=pages_with_text_count,
        empty_pages=empty_pages_count,
        processing_timestamp=datetime.now(timezone.utc).isoformat(),
        processed_documents=processed_docs,
        failed_documents=failed_docs,
    )

    with open(manifest_file, "w", encoding="utf-8") as mf:
        json.dump(manifest.model_dump(), mf, indent=2)

    logger.info("=" * 60)
    logger.info("Ingestion Pipeline Summary:")
    logger.info("  Files discovered      : %d", manifest.total_files_discovered)
    logger.info("  Files processed       : %d", manifest.successfully_processed_files)
    logger.info("  Files failed          : %d", manifest.failed_files)
    logger.info("  Total pages           : %d", manifest.total_pages)
    logger.info("  Pages with text       : %d", manifest.pages_containing_text)
    logger.info("  Empty/scanned pages   : %d", manifest.empty_pages)
    logger.info("  Output JSONL saved to : %s", output_file)
    logger.info("  Manifest saved to     : %s", manifest_file)
    logger.info("=" * 60)

    return manifest


def main() -> None:
    """CLI entry point for manual pipeline execution."""
    parser = argparse.ArgumentParser(
        description="NyayaSetu Legal Document Ingestion Pipeline"
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Path to directory containing raw PDFs (default: data/raw)",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default=None,
        help="Path to directory for processed outputs (default: data/processed)",
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

    try:
        manifest = run_ingestion(
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
        )
        if manifest.failed_files > 0 and manifest.successfully_processed_files == 0:
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        logger.critical("Ingestion pipeline failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
