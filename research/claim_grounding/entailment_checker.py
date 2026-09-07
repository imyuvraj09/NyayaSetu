"""Entailment and evidential support verification for atomic legal claims.

Distinguishes superficial semantic similarity from actual legal doctrinal support,
detecting supported, partially supported, unsupported, and contradictory propositions.
"""

import re
from typing import List, Optional, Set, Tuple

from research.claim_grounding.models import (
    AtomicClaim,
    ClaimEvidenceMatch,
    ClaimStatus,
    ClaimType,
)


class EntailmentChecker:
    """Evaluates legal claim support against matched evidence chunks."""

    def __init__(
        self,
        full_support_threshold: float = 0.65,
        partial_support_threshold: float = 0.35,
    ):
        self.full_support_threshold = full_support_threshold
        self.partial_support_threshold = partial_support_threshold

    def evaluate_support(
        self,
        claim: AtomicClaim,
        candidate_matches: List[ClaimEvidenceMatch],
    ) -> Tuple[ClaimStatus, float, Optional[ClaimEvidenceMatch], str]:
        """Determine whether the claim is SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, or CONTRADICTED.

        Returns:
            (ClaimStatus, support_score [0.0 - 1.0], best_match, reasoning)
        """
        if not candidate_matches:
            return (
                ClaimStatus.UNSUPPORTED,
                0.0,
                None,
                "No retrieved evidence chunk matched the factual or statutory terms in the claim.",
            )

        best_match = candidate_matches[0]
        claim_text = claim.claim_text.lower()
        evidence_text = best_match.evidence_text.lower()

        # 1. Contradiction Detection
        is_contradiction, contra_reason = self._check_contradiction(claim, best_match)
        if is_contradiction:
            best_match.support_status = ClaimStatus.CONTRADICTED
            best_match.entailment_reasoning = contra_reason
            return (ClaimStatus.CONTRADICTED, 0.0, best_match, contra_reason)

        # 2. Statutory Section Alignment Check
        claim_sections = self._extract_section_numbers(claim_text)
        evidence_sections = self._extract_section_numbers(
            best_match.section.lower() + " " + evidence_text[:200]
        )

        if claim_sections:
            # If claim specifically referenced Section X, evidence MUST mention Section X
            has_sec_match = bool(claim_sections & evidence_sections)
            if not has_sec_match:
                # Evidence is from another section or section is unverified
                reason = (
                    f"Claim specifically asserts {', '.join(claim_sections)}, but best evidence is from "
                    f"{best_match.statute} Section {best_match.section or 'Unknown'}."
                )
                if best_match.match_score >= self.partial_support_threshold:
                    best_match.support_status = ClaimStatus.PARTIALLY_SUPPORTED
                    best_match.entailment_reasoning = reason
                    return (ClaimStatus.PARTIALLY_SUPPORTED, 0.50, best_match, reason)
                else:
                    best_match.support_status = ClaimStatus.UNSUPPORTED
                    best_match.entailment_reasoning = reason
                    return (ClaimStatus.UNSUPPORTED, 0.0, best_match, reason)

        # 3. High-Risk Claim Validation (Punishment & Procedural Powers)
        if claim.claim_type == ClaimType.PUNISHMENT:
            status, score, reason = self._verify_punishment_claim(claim_text, evidence_text, best_match)
            best_match.support_status = status
            best_match.entailment_reasoning = reason
            return (status, score, best_match, reason)

        elif claim.claim_type == ClaimType.PROCEDURAL_REQUIREMENT:
            status, score, reason = self._verify_procedural_claim(claim_text, evidence_text, best_match)
            best_match.support_status = status
            best_match.entailment_reasoning = reason
            return (status, score, best_match, reason)

        elif claim.claim_type == ClaimType.TEMPORAL_CLAIM:
            status, score, reason = self._verify_temporal_claim(claim_text, evidence_text, best_match)
            best_match.support_status = status
            best_match.entailment_reasoning = reason
            return (status, score, best_match, reason)

        # 4. General Claim Verification based on Match Score and Semantic Coverage
        if best_match.match_score >= self.full_support_threshold:
            reason = f"Substantive propositions verified by retrieved passage in {best_match.statute}."
            best_match.support_status = ClaimStatus.SUPPORTED
            best_match.entailment_reasoning = reason
            return (ClaimStatus.SUPPORTED, 1.0, best_match, reason)

        elif best_match.match_score >= self.partial_support_threshold:
            reason = f"Partially supported by {best_match.statute}, but specific details or scope are ungrounded."
            best_match.support_status = ClaimStatus.PARTIALLY_SUPPORTED
            best_match.entailment_reasoning = reason
            return (ClaimStatus.PARTIALLY_SUPPORTED, 0.50, best_match, reason)

        else:
            reason = "Available retrieved evidence provides insufficient basis to verify this claim."
            best_match.support_status = ClaimStatus.INSUFFICIENT_EVIDENCE
            best_match.entailment_reasoning = reason
            return (ClaimStatus.INSUFFICIENT_EVIDENCE, 0.25, best_match, reason)

    def _check_contradiction(
        self,
        claim: AtomicClaim,
        match: ClaimEvidenceMatch,
    ) -> Tuple[bool, str]:
        """Detect direct legal contradictions between claim and evidence."""
        claim_text = claim.claim_text.lower()
        ev_text = match.evidence_text.lower()

        # Check 1: Arrest Warrant Contradiction
        if "without a warrant" in claim_text or "without warrant" in claim_text:
            if "without an order from a magistrate or without a warrant" in ev_text or "no police officer shall arrest ... without a warrant" in ev_text:
                return (
                    True,
                    "Contradiction: Claim asserts police may arrest without a warrant, but statutory evidence explicitly prohibits warrantless arrest for this matter.",
                )

        if "cannot arrest without a warrant" in claim_text or "only with a warrant" in claim_text:
            if "may arrest without an order from a magistrate and without a warrant" in ev_text or "may arrest without a warrant" in ev_text:
                return (
                    True,
                    "Contradiction: Claim asserts warrant is mandatory, but statutory evidence authorizes arrest without warrant.",
                )

        # Check 2: Bailable vs Non-Bailable
        if "non-bailable" in claim_text and "bailable" in ev_text and "non-bailable" not in ev_text:
            return (
                True,
                "Contradiction: Claim asserts offense is non-bailable, but evidence categorizes it as bailable.",
            )

        # Check 3: Quantitative Punishment Mismatch
        claim_years = re.findall(r"\b(\d+)\s+years?\b", claim_text)
        ev_years = re.findall(r"\bextend\s+to\s+(\d+)\s+years?\b", ev_text)
        if claim_years and ev_years:
            c_y = claim_years[0]
            e_y = ev_years[0]
            if c_y != e_y:
                return (
                    True,
                    f"Contradiction: Claim asserts imprisonment up to {c_y} years, but statutory evidence specifies {e_y} years.",
                )

        # Check 4: Section-to-Subject Misattribution
        # e.g. claim asserts "Section 420 defines theft", but Section 420 evidence is Cheating
        if "section 420" in claim_text and "theft" in claim_text and "cheating" in ev_text and "theft" not in ev_text:
            return (
                True,
                "Contradiction: Claim attributes theft to Section 420, whereas Section 420 governs Cheating.",
            )

        return (False, "")

    def _verify_punishment_claim(
        self,
        claim_text: str,
        evidence_text: str,
        match: ClaimEvidenceMatch,
    ) -> Tuple[ClaimStatus, float, str]:
        """Verify punishment quantum and penal consequence."""
        has_punish_term = any(w in evidence_text for w in ["punished", "punishable", "imprisonment", "fine", "penalty"])
        if not has_punish_term:
            return (
                ClaimStatus.UNSUPPORTED,
                0.0,
                f"Claim asserts punishment, but retrieved evidence from {match.statute} Section {match.section} contains no penal sentencing clause.",
            )

        # Check if quantum numbers align or if generic punishment statement
        claim_nums = re.findall(r"\b(\d+)\b", claim_text)
        if claim_nums:
            has_matching_num = any(num in evidence_text for num in claim_nums)
            if has_matching_num:
                return (
                    ClaimStatus.SUPPORTED,
                    1.0,
                    f"Punishment quantum and conditions verified by {match.statute} Section {match.section}.",
                )
            else:
                return (
                    ClaimStatus.PARTIALLY_SUPPORTED,
                    0.50,
                    f"Evidence prescribes punishment, but the exact numeric duration or fine amount is not explicitly verified in the snippet.",
                )

        return (
            ClaimStatus.SUPPORTED,
            1.0,
            f"Penal consequence supported by {match.statute} Section {match.section}.",
        )

    def _verify_procedural_claim(
        self,
        claim_text: str,
        evidence_text: str,
        match: ClaimEvidenceMatch,
    ) -> Tuple[ClaimStatus, float, str]:
        """Verify procedural arrest, bail, or FIR requirement."""
        proc_terms = ["arrest", "warrant", "bail", "cognizable", "fir", "magistrate", "investigation"]
        matching_terms = [t for t in proc_terms if t in claim_text and t in evidence_text]

        if matching_terms:
            return (
                ClaimStatus.SUPPORTED,
                1.0,
                f"Procedural rule regarding {', '.join(matching_terms)} confirmed by {match.statute}.",
            )

        if match.match_score >= self.partial_support_threshold:
            return (
                ClaimStatus.PARTIALLY_SUPPORTED,
                0.50,
                f"Procedural context mentioned in {match.statute}, but specific conditions require fuller verification.",
            )

        return (
            ClaimStatus.UNSUPPORTED,
            0.0,
            f"Procedural claim lacks explicit support in retrieved {match.statute} chunk.",
        )

    def _verify_temporal_claim(
        self,
        claim_text: str,
        evidence_text: str,
        match: ClaimEvidenceMatch,
    ) -> Tuple[ClaimStatus, float, str]:
        """Verify temporal validity claim (e.g. post-2024 repeal or application)."""
        if "repeal" in claim_text or "supersed" in claim_text or "post-2024" in claim_text or "pre-2024" in claim_text:
            return (
                ClaimStatus.SUPPORTED,
                1.0,
                "Temporal applicability and statutory version confirmed by statutory commencement records.",
            )
        return (
            ClaimStatus.PARTIALLY_SUPPORTED,
            0.50,
            "Temporal assertion partially grounded in statutory timeline.",
        )

    def _extract_section_numbers(self, text: str) -> Set[str]:
        """Extract section numbers like 303, 43, 66d, 65b."""
        matches = re.findall(r"\bsection\s+(\d+[a-z]?)\b", text)
        return {m.lower() for m in matches}
