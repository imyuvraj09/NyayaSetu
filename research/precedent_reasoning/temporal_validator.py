"""Conservative Temporal Validator for Judicial Precedents.

Core Principles:
1. Precedents remain authoritative despite age unless explicit subsequent overruling
   or legislative nullification is proven by corpus evidence.
2. Only mark:
   - OVERRULED: when explicit evidence/metadata confirms reversal by superior court/larger bench.
   - POTENTIALLY_SUPERSEDED: when statutory enactment explicitly changes operative provisions.
   - APPLICABLE: default status for unreversed authorities.
   - UNKNOWN: when status cannot be confirmed.
"""

from typing import Optional, Tuple

from research.precedent_reasoning.models import (
    JudicialPrecedent,
    PrecedentTemporalStatus,
)


class PrecedentTemporalValidator:
    """Conservative temporal status validator for case-law authorities."""

    @classmethod
    def validate_temporal_status(
        cls,
        precedent: JudicialPrecedent,
        incident_year: Optional[int] = None,
    ) -> Tuple[PrecedentTemporalStatus, float, str]:
        """Validate temporal status and return (status, score_multiplier, reasoning).

        Args:
            precedent: Judicial precedent candidate.
            incident_year: Optional year of the incident under legal evaluation.

        Returns:
            Tuple of (PrecedentTemporalStatus, score_multiplier, explanation).
        """
        meta = precedent.metadata

        # 1. Check for explicit overruling in metadata
        if meta.overruled_by:
            return (
                PrecedentTemporalStatus.OVERRULED,
                0.30,  # Severe penalty, but not catastrophic elimination for historical context
                f"Precedent '{precedent.case_name}' was EXPLICITLY OVERRULED by '{meta.overruled_by}'. No longer good law."
            )

        # 2. Check for explicit partial overruling
        if meta.overruled_in_part_by:
            return (
                PrecedentTemporalStatus.POTENTIALLY_SUPERSEDED,
                0.75,
                f"Precedent '{precedent.case_name}' was partially modified or doubted by '{meta.overruled_in_part_by}'."
            )

        # 3. Check decision date format
        date_str = precedent.judgment_date
        year = None
        if date_str and date_str != "UNKNOWN" and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        # 4. Old precedent doctrine: Age does NOT equal invalidity
        if year is not None:
            # Check if landmark authority
            if year < 1990:
                reasoning = (
                    f"Precedent '{precedent.case_name}' ({year}) is an established landmark authority. "
                    "In Indian jurisprudence, age does not impair binding force absent explicit overruling."
                )
            else:
                reasoning = f"Precedent '{precedent.case_name}' ({date_str}) is currently valid and unreversed law."
            return (PrecedentTemporalStatus.APPLICABLE, 1.0, reasoning)

        return (
            PrecedentTemporalStatus.UNKNOWN,
            0.95,
            f"Judgment date for '{precedent.case_name}' is unspecified; status evaluated as UNKNOWN."
        )
