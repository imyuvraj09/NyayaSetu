"""Risk-aware answer validation and cautious qualification module.

Adjusts generated answers based on claim grounding decisions, qualifying or
excising unsupported high-risk propositions while preserving original text and full audit logs.
"""

from typing import List, Tuple

from research.claim_grounding.models import (
    ClaimHandlingAction,
    ClaimGroundingDecision,
    ClaimStatus,
    RiskLevel,
)


class AnswerValidator:
    """Validates and prudently qualifies legal answers based on claim-level evidential support."""

    def __init__(
        self,
        excise_high_risk_unsupported: bool = False,
        qualify_unsupported_claims: bool = True,
    ):
        self.excise_high_risk_unsupported = excise_high_risk_unsupported
        self.qualify_unsupported_claims = qualify_unsupported_claims

    def validate_and_qualify(
        self,
        original_answer: str,
        decisions: List[ClaimGroundingDecision],
    ) -> Tuple[str, bool]:
        """Produce a validated, qualified answer text based on claim decisions.

        Returns:
            (validated_answer_text, modifications_made_bool)
        """
        if not decisions or not original_answer:
            return original_answer, False

        modifications_made = False
        # Assign handling action to each decision
        for d in decisions:
            if d.status == ClaimStatus.SUPPORTED:
                d.handling_action = ClaimHandlingAction.RETAIN
                d.qualified_claim_text = d.claim.claim_text

            elif d.status == ClaimStatus.CONTRADICTED:
                modifications_made = True
                if self.excise_high_risk_unsupported:
                    d.handling_action = ClaimHandlingAction.REMOVE
                    d.qualified_claim_text = ""
                else:
                    d.handling_action = ClaimHandlingAction.QUALIFY
                    d.qualified_claim_text = (
                        f"[Correction: The statement asserting '{d.claim.claim_text}' is contradicted by governing statutory records. {d.reasoning}]"
                    )

            elif d.status == ClaimStatus.UNSUPPORTED:
                modifications_made = True
                if d.claim.risk_level == RiskLevel.HIGH:
                    if self.excise_high_risk_unsupported:
                        d.handling_action = ClaimHandlingAction.REMOVE
                        d.qualified_claim_text = ""
                    else:
                        d.handling_action = ClaimHandlingAction.QUALIFY
                        d.qualified_claim_text = (
                            f"{d.claim.claim_text} *(Note: This specific proposition could not be verified in the retrieved statutory corpus and requires confirmation.)*"
                        )
                elif d.claim.risk_level == RiskLevel.MEDIUM:
                    d.handling_action = ClaimHandlingAction.QUALIFY
                    d.qualified_claim_text = (
                        f"{d.claim.claim_text} *(Subject to specific statutory verification.)*"
                    )
                else:
                    # Low risk
                    d.handling_action = ClaimHandlingAction.FLAG_UNCERTAIN
                    d.qualified_claim_text = d.claim.claim_text

            elif d.status == ClaimStatus.PARTIALLY_SUPPORTED:
                if d.claim.risk_level == RiskLevel.HIGH and self.qualify_unsupported_claims:
                    modifications_made = True
                    d.handling_action = ClaimHandlingAction.QUALIFY
                    d.qualified_claim_text = (
                        f"{d.claim.claim_text} *(Partially grounded; exact statutory conditions should be verified.)*"
                    )
                else:
                    d.handling_action = ClaimHandlingAction.RETAIN
                    d.qualified_claim_text = d.claim.claim_text

            elif d.status == ClaimStatus.INSUFFICIENT_EVIDENCE:
                modifications_made = True
                d.handling_action = ClaimHandlingAction.FLAG_UNCERTAIN
                d.qualified_claim_text = (
                    f"{d.claim.claim_text} *(Ungrounded: insufficient documentary evidence in retrieved records.)*"
                )

        if not modifications_made:
            return original_answer, False

        # Reconstruct text by replacing claim spans in reverse order (to preserve offsets)
        sorted_decisions = sorted(
            decisions,
            key=lambda d: d.claim.source_span_start,
            reverse=True,
        )

        modified_text = original_answer
        for d in sorted_decisions:
            if d.qualified_claim_text is not None and d.qualified_claim_text != d.claim.claim_text:
                start = d.claim.source_span_start
                end = d.claim.source_span_end
                if 0 <= start <= end <= len(modified_text):
                    # Replace slice
                    modified_text = modified_text[:start] + d.qualified_claim_text + modified_text[end:]

        return modified_text.strip(), True
