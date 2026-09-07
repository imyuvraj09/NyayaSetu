"""Temporal and Legal Version Compatibility Checker for NyayaSetu Evidence Compatibility.

Determines whether retrieved statutory provisions are temporally valid:
- Considers enactment effective dates, repeal dates, and supersession links.
- Specifically handles the 1 July 2024 Indian criminal law transition (IPC -> BNS, CrPC -> BNSS, IEA -> BSA).
- Applies Article 20(1) constitutional principle: No ex-post facto criminal liability.

CRITICAL RESEARCH CONSTRAINT:
If temporal information is absent from the query, ZERO HALLUCINATION is enforced:
returns temporal_status = UNKNOWN and applies neutral evaluation (no aggressive rejection).
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from research.evidence_compatibility.models import (
    CompatibilityStatus,
    CompatibilityViolation,
    TemporalStatus,
)
from research.evidence_compatibility.rules import (
    STATUTE_REGISTRY,
    resolve_statute_key,
)
from research.schemas import ExtractedFacts


# The watershed date for modern Indian criminal law enactments
TRANSITION_DATE_2024 = datetime(2024, 7, 1)


class TemporalCompatibilityChecker:
    """Evaluates temporal applicability of statutes against query timeline anchors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.superseded_penalty = self.config.get("superseded_statute_penalty", 0.60)
        self.ex_post_facto_penalty = self.config.get("ex_post_facto_penalty", 0.70)

    def extract_temporal_anchor(self, query: str, facts: Optional[ExtractedFacts] = None) -> Optional[Dict[str, Any]]:
        """Extract explicit temporal reference from query and facts without hallucinating dates."""
        text_sources = []
        if facts and facts.temporal_context:
            text_sources.append(facts.temporal_context.lower())
        if query:
            text_sources.append(query.lower())

        combined_text = " ".join(text_sources)
        if not combined_text:
            return None

        # 1. Explicit post-2024 cues
        if any(p in combined_text for p in ["post-2024", "after july 2024", "after 1 july 2024", "in 2025", "in 2026", "recently in 2025", "post 2024", "post july 2024"]):
            return {"year": 2025, "raw": "post-2024", "estimated_date": datetime(2025, 1, 1)}

        # 2. Explicit pre-2024 cues
        if any(p in combined_text for p in ["pre-2024", "before 2024", "in 2020", "in 2021", "in 2022", "in 2023", "prior to bns", "pre 2024", "before july 2024"]):
            year_m = re.search(r"\b(201\d|202[0-3])\b", combined_text)
            year = int(year_m.group(1)) if year_m else 2022
            return {"year": year, "raw": "pre-2024", "estimated_date": datetime(year, 1, 1)}

        # 3. Explicit year mentions
        year_match = re.search(r"\b(19\d\d|20[0-2]\d|203\d)\b", combined_text)
        if year_match:
            year = int(year_match.group(1))
            surrounding = combined_text[max(0, year_match.start() - 10) : min(len(combined_text), year_match.end() + 10)]
            if not any(term in surrounding for term in ["act", "sanhita", "adhiniyam", "code", "amendment"]):
                if year > 2024:
                    return {"year": year, "raw": str(year), "estimated_date": datetime(year, 1, 1)}
                elif year < 2024:
                    return {"year": year, "raw": str(year), "estimated_date": datetime(year, 1, 1)}
                else:
                    return {"year": 2024, "raw": str(year), "estimated_date": datetime(2024, 6, 1)}

        return None

    def check_temporal_compatibility(
        self,
        query: str,
        document_name: str,
        source_filename: str = "",
        facts: Optional[ExtractedFacts] = None,
    ) -> Tuple[float, TemporalStatus, List[CompatibilityViolation], List[str], List[str]]:
        """Determine temporal compatibility of the retrieved statute."""
        violations: List[CompatibilityViolation] = []
        supporting_signals: List[str] = []
        rejected_signals: List[str] = []

        statute_key = resolve_statute_key(document_name, source_filename)
        if not statute_key:
            return 1.0, TemporalStatus.UNKNOWN, violations, ["Statute temporal status unrecorded; evaluated neutrally"], []

        stat_data = STATUTE_REGISTRY[statute_key]
        is_repealed = stat_data.get("is_repealed", False)
        superseded_by = stat_data.get("superseded_by")
        supersedes = stat_data.get("supersedes")

        q_lower = (query or "").lower()

        # Special Case: Query specifically asks for historical or repealed law (e.g. "under IPC 1860")
        if statute_key in ["IPC", "CRPC", "IEA"]:
            if any(term in q_lower for term in [statute_key.lower(), "indian penal code", "code of criminal procedure", "evidence act, 1872"]):
                supporting_signals.append(f"Query explicitly requests legacy enactment {statute_key}; temporally relevant")
                return 1.0, TemporalStatus.APPLICABLE, violations, supporting_signals, rejected_signals

        temporal_anchor = self.extract_temporal_anchor(query, facts)

        # 1. No temporal information in query -> UNKNOWN (no aggressive penalty)
        if temporal_anchor is None:
            # Modern enactments (BNS, BNSS, BSA, IT Act, etc.) are presumed applicable by default
            if not is_repealed:
                supporting_signals.append(f"No incident date in query; active statute {statute_key} presumed applicable")
                return 1.0, TemporalStatus.UNKNOWN, violations, supporting_signals, rejected_signals
            else:
                # Repealed statute with unknown date: mild warning, soft penalty
                score = 0.80
                msg = (
                    f"No incident date specified; {document_name} is repealed and superseded by {superseded_by}. "
                    f"Prioritizing current enacted law while retaining evidence."
                )
                rejected_signals.append(msg)
                violations.append(
                    CompatibilityViolation(
                        dimension="temporal",
                        severity="LOW",
                        rule_name="REPEALED_STATUTE_UNKNOWN_INCIDENT_DATE",
                        message=msg,
                        penalty=0.20,
                    )
                )
                return score, TemporalStatus.SUPERSEDED, violations, supporting_signals, rejected_signals

        # 2. Incident date is post-2024 transition (>= 1 July 2024)
        incident_date = temporal_anchor["estimated_date"]
        if incident_date >= TRANSITION_DATE_2024:
            if is_repealed:
                # Post-2024 incident governed by BNS/BNSS/BSA, NOT IPC/CrPC/IEA
                penalty = self.superseded_penalty
                score = max(0.20, 1.0 - penalty)
                msg = (
                    f"Incident occurred post-July 2024 ({temporal_anchor['raw']}), but retrieved evidence "
                    f"is from repealed enactment {document_name} (superseded by {superseded_by})."
                )
                rejected_signals.append(msg)
                violations.append(
                    CompatibilityViolation(
                        dimension="temporal",
                        severity="HIGH",
                        rule_name="SUPERSEDED_STATUTE_POST_2024",
                        message=msg,
                        penalty=penalty,
                    )
                )
                return score, TemporalStatus.REPEALED, violations, supporting_signals, rejected_signals
            else:
                supporting_signals.append(f"Active statute {statute_key} temporally matches post-2024 incident")
                return 1.0, TemporalStatus.APPLICABLE, violations, supporting_signals, rejected_signals

        # 3. Incident date is pre-2024 transition (< 1 July 2024)
        else:
            if supersedes:
                # Post-2024 statute cannot apply retrospectively to a pre-2024 substantive offense (Article 20(1))
                if stat_data.get("primary_role") == "SUBSTANTIVE":
                    penalty = self.ex_post_facto_penalty
                    score = max(0.20, 1.0 - penalty)
                    msg = (
                        f"Incident occurred in {temporal_anchor['raw']} prior to 1 July 2024. Under Article 20(1) of the "
                        f"Constitution, substantive penal provisions of {document_name} cannot apply ex-post facto."
                    )
                    rejected_signals.append(msg)
                    violations.append(
                        CompatibilityViolation(
                            dimension="temporal",
                            severity="HIGH",
                            rule_name="EX_POST_FACTO_NON_APPLICABLE",
                            message=msg,
                            penalty=penalty,
                        )
                    )
                    return score, TemporalStatus.PENDING_ENACTMENT, violations, supporting_signals, rejected_signals

            supporting_signals.append(f"Statute {statute_key} valid for pre-2024 timeline")
            return 1.0, TemporalStatus.APPLICABLE, violations, supporting_signals, rejected_signals
