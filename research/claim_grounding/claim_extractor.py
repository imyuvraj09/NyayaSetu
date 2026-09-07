"""Deterministic atomic claim extraction with source span and citation tracking.

Decomposes legal answers into atomic, verifiable claims while preserving
exact character offsets, original texts, and parsed citation markers.
"""

import re
from typing import List, Optional, Tuple

from research.claim_grounding.models import (
    AttachedCitation,
    AtomicClaim,
    ClaimType,
    RiskLevel,
)

# Common legal and generic abbreviations to prevent false sentence boundaries
LEGAL_ABBREVIATIONS = {
    "sec.", "secs.", "art.", "arts.", "cl.", "cls.", "v.", "vs.",
    "e.g.", "i.e.", "viz.", "etc.", "para.", "paras.", "no.", "nos.",
    "hon'ble", "shri", "smt.", "dr.", "prof.", "adv.", "or.", "ors.",
}

# Regex pattern for statutory citation fragments
CITATION_PATTERNS = [
    # Explicit Section and Act
    r"(?P<section>Section\s+\d+[A-Z]?(?:\s*\(\d+\))?)\s+(?:of\s+(?:the\s+)?)?(?P<statute>Bharatiya\s+Nyaya\s+Sanhita|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|Bharatiya\s+Sakshya\s+Adhiniyam|Indian\s+Penal\s+Code|Code\s+of\s+Criminal\s+Procedure|Indian\s+Evidence\s+Act|Information\s+Technology\s+Act(?:,\s*\d{4})?|Companies\s+Act(?:,\s*\d{4})?|Consumer\s+Protection\s+Act(?:,\s*\d{4})?|Motor\s+Vehicles?\s+Act(?:,\s*\d{4})?|Constitution\s+of\s+India|BNS|BNSS|BSA|IPC|CrPC|IEA|IT\s+Act)",
    # Section alone
    r"(?P<section>Section\s+\d+[A-Z]?(?:\s*\(\d+\))?)",
    # Article alone
    r"(?P<section>Article\s+\d+[A-Z]?(?:\s*\(\d+\))?)",
    # Bracketed source reference: [Source 1], [1]
    r"\[(?:Source\s+)?(?P<source_idx>\d+)\]",
]


class ClaimExtractor:
    """Extracts atomic, verifiable propositions from legal text with precise provenance."""

    def __init__(self, min_claim_length: int = 15):
        self.min_claim_length = min_claim_length

    def extract_claims(self, text: str) -> List[AtomicClaim]:
        """Extract atomic claims from raw answer text with character offsets."""
        if not text or not text.strip():
            return []

        sentences_with_spans = self._split_into_sentences_with_spans(text)
        claims: List[AtomicClaim] = []
        claim_idx = 1

        for sent_text, start_char, end_char in sentences_with_spans:
            clean_sent = sent_text.strip()
            if len(clean_sent) < self.min_claim_length:
                continue

            # Check if sentence contains multiple atomic clauses separated by semicolons
            clauses = self._split_clauses(clean_sent, start_char)

            for clause_text, c_start, c_end in clauses:
                if len(clause_text.strip()) < self.min_claim_length:
                    continue

                citations = self._extract_attached_citations(clause_text, c_start)

                claim = AtomicClaim(
                    claim_id=f"CLAIM_{claim_idx:03d}",
                    claim_text=clause_text.strip(),
                    claim_type=ClaimType.GENERAL_INFORMATION,  # Classified in next stage
                    source_span_start=c_start,
                    source_span_end=c_end,
                    importance_weight=1.0,
                    risk_level=RiskLevel.MEDIUM,
                    attached_citations=citations,
                )
                claims.append(claim)
                claim_idx += 1

        return claims

    def _split_into_sentences_with_spans(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into sentences while tracking exact character offsets."""
        # Normalize list markers and paragraph splits to ensure discrete propositions
        spans: List[Tuple[str, int, int]] = []
        n = len(text)
        start = 0
        i = 0

        while i < n:
            # Check for sentence terminal punctuation (. ? !) or newline
            ch = text[i]

            if ch in ".?!":
                # Check for abbreviation
                word_start = max(0, text.rfind(" ", 0, i) + 1)
                token = text[word_start:i+1].lower()

                if token in LEGAL_ABBREVIATIONS or re.match(r"^[a-zA-Z]\.$", token):
                    # It's an abbreviation, keep scanning
                    i += 1
                    continue

                # Check if next char is digit (e.g. 66.1 or Section 43.A)
                if i + 1 < n and text[i + 1].isdigit():
                    i += 1
                    continue

                # Determine sentence boundary
                end = i + 1
                # Consume any trailing quotes or brackets
                while end < n and text[end] in "\"')]}":
                    end += 1

                candidate = text[start:end]
                if candidate.strip():
                    spans.append((candidate, start, end))

                # Skip whitespace
                while end < n and text[end].isspace():
                    end += 1
                start = end
                i = end
                continue

            elif ch == "\n":
                # Paragraph or bullet boundary
                end = i
                candidate = text[start:end]
                if candidate.strip():
                    spans.append((candidate, start, end))

                while end < n and (text[end] == "\n" or text[end].isspace()):
                    end += 1
                start = end
                i = end
                continue

            i += 1

        if start < n:
            candidate = text[start:n]
            if candidate.strip():
                spans.append((candidate, start, n))

        return spans

    def _split_clauses(self, sentence: str, base_offset: int) -> List[Tuple[str, int, int]]:
        """Split compound sentences with semicolons into independent atomic propositions."""
        if ";" not in sentence:
            return [(sentence, base_offset, base_offset + len(sentence))]

        clauses: List[Tuple[str, int, int]] = []
        parts = sentence.split(";")
        curr_offset = base_offset

        for p in parts:
            p_len = len(p)
            if p.strip():
                # Account for leading spaces in clause
                stripped = p.lstrip()
                lead_spaces = len(p) - len(stripped)
                c_start = curr_offset + lead_spaces
                c_end = c_start + len(stripped.rstrip())
                clauses.append((stripped.rstrip(), c_start, c_end))
            curr_offset += p_len + 1  # +1 for semicolon

        return clauses if clauses else [(sentence, base_offset, base_offset + len(sentence))]

    def _extract_attached_citations(self, text: str, base_offset: int) -> List[AttachedCitation]:
        """Extract statutory references, section markers, or source tags from claim text."""
        citations: List[AttachedCitation] = []

        for pat in CITATION_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                raw = match.group(0)
                m_dict = match.groupdict()
                sec = m_dict.get("section")
                stat = m_dict.get("statute")
                s_idx = None
                if "source_idx" in m_dict and m_dict["source_idx"]:
                    try:
                        s_idx = int(m_dict["source_idx"])
                    except ValueError:
                        pass

                cit = AttachedCitation(
                    raw_text=raw,
                    statute=stat.strip() if stat else None,
                    section=sec.strip() if sec else None,
                    source_index=s_idx,
                    span_start=base_offset + match.start(),
                    span_end=base_offset + match.end(),
                )
                citations.append(cit)

        return citations
