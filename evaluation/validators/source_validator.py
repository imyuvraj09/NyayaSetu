"""
Source integrity validator for NyayaSetu quality assurance.

Validates that returned source documents have complete metadata, verified page numbers,
unique chunk identifiers, and map directly to known canonical legal statutes in ChromaDB.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ingestion.metadata_extractor import KNOWN_LEGAL_DOCUMENTS


CANONICAL_DOCUMENT_NAMES: Set[str] = {
    meta["document_name"] for meta in KNOWN_LEGAL_DOCUMENTS.values()
}


@dataclass
class SourceValidationReport:
    """Outcome of source metadata and integrity checking."""

    is_valid: bool
    total_sources_checked: int
    missing_chunk_ids: int = 0
    missing_document_names: int = 0
    missing_page_metadata: int = 0
    unknown_documents: List[str] = field(default_factory=list)
    duplicate_chunk_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SourceValidator:
    """Validates metadata completeness and provenance of returned source chunks."""

    def __init__(self, chroma_store: Optional[Any] = None) -> None:
        self.chroma_store = chroma_store

    def validate_sources(self, sources: List[Any]) -> SourceValidationReport:
        """Verify metadata integrity and authenticity for a list of source objects.

        Args:
            sources: List of source objects (SourceDocument, SourceReference, or dicts).

        Returns:
            SourceValidationReport detailing metadata validity.
        """
        if not sources:
            return SourceValidationReport(
                is_valid=True,
                total_sources_checked=0,
                warnings=["Source list is empty."],
            )

        missing_ids = 0
        missing_names = 0
        missing_pages = 0
        unknown_docs: List[str] = []
        seen_ids: Set[str] = set()
        duplicate_ids: List[str] = []
        warnings: List[str] = []

        for idx, src in enumerate(sources):
            # Extract attributes from dict or Pydantic model
            chunk_id = getattr(src, "chunk_id", None) or (src.get("chunk_id") if isinstance(src, dict) else None)
            doc_name = getattr(src, "document_name", None) or (src.get("document_name") if isinstance(src, dict) else None)
            pages = (
                getattr(src, "page_numbers", None)
                or getattr(src, "page", None)
                or (src.get("page_numbers") or src.get("page") if isinstance(src, dict) else None)
            )

            if not chunk_id:
                missing_ids += 1
            elif chunk_id in seen_ids:
                duplicate_ids.append(chunk_id)
            else:
                seen_ids.add(chunk_id)

            if not doc_name:
                missing_names += 1
            elif doc_name not in CANONICAL_DOCUMENT_NAMES:
                unknown_docs.append(doc_name)

            if pages is None or (isinstance(pages, list) and len(pages) == 0):
                missing_pages += 1

        if duplicate_ids:
            warnings.append(f"Duplicate chunk IDs detected in source list: {duplicate_ids}")

        if unknown_docs:
            warnings.append(f"Sources from unrecognized enactments detected: {list(set(unknown_docs))}")

        if missing_ids or missing_names or missing_pages:
            warnings.append(
                f"Missing source metadata detected: {missing_ids} missing IDs, "
                f"{missing_names} missing names, {missing_pages} missing page numbers."
            )

        is_valid = (
            missing_ids == 0
            and missing_names == 0
            and missing_pages == 0
            and len(duplicate_ids) == 0
            and len(unknown_docs) == 0
        )

        return SourceValidationReport(
            is_valid=is_valid,
            total_sources_checked=len(sources),
            missing_chunk_ids=missing_ids,
            missing_document_names=missing_names,
            missing_page_metadata=missing_pages,
            unknown_documents=list(set(unknown_docs)),
            duplicate_chunk_ids=duplicate_ids,
            warnings=warnings,
        )
