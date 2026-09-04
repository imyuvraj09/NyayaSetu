"""
Judicial Principle Extractor for NyayaSetu.

Analyzes retrieved CaseLaw chunks to extract core judicial doctrines,
ratio decidendi, holdings, and legal tests while retaining exact paragraph provenance.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from schemas.case_law import EvidenceType
from schemas.retrieval import RerankedChunk
from utils.logger import get_logger

logger = get_logger(__name__)

HOLDING_INDICATOR_PATTERNS = [
    r"\b(?:we\s+hold\s+that|held\s+that|court\s+held\s+that|the\s+supreme\s+court\s+held)\b",
    r"\b(?:the\s+legal\s+position\s+is|it\s+is\s+well\s+settled\s+that|settled\s+law\s+that)\b",
    r"\b(?:there\s+is\s+a\s+clear\s+distinction\s+between|fundamental\s+difference\s+between)\b",
    r"\b(?:consent\s+involves|consent\s+for\s+the\s+purpose\s+of|vitiated\s+by)\b",
    r"\b(?:the\s+test\s+to\s+be\s+applied|must\s+satisfy\s+the\s+following|dual\s+conditions)\b",
    r"\b(?:does\s+not\s+by\s+itself\s+establish|cannot\s+be\s+presumed|cannot\s+operate\s+as)\b",
]


@dataclass
class ExtractedJudicialPrinciple:
    """Represents a verified judicial principle grounded in a specific judgment paragraph."""
    principle: str
    case_name: str
    court: str
    citation: str
    paragraph: str
    judgment_date: str
    source_chunk_id: str
    evidence_type: str = "CASE_LAW"
    principle_category: str = "HOLDING"  # "HOLDING", "LEGAL_TEST", "DISTINCTION", "RATIO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principle": self.principle,
            "case_name": self.case_name,
            "court": self.court,
            "citation": self.citation,
            "paragraph": self.paragraph,
            "judgment_date": self.judgment_date,
            "source_chunk_id": self.source_chunk_id,
            "evidence_type": self.evidence_type,
            "principle_category": self.principle_category,
        }


class JudicialPrincipleExtractor:
    """Extracts grounded judicial holdings and principles with paragraph provenance."""

    def extract_principles(self, case_chunks: List[RerankedChunk]) -> List[ExtractedJudicialPrinciple]:
        """Extract substantive judicial principles from retrieved case law chunks."""
        extracted: List[ExtractedJudicialPrinciple] = []

        for chunk in case_chunks:
            if chunk.evidence_type != "CASE_LAW":
                continue

            text = chunk.text.strip()
            sentences = re.split(r"(?<=[.!?])\s+", text)

            # Find sentences containing holding patterns or core reasoning
            for sent in sentences:
                sent_clean = sent.strip()
                if len(sent_clean) < 30:
                    continue

                is_holding = any(re.search(pat, sent_clean, re.IGNORECASE) for pat in HOLDING_INDICATOR_PATTERNS)
                chunk_meta = chunk.metadata or {}
                if is_holding or chunk.is_holding_or_ratio or chunk_meta.get("is_holding_or_ratio"):
                    cat = "HOLDING"
                    if "test" in sent_clean.lower() or "conditions" in sent_clean.lower():
                        cat = "LEGAL_TEST"
                    elif "distinction" in sent_clean.lower() or "difference" in sent_clean.lower():
                        cat = "DISTINCTION"
                    elif "ratio" in sent_clean.lower():
                        cat = "RATIO"

                    extracted.append(
                        ExtractedJudicialPrinciple(
                            principle=sent_clean,
                            case_name=chunk.case_name or chunk.document_name,
                            court=chunk.court or "Supreme Court of India",
                            citation=chunk.citation or "",
                            paragraph=str(chunk.paragraph_number or "1"),
                            judgment_date=chunk.judgment_date or "",
                            source_chunk_id=chunk.chunk_id,
                            evidence_type="CASE_LAW",
                            principle_category=cat,
                        )
                    )

        logger.info("Extracted %d judicial principles across %d case chunks", len(extracted), len(case_chunks))
        return extracted
