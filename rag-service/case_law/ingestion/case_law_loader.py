"""
Case-Law Document Loader for NyayaSetu.

Loads verified judgment records from authoritative sources.
Enforces strict provenance validation:
- Source URL must be an official domain / verified archive
- Case name, court, citation, and judgment date must be present
- Unverified, blog, or forum entries are strictly rejected
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.case_law import CaseLawDocument, CourtLevel, EvidenceType
from utils.logger import get_logger

logger = get_logger(__name__)

AUTHORITATIVE_SOURCE_DOMAINS = [
    "sci.gov.in",
    "main.sci.gov.in",
    "judis.nic.in",
    "highcourt",
    "ecourts.gov.in",
    "escr",
    "indiankanoon.org",
]


class CaseLawLoader:
    """Loads and validates authoritative Indian judgment documents."""

    def __init__(self, raw_data_path: Optional[Path] = None) -> None:
        if raw_data_path:
            self.raw_data_path = Path(raw_data_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.raw_data_path = base_dir / "data" / "raw" / "judgments" / "verified_judgments.json"

    def load_documents(self) -> List[CaseLawDocument]:
        """Load, validate, and return all verified judgment records."""
        if not self.raw_data_path.exists():
            logger.warning("Case-law data file not found at: %s", self.raw_data_path)
            return []

        with open(self.raw_data_path, "r", encoding="utf-8") as f:
            raw_entries = json.load(f)

        valid_docs: List[CaseLawDocument] = []
        for entry in raw_entries:
            try:
                # Enforce verification criteria
                if not entry.get("verified", False):
                    logger.warning("Skipping unverified case entry: %s", entry.get("case_name"))
                    continue

                source_url = entry.get("source_url", "").lower()
                if not any(domain in source_url for domain in AUTHORITATIVE_SOURCE_DOMAINS):
                    logger.warning(
                        "Skipping case '%s': source_url '%s' not from an authoritative court domain",
                        entry.get("case_name"),
                        source_url,
                    )
                    continue

                # Ensure required fields
                if not entry.get("case_name") or not entry.get("citation") or not entry.get("court"):
                    logger.warning("Skipping case missing core metadata: %s", entry)
                    continue

                # Parse court level
                court_name = entry.get("court", "")
                if "supreme court" in court_name.lower():
                    court_lvl = CourtLevel.SUPREME_COURT
                elif "high court" in court_name.lower():
                    court_lvl = CourtLevel.HIGH_COURT
                else:
                    court_lvl = CourtLevel.OTHER

                doc = CaseLawDocument(
                    document_id=entry["document_id"],
                    evidence_type=EvidenceType.CASE_LAW,
                    case_name=entry["case_name"],
                    court=court_name,
                    court_level=court_lvl,
                    citation=entry["citation"],
                    judgment_date=entry["judgment_date"],
                    case_number=entry.get("case_number"),
                    bench=entry.get("bench", []),
                    statutes_referred=entry.get("statutes_referred", []),
                    sections_referred=entry.get("sections_referred", []),
                    topics=entry.get("topics", []),
                    source_url=entry["source_url"],
                    source_name=entry.get("source_name", "Supreme Court of India Official Judgments"),
                    verified=True,
                    summary=entry.get("summary"),
                    overruled_or_distinguished=entry.get("overruled_or_distinguished"),
                )
                valid_docs.append(doc)
            except Exception as e:
                logger.error("Error validating case law document %s: %s", entry.get("document_id"), e)

        logger.info("Successfully loaded %d verified CaseLawDocuments from %s", len(valid_docs), self.raw_data_path)
        return valid_docs
