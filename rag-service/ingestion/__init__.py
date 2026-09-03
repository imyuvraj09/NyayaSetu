"""
NyayaSetu Legal Document Ingestion & Chunking Package.

Provides modules for discovering, extracting, conservatively cleaning,
serializing, and legally chunking Indian legal documents.
"""

from ingestion.chunker import LegalChunker, is_likely_heading, split_into_sentences
from ingestion.chunking_pipeline import inspect_chunks, run_chunking_pipeline
from ingestion.document_loader import (
    DocumentLoadResult,
    RawPageExtract,
    discover_pdf_files,
    load_all_pdfs,
    load_pdf_pages,
)
from ingestion.ingestion_pipeline import run_ingestion
from ingestion.metadata_extractor import (
    KNOWN_LEGAL_DOCUMENTS,
    extract_metadata_for_file,
)
from ingestion.text_cleaner import clean_text

__all__ = [
    "run_ingestion",
    "discover_pdf_files",
    "load_pdf_pages",
    "load_all_pdfs",
    "clean_text",
    "extract_metadata_for_file",
    "KNOWN_LEGAL_DOCUMENTS",
    "DocumentLoadResult",
    "RawPageExtract",
    "LegalChunker",
    "run_chunking_pipeline",
    "inspect_chunks",
    "is_likely_heading",
    "split_into_sentences",
]
