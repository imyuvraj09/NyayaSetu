"""Evidence matcher connecting atomic claims to retrieved candidate chunks.

Identifies candidate chunks from the context actually provided to the generator
and scores alignment based on statutory entity, section, and lexical relevance.
"""

import re
from typing import Any, Dict, List, Optional, Set

from research.claim_grounding.models import (
    AtomicClaim,
    ClaimEvidenceMatch,
    ClaimStatus,
)


class EvidenceMatcher:
    """Matches atomic claims to retrieved context chunks without external post-hoc retrieval."""

    def __init__(self, min_match_threshold: float = 0.20):
        self.min_match_threshold = min_match_threshold

    def match_claim_to_evidence(
        self,
        claim: AtomicClaim,
        evidence_chunks: List[Any],
    ) -> List[ClaimEvidenceMatch]:
        """Rank and return candidate chunks for a single atomic claim."""
        matches: List[ClaimEvidenceMatch] = []
        claim_text_lower = claim.claim_text.lower()
        claim_tokens = self._tokenize(claim_text_lower)

        # Extract targeted sections and statutes mentioned in claim
        claim_sections = self._extract_section_numbers(claim_text_lower)
        claim_statutes = self._extract_statute_mentions(claim_text_lower)

        for chunk in evidence_chunks:
            chunk_dict = self._normalize_chunk(chunk)
            chunk_id = chunk_dict.get("chunk_id", "unknown")
            statute = chunk_dict.get("statute", "")
            section = chunk_dict.get("section", "")
            doc_name = chunk_dict.get("document_name", "")
            evidence_text = chunk_dict.get("text", "")
            ev_lower = evidence_text.lower()
            ev_tokens = self._tokenize(ev_lower)

            score = 0.0

            # 1. Exact Section Match Bonus
            chunk_sections = self._extract_section_numbers(section.lower() + " " + ev_lower[:150])
            if claim_sections and chunk_sections:
                common_secs = claim_sections & chunk_sections
                if common_secs:
                    score += 0.45
            elif claim_sections:
                # Claim specifically named a section, but chunk does not have it
                pass

            # 2. Statute Match Bonus
            full_statute_name = (statute + " " + doc_name).lower()
            if claim_statutes:
                matched_stat = any(s in full_statute_name for s in claim_statutes)
                if matched_stat:
                    score += 0.30
                else:
                    # Claim explicitly cited Statute A, but chunk is from Statute B
                    score -= 0.15

            # 3. Lexical Token Overlap (Jaccard on non-stop words)
            if claim_tokens and ev_tokens:
                intersection = claim_tokens & ev_tokens
                overlap_ratio = len(intersection) / len(claim_tokens)
                score += 0.35 * overlap_ratio

            # Bound score [0.0, 1.0]
            final_score = max(0.0, min(1.0, score))

            if final_score >= self.min_match_threshold:
                matches.append(
                    ClaimEvidenceMatch(
                        claim_id=claim.claim_id,
                        chunk_id=chunk_id,
                        statute=statute or doc_name,
                        section=section,
                        source_identifier=doc_name or statute,
                        match_score=round(final_score, 4),
                        evidence_text=evidence_text,
                        support_status=ClaimStatus.INSUFFICIENT_EVIDENCE,  # Decided by EntailmentChecker
                    )
                )

        # Sort descending by match score
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches

    def _normalize_chunk(self, chunk: Any) -> Dict[str, Any]:
        """Normalize different chunk objects (RetrievedChunk, SourceReference, dict) into uniform dict."""
        if isinstance(chunk, dict):
            text = chunk.get("text", "") or chunk.get("content", "")
            return {
                "chunk_id": chunk.get("chunk_id", chunk.get("id", "chunk")),
                "statute": chunk.get("statute", chunk.get("act", "")),
                "section": chunk.get("section", ""),
                "document_name": chunk.get("document_name", chunk.get("document_title", "")),
                "text": text,
            }
        # Object attribute extraction
        c_id = getattr(chunk, "chunk_id", getattr(chunk, "source_id", "chunk"))
        statute = getattr(chunk, "statute", getattr(chunk, "act", ""))
        section = getattr(chunk, "section", getattr(chunk, "section_number", ""))
        doc_name = getattr(chunk, "document_name", getattr(chunk, "document_title", ""))
        text = getattr(chunk, "text", getattr(chunk, "content", getattr(chunk, "snippet", "")))

        return {
            "chunk_id": str(c_id),
            "statute": str(statute) if statute else "",
            "section": str(section) if section else "",
            "document_name": str(doc_name) if doc_name else "",
            "text": str(text) if text else "",
        }

    def _tokenize(self, text: str) -> Set[str]:
        """Simple alphanumeric tokenizer filtering basic stopwords."""
        words = set(re.findall(r"\b[a-z0-9_]{3,}\b", text))
        stopwords = {
            "the", "and", "that", "this", "with", "for", "from", "are", "was",
            "were", "shall", "under", "which", "such", "any", "not", "have", "has",
        }
        return words - stopwords

    def _extract_section_numbers(self, text: str) -> Set[str]:
        """Extract section numbers like 303, 43, 66d, 65b."""
        matches = re.findall(r"\bsection\s+(\d+[a-z]?)\b", text)
        return {m.lower() for m in matches}

    def _extract_statute_mentions(self, text: str) -> Set[str]:
        """Extract mentioned statute names or acronyms."""
        statutes = set()
        if "bns" in text or "bharatiya nyaya" in text:
            statutes.add("bns")
            statutes.add("bharatiya nyaya")
        if "bnss" in text or "nagarik suraksha" in text:
            statutes.add("bnss")
            statutes.add("nagarik suraksha")
        if "bsa" in text or "sakshya" in text:
            statutes.add("bsa")
            statutes.add("sakshya")
        if "ipc" in text or "penal code" in text:
            statutes.add("ipc")
            statutes.add("indian penal code")
        if "crpc" in text or "criminal procedure" in text:
            statutes.add("crpc")
        if "iea" in text or "evidence act" in text:
            statutes.add("iea")
        if "it act" in text or "information technology" in text:
            statutes.add("it act")
            statutes.add("information technology")
        if "companies act" in text:
            statutes.add("companies act")
        if "constitution" in text:
            statutes.add("constitution")
        return statutes
