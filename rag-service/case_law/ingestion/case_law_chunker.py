"""
Paragraph-Aware Case-Law Chunker for NyayaSetu.

Chunks judicial decisions while preserving:
- Paragraph numbers and headings
- Ratio decidendi, holdings, and legal tests
- Cited statutes and sections
- Complete provenance metadata
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.case_law import CaseLawChunk, CaseLawDocument, PassageType
from utils.logger import get_logger

logger = get_logger(__name__)


class CaseLawChunker:
    """Chunks judicial documents into paragraph-level chunks with full provenance."""

    def __init__(self, raw_data_path: Optional[Path] = None) -> None:
        if raw_data_path:
            self.raw_data_path = Path(raw_data_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.raw_data_path = base_dir / "data" / "raw" / "judgments" / "verified_judgments.json"

    def chunk_documents(self, documents: List[CaseLawDocument]) -> List[CaseLawChunk]:
        """Generate paragraph-aware CaseLawChunk objects for all validated documents."""
        # Read raw paragraphs from JSON
        doc_map = {d.document_id: d for d in documents}
        raw_entries = []
        if self.raw_data_path.exists():
            with open(self.raw_data_path, "r", encoding="utf-8") as f:
                raw_entries = json.load(f)

        chunks: List[CaseLawChunk] = []

        for entry in raw_entries:
            doc_id = entry.get("document_id")
            if doc_id not in doc_map:
                continue

            doc = doc_map[doc_id]
            paragraphs = entry.get("paragraphs", [])

            for p in paragraphs:
                para_num = str(p.get("paragraph_number", "1"))
                chunk_id = f"{doc.document_id}_p{para_num.zfill(4)}"

                p_type_str = p.get("passage_type", "GENERAL").upper()
                try:
                    p_type = PassageType[p_type_str]
                except KeyError:
                    p_type = PassageType.GENERAL

                chunk = CaseLawChunk(
                    chunk_id=chunk_id,
                    document_id=doc.document_id,
                    evidence_type=doc.evidence_type,
                    case_name=doc.case_name,
                    court=doc.court,
                    court_level=doc.court_level,
                    citation=doc.citation,
                    judgment_date=doc.judgment_date,
                    paragraph_number=para_num,
                    paragraph_heading=p.get("paragraph_heading"),
                    passage_type=p_type,
                    text=p.get("text", "").strip(),
                    statutes_referred=p.get("statutes_referred", doc.statutes_referred),
                    sections_referred=p.get("sections_referred", doc.sections_referred),
                    topics=p.get("topics", doc.topics),
                    is_holding_or_ratio=p.get("is_holding_or_ratio", False),
                    verified=doc.verified,
                )
                chunks.append(chunk)

        logger.info("Generated %d paragraph-level CaseLawChunks across %d documents", len(chunks), len(documents))
        return chunks
