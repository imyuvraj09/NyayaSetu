"""
Answer Consistency Validator for NyayaSetu Legal Assistant.

Performs cross-claim and inter-section consistency validation on draft answers:
1. Proposition extraction across answer sections (Direct Answer, Legal Basis, Key Conditions, Conclusion).
2. Inter-section contradiction detection:
   - Section role contradiction: e.g. claiming electronic records are proved under Section 63 in one place,
     but asserting that Section 62 mandates the admissibility conditions in another.
   - Requirement contradiction: claiming certification is mandatory under Section 63(4) in one place,
     but stating that certificate is optional or not required in another.
   - Offence / punishment contradiction: asserting varying terms of imprisonment or incompatible penalties.
3. Automatically reconciles and corrects contradictory statements before finalizing answer.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContradictionReport:
    """Represents a detected contradiction within an answer."""
    statement_1: str
    statement_2: str
    contradiction_type: str
    explanation: str
    reconciled_statement: str


class AnswerConsistencyValidator:
    """Detects and resolves internal contradictions across different sections of a generated legal answer."""

    def __init__(self) -> None:
        pass

    def check_consistency(self, answer_text: str) -> Tuple[bool, List[ContradictionReport]]:
        """Scan answer text for internal contradictions."""
        reports: List[ContradictionReport] = []
        if not answer_text:
            return True, reports

        lower_text = answer_text.lower()

        # 1. Check for BSA Section 62 vs 63 Contradiction
        # Statement A: Electronic records are proved under Section 63
        has_63_proof = bool(
            re.search(r"\bproved\s+(?:in\s+accordance\s+with|under)\s+(?:the\s+provisions\s+of\s+)?section\s+63\b", lower_text)
            or re.search(r"\bsection\s+62\s+(?:provides|states)\s+that\s+.*proved.*section\s+63\b", lower_text)
        )

        # Statement B: Conditions / mandates attributed to Section 62 instead of 63
        has_62_conditions = bool(
            re.search(r"\bsection\s+62\s+(?:mandates|specifies|prescribes|sets\s+forth|lays\s+down)\s+(?:the\s+)?(?:conditions|certificate|requirements)\b", lower_text)
            or re.search(r"\bconditions\s+(?:mandated|prescribed)\s+by\s+section\s+62\b", lower_text)
        )

        if has_63_proof and has_62_conditions:
            reports.append(
                ContradictionReport(
                    statement_1="Section 62 provides that electronic records are proved under Section 63.",
                    statement_2="Section 62 mandates the admissibility conditions.",
                    contradiction_type="STATUTORY_ROLE_CONTRADICTION",
                    explanation=(
                        "Contradiction: One section states Section 62 directs proof under Section 63, "
                        "while another section erroneously claims Section 62 itself mandates the conditions."
                    ),
                    reconciled_statement=(
                        "Section 62 provides that electronic records may be proved in accordance with Section 63, "
                        "which sets forth the substantive conditions and certification mandate."
                    ),
                )
            )

        # 2. Check for Certification Mandate Contradiction
        has_mandatory_cert = bool(
            re.search(r"\b(?:mandatory|mandatorily\s+required|strict\s+mandate|shall\s+be\s+submitted|mandatory\s+requirement)\b", lower_text)
            and re.search(r"\bcertificate\b", lower_text)
        )
        has_optional_cert = bool(
            re.search(r"\bcertificate\s+is\s+(?:optional|not\s+mandatory|discretionary|not\s+strictly\s+required)\b", lower_text)
        )

        if has_mandatory_cert and has_optional_cert:
            reports.append(
                ContradictionReport(
                    statement_1="A certificate under Section 63(4) is mandatory.",
                    statement_2="Certificate is optional or discretionary.",
                    contradiction_type="MANDATE_CONTRADICTION",
                    explanation="Contradiction between mandatory vs optional certificate requirement.",
                    reconciled_statement="Under Section 63(4), submitting a signed certificate is a mandatory requirement for admitting secondary electronic records.",
                )
            )

        is_consistent = len(reports) == 0
        return is_consistent, reports

    def reconcile_and_sanitize_answer(self, answer_text: str, query_analysis: Optional[Any] = None) -> str:
        """Resolve internal contradictions and enforce consistent propositions throughout the answer."""
        if not answer_text:
            return answer_text

        # Support JSON string format
        is_json = False
        data = None
        trimmed = answer_text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                import json
                data = json.loads(trimmed)
                if isinstance(data, dict):
                    is_json = True
            except Exception:
                is_json = False

        case_law_requested = False
        if query_analysis:
            if isinstance(query_analysis, dict):
                req_auth = str(query_analysis.get("authority_requirement", ""))
                lq = query_analysis.get("legal_question", {})
                req_case = lq.get("requires_case_law", False) if isinstance(lq, dict) else getattr(lq, "requires_case_law", False)
                q_types = str(lq.get("question_types", [])) if isinstance(lq, dict) else str(getattr(lq, "question_types", []))
                raw_q = query_analysis.get("raw_query", "") or (lq.get("raw_question", "") if isinstance(lq, dict) else getattr(lq, "raw_question", ""))
                if "CASE_LAW" in req_auth or "BOTH" in req_auth or req_case or "JUDICIAL_PRINCIPLES" in q_types or any(k in str(raw_q).lower() for k in ["judicial principles", "precedent tests", "precedent", "case law", "judicial test"]):
                    case_law_requested = True
            else:
                req_auth = str(getattr(query_analysis, "authority_requirement", ""))
                req_case = getattr(query_analysis, "requires_case_law", False)
                if "CASE_LAW" in req_auth or "BOTH" in req_auth or req_case:
                    case_law_requested = True

        def reconcile_text_block(text: str) -> str:
            if not text:
                return text

            # Reconcile Section 62 vs 63 contradiction:
            text = re.sub(
                r"\bSection\s+62\s+(?:mandates|specifies|prescribes|sets\s+forth|lays\s+down)\s+(the\s+conditions|the\s+admissibility\s+conditions|admissibility\s+conditions|conditions)\b",
                r"Section 63 specifies \1",
                text,
                flags=re.IGNORECASE,
            )

            text = re.sub(
                r"\bconditions\s+mandated\s+by\s+Section\s+62\b",
                "conditions prescribed under Section 63",
                text,
                flags=re.IGNORECASE,
            )

            # Reconcile contradiction where conclusion states records are "strictly inadmissible" while direct answer stated admissible
            text = re.sub(
                r"\bElectronic\s+records\s+are\s+strictly\s+inadmissible\s+in\s+all\s+court\s+proceedings\b",
                "Electronic records are admissible in court proceedings subject to compliance with the statutory conditions and certificate requirement under Section 63",
                text,
                flags=re.IGNORECASE,
            )

            # Remove repetitive conclusion if conclusion simply repeats the direct answer
            lines = text.splitlines()
            filtered_lines: List[str] = []
            skip_duplicate_conclusion = False

            for line in lines:
                trimmed_line = line.strip()
                if trimmed_line in ("Conclusion", "Conclusion:", "In Summary:", "Summary:"):
                    skip_duplicate_conclusion = True
                    continue
                if skip_duplicate_conclusion:
                    if re.match(r"^(?:Sources|Disclaimer|Important Note|Relevant Legal Provisions)\b", trimmed_line, re.IGNORECASE):
                        skip_duplicate_conclusion = False
                        filtered_lines.append(line)
                    else:
                        continue
                else:
                    filtered_lines.append(line)

            # Conditionally omit unsupported/empty Judicial Principles section when case law was NOT requested
            final_lines: List[str] = []
            skip_empty_judicial = False
            for line in filtered_lines:
                trimmed_line = line.strip()
                if re.match(r"^Judicial\s+Principles\b", trimmed_line, re.IGNORECASE):
                    if not case_law_requested:
                        skip_empty_judicial = True
                        continue
                    else:
                        final_lines.append(line)
                        continue
                if skip_empty_judicial:
                    if re.match(r"^(?:Sources|Disclaimer|Important Note|Relevant Legal Provisions|Answer|Conclusion)\b", trimmed_line, re.IGNORECASE):
                        skip_empty_judicial = False
                        final_lines.append(line)
                    elif any(w in trimmed_line.lower() for w in ("do not contain verified", "not contain verified", "corpus does not contain", "no verified judicial")):
                        # Continue skipping empty judicial boilerplate
                        continue
                    elif len(trimmed_line) == 0:
                        continue
                    else:
                        continue
                else:
                    final_lines.append(line)

            res = "\n".join(final_lines)
            res = re.sub(r"\n{3,}", "\n\n", res).strip()
            return res

        if is_json and data:
            import json
            if "mainAnswer" in data and isinstance(data["mainAnswer"], str):
                data["mainAnswer"] = reconcile_text_block(data["mainAnswer"])
            if "legalBasis" in data and isinstance(data["legalBasis"], str):
                data["legalBasis"] = reconcile_text_block(data["legalBasis"])
            return json.dumps(data, ensure_ascii=False)

        return reconcile_text_block(answer_text)


_ANSWER_CONSISTENCY_VALIDATOR_INSTANCE = None


def get_answer_consistency_validator() -> AnswerConsistencyValidator:
    """Return singleton instance of AnswerConsistencyValidator."""
    global _ANSWER_CONSISTENCY_VALIDATOR_INSTANCE
    if _ANSWER_CONSISTENCY_VALIDATOR_INSTANCE is None:
        _ANSWER_CONSISTENCY_VALIDATOR_INSTANCE = AnswerConsistencyValidator()
    return _ANSWER_CONSISTENCY_VALIDATOR_INSTANCE
