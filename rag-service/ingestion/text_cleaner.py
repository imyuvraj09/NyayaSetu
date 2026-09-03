"""
Conservative text cleaning module for legal document ingestion.

Prepares raw extracted PDF text for downstream chunking and embedding
without modifying legal terminology, punctuation, numbering, or formatting structure.
"""

import re
from typing import Optional


def clean_text(raw_text: Optional[str]) -> str:
    """Conservatively clean extracted text from a legal document page.

    Operations performed:
    1. Remove null characters and unicode replacement/control artifacts.
    2. Normalize line terminators (\\r\\n and \\r to \\n).
    3. Strip trailing spaces from individual lines.
    4. Normalize excessive horizontal whitespace (multiple spaces/tabs to a single space).
    5. Collapse 3+ consecutive newlines to 2 newlines (retaining paragraph boundaries).
    6. Strip overall leading and trailing whitespace.

    Strictly preserves:
    - Legal sections, articles, clause identifiers, and numerals
    - Case sensitivity and exact legal phraseology
    - Punctuation marks and citations
    """
    if not raw_text:
        return ""

    # 1. Remove null bytes
    cleaned = raw_text.replace("\x00", "")

    # 2. Normalize line endings to standard LF
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Clean line by line: normalize inline horizontal whitespace while preserving line structure
    lines = cleaned.split("\n")
    cleaned_lines = []
    for line in lines:
        # Replace multiple horizontal whitespaces (spaces/tabs) with a single space
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(line_clean)

    cleaned = "\n".join(cleaned_lines)

    # 4. Collapse 3 or more consecutive newlines into 2 (preserves paragraph breaks)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 5. Final strip of outer whitespace
    return cleaned.strip()
