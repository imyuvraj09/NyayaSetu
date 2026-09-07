"""Legal Role Compatibility Checker for Substantive vs Procedural vs Evidentiary Evidence.

Classifies legal provisions into:
- SUBSTANTIVE
- PROCEDURAL
- EVIDENTIARY
- CONSTITUTIONAL
- SPECIAL_LAW
- GENERAL_LAW

Evaluates role appropriateness against query intent (e.g., penalizing procedural arrest
provisions when the user asks for substantive statutory punishments).
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from research.evidence_compatibility.models import (
    CompatibilityStatus,
    CompatibilityViolation,
    LegalRole,
)
from research.evidence_compatibility.rules import (
    INTENT_ROLE_MAP,
    STATUTE_REGISTRY,
    resolve_statute_key,
)


# Section-specific role overrides
SECTION_ROLE_OVERRIDES: Dict[str, Dict[str, LegalRole]] = {
    "BNSS": {
        "35": LegalRole.PROCEDURAL,
        "36": LegalRole.PROCEDURAL,
        "43": LegalRole.PROCEDURAL,
        "173": LegalRole.PROCEDURAL,
        "482": LegalRole.PROCEDURAL,
    },
    "BNS": {
        "101": LegalRole.SUBSTANTIVE,
        "103": LegalRole.SUBSTANTIVE,
        "303": LegalRole.SUBSTANTIVE,
        "305": LegalRole.SUBSTANTIVE,
        "318": LegalRole.SUBSTANTIVE,
        "61": LegalRole.SUBSTANTIVE,
        "111": LegalRole.SUBSTANTIVE,
    },
    "BSA": {
        "26": LegalRole.EVIDENTIARY,
        "62": LegalRole.EVIDENTIARY,
        "63": LegalRole.EVIDENTIARY,
    },
}


class LegalRoleCompatibilityChecker:
    """Classifies statutory evidence roles and evaluates role compatibility with query inquiry."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.role_mismatch_penalty = self.config.get("role_mismatch_penalty", 0.35)

    def determine_evidence_role(
        self,
        document_name: str,
        source_filename: str,
        section: Optional[str] = None,
        chunk_text: str = "",
    ) -> LegalRole:
        """Determine doctrinal role of evidence chunk from statute and section."""
        statute_key = resolve_statute_key(document_name, source_filename)
        if not statute_key:
            return LegalRole.UNKNOWN

        # Section-level override if available
        if section and statute_key in SECTION_ROLE_OVERRIDES:
            sec_clean = re.sub(r"[^\d]", "", str(section))
            if sec_clean in SECTION_ROLE_OVERRIDES[statute_key]:
                return SECTION_ROLE_OVERRIDES[statute_key][sec_clean]

        # Statute-level default role
        stat_data = STATUTE_REGISTRY.get(statute_key, {})
        return stat_data.get("primary_role", LegalRole.UNKNOWN)

    def infer_query_desired_roles(self, query: str) -> List[LegalRole]:
        """Infer expected doctrinal legal roles from query intent and keywords."""
        q_lower = (query or "").lower()
        desired_roles: Set[LegalRole] = set()

        # 1. Substantive punishment / offense inquiries
        if any(w in q_lower for w in ["punishment", "punished", "penalty", "imprisonment", "fine", "definition of", "what is the offense", "offence of"]):
            desired_roles.add(LegalRole.SUBSTANTIVE)
            desired_roles.add(LegalRole.SPECIAL_LAW)

        # 2. Procedural arrest / bail / FIR / police power inquiries
        if any(w in q_lower for w in ["arrest", "warrant", "bail", "anticipatory bail", "custody", "remand", "fir", "police officer may", "procedure", "investigation"]):
            desired_roles.add(LegalRole.PROCEDURAL)

        # 3. Evidentiary proof / admissibility inquiries
        if any(w in q_lower for w in ["admitted", "admissible", "admissibility", "electronic record", "certificate", "dying declaration", "prove", "burden of proof", "evidence in court"]):
            desired_roles.add(LegalRole.EVIDENTIARY)

        # 4. Constitutional fundamental rights / writ remedies
        if any(w in q_lower for w in ["constitution", "fundamental right", "article 21", "article 14", "article 19", "writ", "habeas corpus"]):
            desired_roles.add(LegalRole.CONSTITUTIONAL)

        # 5. Cyber offenses
        if any(w in q_lower for w in ["hacked", "cyber", "unauthorized access", "identity theft", "computer"]):
            desired_roles.add(LegalRole.SPECIAL_LAW)

        # 6. Workplace harassment
        if any(w in q_lower for w in ["sexual harassment", "workplace", "icc", "internal committee"]):
            desired_roles.add(LegalRole.SPECIAL_LAW)

        if not desired_roles:
            # Neutral fallback: accept any standard legal role
            return [LegalRole.SUBSTANTIVE, LegalRole.PROCEDURAL, LegalRole.EVIDENTIARY, LegalRole.SPECIAL_LAW, LegalRole.CONSTITUTIONAL]

        return list(desired_roles)

    def check_role_compatibility(
        self,
        query: str,
        evidence_role: LegalRole,
        document_name: str,
        section: Optional[str] = None,
    ) -> Tuple[float, CompatibilityStatus, List[CompatibilityViolation], List[str], List[str]]:
        """Evaluate whether evidence role aligns with the user inquiry's legal intent."""
        violations: List[CompatibilityViolation] = []
        supporting_signals: List[str] = []
        rejected_signals: List[str] = []

        desired_roles = self.infer_query_desired_roles(query)

        # If role is unknown, neutral evaluation
        if evidence_role == LegalRole.UNKNOWN:
            supporting_signals.append("Evidence legal role undetermined; evaluated neutrally")
            return 0.80, CompatibilityStatus.UNCERTAIN, violations, supporting_signals, rejected_signals

        # Direct role match
        if evidence_role in desired_roles:
            supporting_signals.append(
                f"Role alignment: Evidence role {evidence_role.value} matches desired query roles {[r.value for r in desired_roles]}"
            )
            return 1.0, CompatibilityStatus.COMPATIBLE, violations, supporting_signals, rejected_signals

        # Role mismatch: e.g. procedural evidence when substantive punishment is sought
        q_lower = (query or "").lower()
        is_punishment_query = "punishment" in q_lower or "penalty" in q_lower or "sentence" in q_lower
        if evidence_role == LegalRole.PROCEDURAL and is_punishment_query:
            penalty = self.role_mismatch_penalty * 1.2
            score = max(0.30, 1.0 - penalty)
            msg = (
                f"Query seeks substantive statutory punishment/penalty, but retrieved evidence "
                f"from {document_name} is Procedural ({evidence_role.value}). Applying soft compatibility penalty."
            )
            rejected_signals.append(msg)
            violations.append(
                CompatibilityViolation(
                    dimension="legal_role",
                    severity="HIGH",
                    rule_name="PROCEDURAL_PROVISION_FOR_SUBSTANTIVE_PUNISHMENT_QUERY",
                    message=msg,
                    penalty=penalty,
                )
            )
            return score, CompatibilityStatus.PARTIALLY_COMPATIBLE, violations, supporting_signals, rejected_signals

        # Standard role mismatch
        score = max(0.40, 1.0 - self.role_mismatch_penalty)
        msg = f"Evidence role {evidence_role.value} does not directly correspond to desired query roles {[r.value for r in desired_roles]}"
        rejected_signals.append(msg)
        violations.append(
            CompatibilityViolation(
                dimension="legal_role",
                severity="MEDIUM",
                rule_name="ROLE_MISMATCH",
                message=msg,
                penalty=self.role_mismatch_penalty,
            )
        )
        return score, CompatibilityStatus.PARTIALLY_COMPATIBLE, violations, supporting_signals, rejected_signals
