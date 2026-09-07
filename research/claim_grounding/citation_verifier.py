"""Citation verification module for verifying statutory references and source attributions.

Evaluates cited sources against retrieved candidate evidence chunks, detecting
valid, misaligned, unsupported, missing, and fabricated/invalid citations.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from research.claim_grounding.models import (
    AttachedCitation,
    AtomicClaim,
    CitationStatus,
    CitationVerificationResult,
    ClaimEvidenceMatch,
    ClaimStatus,
    ClaimType,
)


class CitationVerifier:
    """Verifies that citations in generated claims accurately refer to retrieved, applicable sources."""

    def __init__(self, citation_match_threshold: float = 0.30):
        self.citation_match_threshold = citation_match_threshold

    def verify_citations(
        self,
        claim: AtomicClaim,
        evidence_chunks: List[Any],
        evidence_matches: List[ClaimEvidenceMatch],
        claim_support_status: ClaimStatus,
    ) -> List[CitationVerificationResult]:
        """Verify all citations attached to a claim, or detect missing citations for high-risk claims."""
        results: List[CitationVerificationResult] = []

        # 1. Missing Citation Check for high-stakes statutory / punishment claims
        if not claim.attached_citations:
            if claim.claim_type in [ClaimType.STATUTORY_PROVISION, ClaimType.PUNISHMENT, ClaimType.PROCEDURAL_REQUIREMENT]:
                # Check if text mentions a statutory rule without citing the enactment
                results.append(
                    CitationVerificationResult(
                        claim_id=claim.claim_id,
                        citation_text="",
                        status=CitationStatus.MISSING_CITATION,
                        target_statute=None,
                        target_section=None,
                        matched_chunk_id=None,
                        reasoning=(
                            f"Claim makes an affirmative {claim.claim_type.value} proposition but provides no "
                            "statutory enactment or section citation."
                        ),
                    )
                )
            return results

        # 2. Verify each attached citation
        for cit in claim.attached_citations:
            res = self._verify_single_citation(cit, claim, evidence_chunks, evidence_matches, claim_support_status)
            results.append(res)

        return results

    def _verify_single_citation(
        self,
        cit: AttachedCitation,
        claim: AtomicClaim,
        evidence_chunks: List[Any],
        evidence_matches: List[ClaimEvidenceMatch],
        claim_support_status: ClaimStatus,
    ) -> CitationVerificationResult:
        """Verify an individual attached citation against retrieved chunks."""
        cit_raw = cit.raw_text
        cit_statute = cit.statute or ""
        cit_section = cit.section or ""

        # Check bracketed source index like [Source 1]
        if cit.source_index is not None:
            idx = cit.source_index - 1  # 1-indexed to 0-indexed
            if 0 <= idx < len(evidence_chunks):
                chunk = evidence_chunks[idx]
                chunk_id = chunk.get("chunk_id", chunk.get("source_id", f"chunk_{idx}")) if isinstance(chunk, dict) else getattr(chunk, "chunk_id", getattr(chunk, "source_id", f"chunk_{idx}"))
                c_stat = chunk.get("statute", chunk.get("document_name", "")) if isinstance(chunk, dict) else getattr(chunk, "statute", getattr(chunk, "document_name", ""))
                c_sec = chunk.get("section", "") if isinstance(chunk, dict) else getattr(chunk, "section", "")

                if claim_support_status in [ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED]:
                    return CitationVerificationResult(
                        claim_id=claim.claim_id,
                        citation_text=cit_raw,
                        status=CitationStatus.VALID_CITATION,
                        target_statute=c_stat,
                        target_section=c_sec,
                        matched_chunk_id=str(chunk_id),
                        reasoning=f"Bracketed citation [{cit.source_index}] correctly points to valid retrieved source {c_stat}.",
                    )
                else:
                    return CitationVerificationResult(
                        claim_id=claim.claim_id,
                        citation_text=cit_raw,
                        status=CitationStatus.UNSUPPORTED_CITATION,
                        target_statute=c_stat,
                        target_section=c_sec,
                        matched_chunk_id=str(chunk_id),
                        reasoning=f"Bracketed citation [{cit.source_index}] points to {c_stat}, but source does not support this claim.",
                    )
            else:
                return CitationVerificationResult(
                    claim_id=claim.claim_id,
                    citation_text=cit_raw,
                    status=CitationStatus.INVALID_SOURCE,
                    target_statute=None,
                    target_section=None,
                    matched_chunk_id=None,
                    reasoning=f"Citation refers to [Source {cit.source_index}], which does not exist in retrieved context (total sources: {len(evidence_chunks)}).",
                )

        # Statutory citation verification (e.g. "Section 303 BNS")
        cit_sec_num = self._extract_sec_num(cit_section or cit_raw)
        matched_chunk = None

        for match in evidence_matches:
            match_stat = match.statute.lower()
            match_sec_num = self._extract_sec_num(match.section or match.evidence_text[:100])

            statute_match = True
            if cit_statute:
                statute_match = (
                    cit_statute.lower() in match_stat
                    or self._statute_aliases_match(cit_statute.lower(), match_stat)
                )

            sec_match = True
            if cit_sec_num:
                sec_match = (cit_sec_num == match_sec_num)

            if statute_match and sec_match:
                matched_chunk = match
                break
            elif statute_match and not cit_sec_num:
                matched_chunk = match
                break

        if matched_chunk:
            if claim_support_status in [ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED]:
                return CitationVerificationResult(
                    claim_id=claim.claim_id,
                    citation_text=cit_raw,
                    status=CitationStatus.VALID_CITATION,
                    target_statute=matched_chunk.statute,
                    target_section=matched_chunk.section,
                    matched_chunk_id=matched_chunk.chunk_id,
                    reasoning=f"Citation '{cit_raw}' verified against retrieved chunk {matched_chunk.chunk_id} in {matched_chunk.statute}.",
                )
            else:
                return CitationVerificationResult(
                    claim_id=claim.claim_id,
                    citation_text=cit_raw,
                    status=CitationStatus.UNSUPPORTED_CITATION,
                    target_statute=matched_chunk.statute,
                    target_section=matched_chunk.section,
                    matched_chunk_id=matched_chunk.chunk_id,
                    reasoning=f"Cited enactment '{cit_raw}' exists in retrieved corpus, but retrieved text does not substantiate the claim.",
                )

        # Check if the cited section exists in corpus but under a different statute (misaligned)
        for chunk in evidence_chunks:
            c_doc = (chunk.get("document_name", chunk.get("statute", "")) if isinstance(chunk, dict) else getattr(chunk, "document_name", getattr(chunk, "statute", ""))).lower()
            c_sec = (chunk.get("section", "") if isinstance(chunk, dict) else getattr(chunk, "section", "")).lower()
            c_id = chunk.get("chunk_id", None) if isinstance(chunk, dict) else getattr(chunk, "chunk_id", None)
            if cit_sec_num and cit_sec_num == self._extract_sec_num(c_sec):
                # Found the section, but statute was different!
                return CitationVerificationResult(
                    claim_id=claim.claim_id,
                    citation_text=cit_raw,
                    status=CitationStatus.MISALIGNED_CITATION,
                    target_statute=c_doc,
                    target_section=c_sec,
                    matched_chunk_id=str(c_id) if c_id else None,
                    reasoning=f"Misaligned citation: Claim cited '{cit_raw}', but Section {cit_sec_num} in context belongs to {c_doc}.",
                )

        return CitationVerificationResult(
            claim_id=claim.claim_id,
            citation_text=cit_raw,
            status=CitationStatus.INVALID_SOURCE,
            target_statute=cit_statute or None,
            target_section=cit_sec_num or None,
            matched_chunk_id=None,
            reasoning=f"Cited statutory authority '{cit_raw}' does not exist anywhere in retrieved context.",
        )

    def _extract_sec_num(self, text: str) -> Optional[str]:
        """Extract numeric section token."""
        m = re.search(r"\b(?:section\s+|s\.\s*|sec\.\s*)?(\d+[a-z]?)\b", text.lower())
        return m.group(1) if m else None

    def _statute_aliases_match(self, cit: str, target: str) -> bool:
        """Match statutory acronyms to full names."""
        alias_pairs = [
            ("bns", "bharatiya nyaya"),
            ("bnss", "bharatiya nagarik"),
            ("bsa", "bharatiya sakshya"),
            ("ipc", "indian penal"),
            ("crpc", "criminal procedure"),
            ("iea", "indian evidence"),
            ("it act", "information technology"),
            ("cpa", "consumer protection"),
        ]
        for a, b in alias_pairs:
            if (a in cit and b in target) or (b in cit and a in target):
                return True
        return False
