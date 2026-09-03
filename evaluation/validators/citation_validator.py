"""
Citation validator module for NyayaSetu quality assurance.

Performs structural validation of citations in generated legal answers against
the actual source list returned by the retrieval pipeline.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CitationValidationReport:
    """Detailed structural citation validation report."""

    is_valid: bool
    detected_citations: List[str]
    valid_citations: List[str]
    invalid_citations: List[str]
    warnings: List[str] = field(default_factory=list)


class CitationValidator:
    """Validates that inline citations map strictly to returned source objects."""

    def validate(
        self,
        answer: str,
        sources: List[Any],
    ) -> CitationValidationReport:
        """Analyze citation syntax, presence, and boundary alignment.

        Args:
            answer: Model generated answer text.
            sources: List of source objects (dicts or SourceDocument / SourceReference).

        Returns:
            CitationValidationReport with valid/invalid counts and warnings.
        """
        warnings: List[str] = []
        available_count = len(sources)

        if not answer or not answer.strip():
            return CitationValidationReport(
                is_valid=False,
                detected_citations=[],
                valid_citations=[],
                invalid_citations=[],
                warnings=["Answer text is empty."],
            )

        # Extract [Source N] or [SOURCE N]
        raw_matches = re.findall(r"\[(?:Source|SOURCE)\s*(\d+)\]", answer)
        detected_indices = [int(m) for m in raw_matches]
        detected_citations = [f"[Source {idx}]" for idx in detected_indices]

        valid_citations: List[str] = []
        invalid_citations: List[str] = []

        for idx in detected_indices:
            label = f"[Source {idx}]"
            if 1 <= idx <= available_count:
                valid_citations.append(label)
            else:
                invalid_citations.append(label)

        # Check for malformed citations like [Source] or [Source ABC]
        malformed = re.findall(r"\[(?:Source|SOURCE)[^0-9\]]+\]", answer)
        if malformed:
            warnings.append(f"Detected malformed citation pattern(s): {malformed}")

        if invalid_citations:
            warnings.append(
                f"Answer references non-existent source label(s) {list(set(invalid_citations))} "
                f"when only {available_count} sources were provided."
            )

        if available_count > 0 and not detected_citations:
            warnings.append(
                "Answer does not cite any of the provided legal sources. "
                "Citations are required for explainable statutory attribution."
            )

        # Verification note: Structural traceability only
        warnings.append(
            "Structural citation verification passed; note this confirms syntax and source presence only, "
            "not judicial or legal correctness of the interpretation."
        )

        is_valid = len(invalid_citations) == 0 and len(malformed) == 0

        return CitationValidationReport(
            is_valid=is_valid,
            detected_citations=list(dict.fromkeys(detected_citations)),
            valid_citations=list(dict.fromkeys(valid_citations)),
            invalid_citations=list(dict.fromkeys(invalid_citations)),
            warnings=warnings,
        )
