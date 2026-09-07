"""Legal Issue Compatibility Checker for NyayaSetu Evidence Compatibility Filtering.

Explicitly distinguishes:
- TOPICAL_SIMILARITY (generic lexical or semantic overlap)
- LEGAL_ISSUE_COMPATIBILITY (doctrinal alignment with the identified legal issue)

Detects when retrieved evidence contains words superficially similar to the query
(e.g., "theft", "personation", "cheating", "records") but addresses an entirely
different statutory legal issue (e.g., physical theft vs cyber identity theft).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from research.evidence_compatibility.models import (
    CompatibilityStatus,
    CompatibilityViolation,
)
from research.schemas import IdentifiedLegalIssue, NormalizedFacts


# Mapping of legal issues to defining conceptual terms and negative collision indicators
ISSUE_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "cyber_identity_theft_personation": {
        "required_signals": ["computer", "electronic", "identity", "password", "digital signature", "unique identification", "cheating by personation using computer", "section 66c", "section 66d"],
        "negative_signals": ["movable property without consent", "dishonest intention to take movable property", "extortion", "robbery"],
        "topical_distractors": ["theft of cattle", "theft in dwelling house", "theft of vehicle", "simple theft"],
    },
    "cyber_unauthorized_access": {
        "required_signals": ["computer system", "computer network", "unauthorized access", "data damage", "hacking", "section 43", "section 66"],
        "negative_signals": ["criminal trespass on land", "house-trespass"],
        "topical_distractors": ["physical trespass", "burglary"],
    },
    "substantive_theft_offence": {
        "required_signals": ["theft", "movable property", "dishonestly takes", "out of possession", "punished with imprisonment", "section 303", "section 379"],
        "negative_signals": ["computer resource", "digital signature", "electronic mail"],
        "topical_distractors": ["identity theft", "electronic data theft"],
    },
    "procedural_police_arrest_powers": {
        "required_signals": ["arrest", "police officer may arrest", "without warrant", "cognizable offence", "notice of appearance", "section 35", "section 41"],
        "negative_signals": [],
        "topical_distractors": ["punishment for offence", "definition of offence"],
    },
    "procedural_bail_investigation": {
        "required_signals": ["bail", "anticipatory bail", "bond", "surety", "custody", "remand", "investigation", "police report"],
        "negative_signals": [],
        "topical_distractors": [],
    },
    "evidentiary_electronic_records_admissibility": {
        "required_signals": ["electronic record", "admissibility", "admissible", "certificate", "computer output", "section 63", "section 65b"],
        "negative_signals": ["commencement of act", "short title"],
        "topical_distractors": ["substantive cyber crime penalty"],
    },
    "evidentiary_dying_declaration": {
        "required_signals": ["dying declaration", "statement of person who cannot be found", "cause of death", "section 26", "section 32"],
        "negative_signals": [],
        "topical_distractors": [],
    },
    "constitutional_fundamental_rights": {
        "required_signals": ["fundamental rights", "article 21", "article 14", "article 19", "life and liberty", "equality before law", "writ"],
        "negative_signals": [],
        "topical_distractors": [],
    },
    "workplace_sexual_harassment_protection": {
        "required_signals": ["sexual harassment", "workplace", "internal committee", "icc", "aggrieved woman", "complaint", "posh"],
        "negative_signals": [],
        "topical_distractors": ["electronic evidence certificate", "general bodily hurt"],
    },
    "child_sexual_abuse_protection": {
        "required_signals": ["child", "sexual assault", "pocso", "special court", "penetrative"],
        "negative_signals": [],
        "topical_distractors": [],
    },
}


class IssueCompatibilityChecker:
    """Evaluates whether retrieved statutory text is doctrinally compatible with identified legal issues."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.distractor_penalty = self.config.get("topical_distractor_penalty", 0.45)

    def check_issue_compatibility(
        self,
        chunk_text: str,
        document_name: str,
        section: Optional[str],
        identified_issues: List[IdentifiedLegalIssue],
        normalized_facts: Optional[NormalizedFacts],
    ) -> Tuple[float, CompatibilityStatus, List[CompatibilityViolation], List[str], List[str]]:
        """Evaluate legal issue compatibility score and identify topical distractions."""
        violations: List[CompatibilityViolation] = []
        supporting_signals: List[str] = []
        rejected_signals: List[str] = []

        if not identified_issues:
            supporting_signals.append("No specific legal issue constrained; issue score neutral")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        text_lower = (chunk_text or "").lower()
        top_issue = identified_issues[0]
        issue_id = top_issue.issue_id
        issue_name = top_issue.issue_name

        signature = ISSUE_SIGNATURES.get(issue_id)
        if not signature:
            supporting_signals.append(f"Issue '{issue_id}' lacks explicit signature; neutral evaluation applied")
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        required_signals = signature.get("required_signals", [])
        negative_signals = signature.get("negative_signals", [])
        topical_distractors = signature.get("topical_distractors", [])

        # Count presence of required conceptual signals
        matched_required = [sig for sig in required_signals if sig in text_lower]
        matched_negatives = [sig for sig in negative_signals if sig in text_lower]
        matched_distractors = [sig for sig in topical_distractors if sig in text_lower]

        score = 1.0

        # Positive support
        if matched_required:
            supporting_signals.append(
                f"Evidence text contains issue-defining signals for '{issue_name}': {matched_required[:3]}"
            )
            score = min(1.0, 0.85 + 0.05 * len(matched_required))

        # Check for topical distractor collision (high topical word match but opposite conceptual target)
        if matched_distractors or (matched_negatives and not matched_required):
            penalty = self.distractor_penalty * top_issue.confidence
            score = max(0.20, score - penalty)
            msg = (
                f"Evidence contains topical distractor signals {matched_distractors or matched_negatives} "
                f"diverging from core legal issue '{issue_name}'."
            )
            rejected_signals.append(msg)
            violations.append(
                CompatibilityViolation(
                    dimension="issue",
                    severity="HIGH" if top_issue.confidence > 0.70 else "MEDIUM",
                    rule_name="TOPICAL_SIMILARITY_WITHOUT_ISSUE_COMPATIBILITY",
                    message=msg,
                    penalty=penalty,
                )
            )

        if not matched_required and not matched_distractors and not matched_negatives:
            # Chunk is neither confirmed nor rejected by issue signature
            score = 0.80
            supporting_signals.append("No strong positive or negative issue markers in chunk text")

        status = CompatibilityStatus.COMPATIBLE if score >= 0.80 else (
            CompatibilityStatus.PARTIALLY_COMPATIBLE if score >= 0.50 else CompatibilityStatus.INCOMPATIBLE
        )

        return score, status, violations, supporting_signals, rejected_signals
