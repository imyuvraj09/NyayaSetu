"""
Query-Answer Relevance and Intent Coverage Validation for NyayaSetu.

Validates that:
1. The synthesized answer directly addresses the operative legal issue and domain of the current query.
2. No stale conversation context or previous query answer (e.g., BSA electronic records leakage) contaminates the response.
3. All constituent intents of a multi-intent inquiry are addressed with adequate coverage.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from retrieval.legal_question import LegalQuestion
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueryAnswerValidationResult:
    """Outcome of query-answer relevance and intent coverage validation."""

    is_valid: bool
    relevance_score: float = 1.0
    intent_coverage: Dict[str, bool] = field(default_factory=dict)
    contamination_detected: bool = False
    warnings: List[str] = field(default_factory=list)
    details: str = ""


class QueryAnswerRelevanceValidator:
    """Validates semantic and domain consistency between query and synthesized answer."""

    @classmethod
    def validate(
        cls,
        query: str,
        answer: str,
        legal_question: Optional[LegalQuestion] = None,
        query_analysis: Optional[Any] = None,
    ) -> QueryAnswerValidationResult:
        """Validate that the answer addresses the query without stale context contamination."""
        if not answer or not answer.strip():
            return QueryAnswerValidationResult(
                is_valid=False,
                relevance_score=0.0,
                contamination_detected=False,
                warnings=["Synthesized answer is empty."],
                details="Empty answer cannot satisfy query relevance.",
            )

        q_lower = query.lower()
        a_lower = answer.lower()
        warnings: List[str] = []
        contamination_detected = False
        relevance_score = 1.0

        # -----------------------------------------------------------------
        # 1. Stale Context & Query-Answer Mismatch Detection
        # -----------------------------------------------------------------
        is_posh_query = any(w in q_lower for w in ["sexual harassment", "posh", "internal complaints committee", "icc", "local committee", "lcc"]) or (
            "workplace" in q_lower and ("harass" in q_lower or "harassment" in q_lower)
        )
        is_bsa_electronic_query = any(
            w in q_lower for w in [
                "admissibility of electronic", "section 63", "section 65b", "section 62",
                "electronic records admitted", "computer output", "sakshya adhiniyam"
            ]
        )

        is_bsa_electronic_answer = (
            "bharatiya sakshya adhiniyam" in a_lower or "bsa" in a_lower
        ) and (
            "section 63" in a_lower or "section 62" in a_lower or "admissibility of electronic records" in a_lower
        ) and not any(w in a_lower for w in ["sexual harassment", "posh", "internal complaints committee", "icc"])

        # Severe mismatch: Workplace Sexual Harassment Query answered with BSA electronic evidence
        if is_posh_query and is_bsa_electronic_answer:
            logger.error(
                "CRITICAL MISMATCH: Workplace sexual harassment query received unrelated BSA electronic evidence admissibility answer!"
            )
            return QueryAnswerValidationResult(
                is_valid=False,
                relevance_score=0.0,
                contamination_detected=True,
                intent_coverage={"legal_protections": False, "complaint_mechanisms": False, "relevant_evidence": False},
                warnings=[
                    "Severe query-answer mismatch: Answer discusses electronic records admissibility under Bharatiya Sakshya Adhiniyam, 2023 for a workplace sexual harassment question."
                ],
                details="Answer completely fails domain and topic alignment with the user's inquiry regarding workplace sexual harassment under the POSH Act.",
            )

        # Reverse mismatch: Electronic evidence query answered with sexual harassment
        if is_bsa_electronic_query and any(w in a_lower for w in ["sexual harassment", "posh", "internal complaints committee"]) and not any(w in a_lower for w in ["section 63", "electronic record"]):
            logger.error("CRITICAL MISMATCH: BSA electronic query received workplace harassment answer!")
            return QueryAnswerValidationResult(
                is_valid=False,
                relevance_score=0.0,
                contamination_detected=True,
                intent_coverage={"electronic_evidence": False},
                warnings=["Severe query-answer mismatch: Answer discusses workplace harassment for an electronic evidence inquiry."],
                details="Answer fails domain alignment with evidence law query.",
            )

        # -----------------------------------------------------------------
        # 2. Multi-Intent Coverage Validation
        # -----------------------------------------------------------------
        intent_coverage: Dict[str, bool] = {}

        if is_posh_query:
            # Intent 1: Legal Protections
            has_protections = any(w in a_lower for w in [
                "protection", "protections", "prohibition", "hostile work environment",
                "section 3", "section 12", "interim relief", "employer obligations", "section 19", "safeguard"
            ])
            intent_coverage["legal_protections"] = bool(has_protections)

            # Intent 2: Complaint Mechanisms
            has_mechanisms = any(w in a_lower for w in [
                "complaint", "mechanism", "internal complaints committee", "icc",
                "local committee", "section 4", "section 6", "section 9", "conciliation", "inquiry"
            ])
            intent_coverage["complaint_mechanisms"] = bool(has_mechanisms)

            # Intent 3: Relevant Evidence
            has_evidence = any(w in a_lower for w in [
                "evidence", "witness", "contemporaneous", "records", "chats",
                "messages", "emails", "corroborat", "proof", "documentation"
            ])
            intent_coverage["relevant_evidence"] = bool(has_evidence)

            missing_intents = [intent for intent, covered in intent_coverage.items() if not covered]
            if missing_intents:
                warnings.append(f"Incomplete intent coverage: Missing coverage for {missing_intents}.")
                relevance_score *= (1.0 - (0.25 * len(missing_intents)))

        # -----------------------------------------------------------------
        # 3. Overall Validity Determination
        # -----------------------------------------------------------------
        is_valid = relevance_score >= 0.5 and not contamination_detected

        return QueryAnswerValidationResult(
            is_valid=is_valid,
            relevance_score=round(relevance_score, 2),
            intent_coverage=intent_coverage,
            contamination_detected=contamination_detected,
            warnings=warnings,
            details=f"Relevance Score: {relevance_score:.2f} | Contamination: {contamination_detected} | Intents Covered: {intent_coverage}",
        )
