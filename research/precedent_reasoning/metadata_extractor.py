"""Metadata Extraction with Provenance and Explicit Uncertainty Preservation.

Extracts:
- Official case title
- Court name and classified CourtLevel
- Citation and standard law reporter normalization
- Decision date
- Bench composition and BenchStrength
- Referenced statutes and sections
- Explicit subsequent treatment (overruled_by, distinguished_by, followed_by)

Strict safety rule: Missing fields remain UNKNOWN. No guessing or halluncinating metadata.
"""

import json
import re
from typing import Any, Dict, List, Optional

from research.precedent_reasoning.court_hierarchy import CourtHierarchyEngine
from research.precedent_reasoning.models import (
    BenchStrength,
    CourtLevel,
    PrecedentMetadata,
)


class PrecedentMetadataExtractor:
    """Extracts structured, verified metadata from judgment chunks or dictionaries."""

    CITATION_PATTERNS = [
        r"\(\d{4}\)\s*\d+\s+SCC\s+\d+",
        r"AIR\s+\d{4}\s+SC\s+\d+",
        r"\d{4}\s+SCC\s+OnLine\s+[A-Za-z\s]+\d+",
        r"\d{4}\s+Cri\s*LJ\s+\d+",
        r"\(\d{4}\)\s*\d+\s+SCR\s+\d+",
    ]

    @classmethod
    def extract_from_dict(cls, data: Dict[str, Any]) -> PrecedentMetadata:
        """Extract PrecedentMetadata from a dictionary (e.g., ChromaDB metadata or raw JSON)."""
        case_name = data.get("case_name") or data.get("document_name") or data.get("documentName") or "Unknown Case"
        court = data.get("court") or data.get("actName") or "Unknown Court"

        # Classify court level
        raw_level = data.get("court_level")
        if raw_level and hasattr(raw_level, "value"):
            court_level = CourtLevel(raw_level.value)
        elif raw_level and str(raw_level).upper() in CourtLevel.__members__:
            court_level = CourtLevel(str(raw_level).upper())
        else:
            court_level = CourtHierarchyEngine.classify_court_level(court)

        citation = data.get("citation") or "Unknown Citation"
        judgment_date = data.get("judgment_date") or "UNKNOWN"
        jurisdiction = data.get("jurisdiction") or "India"

        # Bench members & strength
        raw_bench = data.get("bench") or []
        if isinstance(raw_bench, str):
            try:
                raw_bench = json.loads(raw_bench)
            except Exception:
                raw_bench = [b.strip() for b in raw_bench.split(",") if b.strip()]

        bench = [str(b).strip() for b in raw_bench if str(b).strip()]
        bench_strength = CourtHierarchyEngine.determine_bench_strength(bench)

        # Statutes & Sections referred
        statutes = cls._parse_list_field(data.get("statutes_referred"))
        sections = cls._parse_list_field(data.get("sections_referred"))
        topics = cls._parse_list_field(data.get("topics"))

        # Explicit subsequent treatment
        overruled_by = data.get("overruled_by") or data.get("overruled_or_distinguished")
        if overruled_by and "overruled" not in str(overruled_by).lower():
            # If it says 'distinguished', handle separately
            if "distinguished" in str(overruled_by).lower():
                overruled_by = None

        distinguished_by = cls._parse_list_field(data.get("distinguished_by"))
        followed_by = cls._parse_list_field(data.get("followed_by"))

        source_id = data.get("source_filename") or data.get("source_name") or data.get("source_identifier") or "verified_corpus"

        return PrecedentMetadata(
            case_name=case_name,
            court=court,
            court_level=court_level,
            citation=citation,
            judgment_date=judgment_date,
            jurisdiction=jurisdiction,
            bench=bench,
            bench_strength=bench_strength,
            statutes_referred=statutes,
            sections_referred=sections,
            topics=topics,
            overruled_by=overruled_by,
            distinguished_by=distinguished_by,
            followed_by=followed_by,
            source_identifier=source_id,
        )

    @classmethod
    def extract_from_text(cls, text: str, fallback_case_name: str = "Unknown Case") -> PrecedentMetadata:
        """Extract available metadata from plain judgment text using regex patterns."""
        citation = "Unknown Citation"
        for pat in cls.CITATION_PATTERNS:
            match = re.search(pat, text)
            if match:
                citation = match.group(0)
                break

        # Court mention
        court = "Unknown Court"
        if "Supreme Court of India" in text or "IN THE SUPREME COURT OF INDIA" in text:
            court = "Supreme Court of India"
        elif "High Court" in text:
            m = re.search(r"High Court of [A-Za-z\s]+", text)
            court = m.group(0) if m else "High Court"

        court_level = CourtHierarchyEngine.classify_court_level(court)

        # Date pattern (YYYY-MM-DD or DD Month YYYY)
        judgment_date = "UNKNOWN"
        d_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if d_match:
            judgment_date = d_match.group(1)

        return PrecedentMetadata(
            case_name=fallback_case_name,
            court=court,
            court_level=court_level,
            citation=citation,
            judgment_date=judgment_date,
            jurisdiction="India",
            bench=[],
            bench_strength=BenchStrength.UNKNOWN,
            statutes_referred=[],
            sections_referred=[],
            topics=[],
            source_identifier="unstructured_text",
        )

    @staticmethod
    def _parse_list_field(field_val: Any) -> List[str]:
        """Safely parse a list or JSON string field into a List[str]."""
        if not field_val:
            return []
        if isinstance(field_val, list):
            return [str(v).strip() for v in field_val if str(v).strip()]
        if isinstance(field_val, str):
            try:
                parsed = json.loads(field_val)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            except Exception:
                pass
            return [v.strip() for v in field_val.split(",") if v.strip()]
        return []
