"""
Clean Proposition Model for NyayaSetu.

Defines the normalized proposition representation that decouples raw statutory/case text
from generated legal answers, eliminating raw OCR, gazette text, section numbers, and subsection digits.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CleanProposition:
    """A clean, normalized legal proposition extracted from an authority."""
    authority_name: str
    act: str
    section: str
    title: str
    clean_proposition: str
    support_span: str = ""
    facet: str = "GENERAL"
    source_id: str = ""
    authority_type: str = "STATUTE"
    status: str = "ANSWERED_SUPPORTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_name": self.authority_name,
            "act": self.act,
            "section": self.section,
            "title": self.title,
            "clean_proposition": self.clean_proposition,
            "support_span": self.support_span,
            "facet": self.facet,
            "source_id": self.source_id,
            "authority_type": self.authority_type,
            "status": self.status,
        }
