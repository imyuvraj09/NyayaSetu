"""
PDF document loader module for NyayaSetu.

Discovers PDF documents in raw storage, extracts page-by-page text using pypdf,
and handles empty or unreadable pages/documents with graceful error logging.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import pypdf
from pypdf.errors import PyPdfError

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RawPageExtract:
    """Raw text extracted from a single page of a PDF document."""

    page_number: int
    raw_text: str
    is_empty: bool


@dataclass
class DocumentLoadResult:
    """Result of loading and reading an individual PDF file."""

    file_path: Path
    source_filename: str
    is_success: bool
    total_pages: int = 0
    pages: List[RawPageExtract] = field(default_factory=list)
    error_message: Optional[str] = None


def discover_pdf_files(directory: Union[str, Path]) -> List[Path]:
    """Discover all .pdf files inside the specified directory.

    Args:
        directory: Path to the directory containing raw PDF files.

    Returns:
        Sorted list of Path objects for all .pdf files found.
    """
    raw_dir = Path(directory)
    if not raw_dir.exists() or not raw_dir.is_dir():
        logger.warning("Directory not found or is not a directory: %s", raw_dir)
        return []

    pdf_files = sorted(
        [p for p in raw_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    )
    logger.info("Discovered %d PDF file(s) in %s", len(pdf_files), raw_dir)
    return pdf_files


def load_pdf_pages(file_path: Union[str, Path]) -> DocumentLoadResult:
    """Extract text page by page from a single PDF document.

    Args:
        file_path: Path to the PDF file.

    Returns:
        DocumentLoadResult containing extracted pages or error details.
    """
    path = Path(file_path)
    result = DocumentLoadResult(file_path=path, source_filename=path.name, is_success=False)

    if not path.exists():
        msg = f"File does not exist: {path}"
        logger.error(msg)
        result.error_message = msg
        return result

    try:
        reader = pypdf.PdfReader(str(path))
        num_pages = len(reader.pages)
        result.total_pages = num_pages

        logger.info("Reading PDF: %s (%d pages)", path.name, num_pages)

        for idx, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as page_err:
                logger.warning(
                    "Error extracting text from page %d of %s: %s",
                    idx,
                    path.name,
                    page_err,
                )
                page_text = ""

            is_empty = len(page_text.strip()) == 0
            result.pages.append(
                RawPageExtract(
                    page_number=idx,
                    raw_text=page_text,
                    is_empty=is_empty,
                )
            )

        result.is_success = True
        logger.info(
            "Successfully loaded %s: %d page(s) extracted",
            path.name,
            len(result.pages),
        )

    except PyPdfError as pdf_err:
        msg = f"pypdf extraction error in {path.name}: {pdf_err}"
        logger.error(msg)
        result.error_message = msg
    except Exception as exc:
        msg = f"Unexpected error reading {path.name}: {exc}"
        logger.error(msg, exc_info=True)
        result.error_message = msg

    return result


def load_all_pdfs(directory: Union[str, Path]) -> List[DocumentLoadResult]:
    """Discover and load all PDF documents in the given directory.

    Args:
        directory: Path to raw PDF directory.

    Returns:
        List of DocumentLoadResult objects for each discovered PDF.
    """
    pdf_files = discover_pdf_files(directory)
    results = []

    for pdf_file in pdf_files:
        res = load_pdf_pages(pdf_file)
        results.append(res)

    return results
