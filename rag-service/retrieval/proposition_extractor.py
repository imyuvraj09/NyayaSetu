"""
Proposition Extractor for NyayaSetu.

Transforms raw retrieved statutory and case-law chunks into sanitized,
normalized CleanProposition objects, stripping all raw gazette headers,
broken OCR, leading section numbers, and subsection indicators.
"""

import re
from typing import Any, Dict, List, Optional

from rag.clean_proposition import CleanProposition
from schemas.generation import SourceReference
from utils.logger import get_logger

logger = get_logger(__name__)

GAZETTE_PATTERNS = [
    r"(?i)\b\d+\s+the\s+gazette\s+of\s+india\s+extraordinary\b",
    r"(?i)\[\s*part\s+ii\s*[-–—]\s*sec(?:tion)?\.?\s*\d+\s*\]",
    r"(?i)part\s+ii\s*[-–—]\s*sec(?:tion)?\.?\s*\d+",
    r"(?i)sec(?:tion)?\.?\s*\d+\s*\]",
    r"(?i)\[\s*sec(?:tion)?\.?\s*\d+\s*\]",
    r"(?i)the\s+gazette\s+of\s+india",
    r"(?i)extraordinary",
    r"(?i)published\s+by\s+authority",
    r"(?i)ministry\s+of\s+law\s+and\s+justice",
    r"(?i)regd\.?\s*no\.?\s*[a-z0-9\-/]+",
    r"(?i)new\s+delhi,\s+the\s+\d+.*?(?:20\d\d|19\d\d)",
    r"(?i)\[\s*part\s+ii",
]


class PropositionExtractor:
    """Extracts clean, normalized legal propositions from raw evidence chunks."""

    @classmethod
    def clean_raw_text(
        cls,
        text: str,
        section_number: str = "",
        section_title: str = "",
        max_chars: int = 350,
    ) -> str:
        """Sanitize raw statutory text, eliminating OCR noise, gazette headers, and leading section markers."""
        if not text:
            return ""

        clean = text

        # 1. Remove Gazette and OCR header lines
        for pat in GAZETTE_PATTERNS:
            clean = re.sub(pat, " ", clean)

        # 2. Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()

        # 2.5 Strip orphaned leading page numbers / dashes left from gazette headers
        clean = re.sub(r"^\s*[\d\s\-–—\.]+(?=(?:Section|\b[A-Z]))", "", clean).strip()

        # 3. Strip leading section number prefix (e.g. "66.", "66A.", "Section 66.", "Section 105.")
        if section_number:
            sec_esc = re.escape(str(section_number).strip())
            clean = re.sub(r"^(?:section\s+)?" + sec_esc + r"[\.\s:–—\-]+", "", clean, flags=re.IGNORECASE).strip()
        else:
            clean = re.sub(r"^(?:section\s+\d+[a-z]?|\d+[a-z]?)[\.\s:–—\-]+", "", clean, flags=re.IGNORECASE).strip()

        # 4. Strip subsection markers or leading section title if repeated in text
        clean = re.sub(r"^\(\s*[0-9a-zA-Z]+\s*\)\s*", "", clean).strip()
        clean = re.sub(r"^[0-9]+\s*[\.\)]\s*", "", clean).strip()

        if section_title:
            title_esc = re.escape(section_title.strip())
            clean = re.sub(r"^" + title_esc + r"[\.\s:–—\-]+", "", clean, flags=re.IGNORECASE).strip()

        # Strip subsection markers again if after title
        clean = re.sub(r"^\(\s*[0-9a-zA-Z]+\s*\)\s*", "", clean).strip()
        clean = re.sub(r"^[0-9]+\s*[\.\)]\s*", "", clean).strip()

        # 6. Transform stiff legalese opening phrases into clear plain-English
        if clean.startswith("Whoever "):
            clean = "Whoever " + clean[8:]
        elif clean.startswith("If any person, "):
            clean = "Under this provision, where any person, " + clean[15:]
        elif clean.startswith("If any person "):
            clean = "Under this provision, where any person " + clean[14:]
        elif clean.startswith("No person shall be "):
            clean = "The enactment provides that no person shall be " + clean[19:]
        elif clean.startswith("Every citizen shall have "):
            clean = "The enactment guarantees that every citizen shall have " + clean[25:]
        elif clean.startswith("A consumer may "):
            clean = "The provision entitles a consumer to " + clean[15:]

        # 7. Truncate at sentence boundary if exceeding max_chars
        if len(clean) > max_chars:
            cutoff = clean[:max_chars]
            last_period = cutoff.rfind(".")
            last_semi = cutoff.rfind(";")
            last_break = max(last_period, last_semi)
            if last_break > max_chars * 0.6:
                clean = clean[:last_break + 1]
            else:
                clean = clean[:max_chars].rstrip() + "..."

        if clean:
            clean = clean[0].upper() + clean[1:]
        return clean

    @classmethod
    def extract_from_source(
        cls,
        source: SourceReference,
        facet: str = "GENERAL",
    ) -> CleanProposition:
        """Create a CleanProposition from a SourceReference."""
        act_name = source.act_short_name or source.document_name or "Statute"
        sec_num = source.section_number or ""
        sec_title = source.section_title or ""
        raw_text = source.text_snippet or ""
        ev_type = (getattr(source, "evidence_type", None) or "STATUTE").upper()
        source_id = source.source_label or ""

        clean_text = cls.clean_raw_text(raw_text, sec_num, sec_title)
        if not clean_text:
            if sec_title:
                clean_text = f"The provision establishes the statutory framework and legal standards governing {sec_title.lower()}."
            else:
                clean_text = f"The provision sets forth the governing legal requirements under {act_name}."

        authority_name = f"{act_name} Section {sec_num}" if sec_num else act_name
        if "constitution" in (source.document_name or "").lower():
            authority_name = f"Constitution of India Article {sec_num}" if sec_num else "Constitution of India"
            ev_type = "CONSTITUTION"
        elif ev_type == "CASE_LAW" or getattr(source, "case_name", None):
            authority_name = getattr(source, "case_name", "") or source.document_name
            ev_type = "CASE_LAW"

        return CleanProposition(
            authority_name=authority_name,
            act=act_name,
            section=sec_num,
            title=sec_title,
            clean_proposition=clean_text,
            support_span=clean_text[:120],
            facet=facet,
            source_id=source_id,
            authority_type=ev_type,
            status="ANSWERED_SUPPORTED",
        )

    @classmethod
    def extract_all(
        cls,
        sources: List[SourceReference],
    ) -> List[CleanProposition]:
        """Extract a list of CleanPropositions from retrieved sources."""
        propositions: List[CleanProposition] = []
        for src in sources:
            prop = cls.extract_from_source(src)
            propositions.append(prop)
        return propositions
