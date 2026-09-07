"""Indian Court Hierarchy and Bench Rules for Judicial Precedent Reasoning.

Encodes:
1. Constitutional hierarchy:
   - Supreme Court of India (Apex Court, Article 141 binding authority)
   - High Courts (State-level constitutional courts, binding within territorial jurisdiction, persuasive across states)
   - Specialized Appellate Tribunals (NCLAT, ITAT, NGT, TDSAT, etc.)
   - District & Subordinate Courts
2. Bench strength precedence:
   - Constitution Bench (5+ judges) > Full/Larger Bench (3 judges) > Division Bench (2 judges) > Single Judge (1 judge)
3. Coordinate bench doctrine:
   - A bench of coordinate strength cannot overrule another bench of equal strength; must refer to larger bench.
"""

import re
from typing import Dict, List, Optional, Tuple

from research.precedent_reasoning.models import (
    AuthorityStatus,
    BenchStrength,
    CourtLevel,
)

# Canonical High Court names and territorial jurisdictions
HIGH_COURT_TERRITORIES: Dict[str, List[str]] = {
    "delhi": ["delhi", "nct of delhi"],
    "bombay": ["maharashtra", "goa", "daman and diu", "dadra and nagar haveli"],
    "allahabad": ["uttar pradesh", "up"],
    "madras": ["tamil nadu", "puducherry"],
    "calcutta": ["west bengal", "andaman and nicobar islands"],
    "karnataka": ["karnataka"],
    "kerala": ["kerala", "lakshadweep"],
    "gujarat": ["gujarat"],
    "punjab and haryana": ["punjab", "haryana", "chandigarh"],
    "madhya pradesh": ["madhya pradesh", "mp"],
    "patna": ["bihar"],
    "rajasthan": ["rajasthan"],
    "orissa": ["odisha", "orissa"],
    "gauhati": ["assam", "nagaland", "mizoram", "arunachal pradesh"],
    "telangana": ["telangana"],
    "andhra pradesh": ["andhra pradesh"],
    "himachal pradesh": ["himachal pradesh"],
    "jammu and kashmir": ["jammu and kashmir", "ladakh"],
    "jharkhand": ["jharkhand"],
    "chhattisgarh": ["chhattisgarh"],
    "uttarakhand": ["uttarakhand"],
}

# Known Central / State Tribunals
TRIBUNAL_IDENTIFIERS: List[str] = [
    "nclat", "nclt", "itat", "ngt", "tdsat", "aptel", "cat", "drata", "drt", "cegato", "cestat"
]


class CourtHierarchyEngine:
    """Deterministic analyzer of Indian judicial hierarchy and court levels."""

    @staticmethod
    def classify_court_level(court_name: Optional[str]) -> CourtLevel:
        """Deterministically determine the court level from official court name."""
        if not court_name or not court_name.strip():
            return CourtLevel.UNKNOWN

        c_lower = court_name.lower().strip()

        # 1. Supreme Court
        if any(term in c_lower for term in ["supreme court", "apex court", "sc of india", "hon'ble sc"]):
            return CourtLevel.SUPREME_COURT

        # 2. High Court
        if "high court" in c_lower or c_lower.startswith("hc ") or " hc" in c_lower:
            return CourtLevel.HIGH_COURT

        # 3. Tribunal
        if any(term in c_lower for term in TRIBUNAL_IDENTIFIERS) or "tribunal" in c_lower or "appellate tribunal" in c_lower:
            return CourtLevel.TRIBUNAL

        # 4. District & Sessions Court
        if any(term in c_lower for term in ["district court", "sessions court", "magistrate", "sub-court"]):
            return CourtLevel.DISTRICT_COURT

        return CourtLevel.OTHER

    @staticmethod
    def determine_bench_strength(bench_members: Optional[List[str]]) -> BenchStrength:
        """Classify bench strength from list of judges."""
        if not bench_members or not isinstance(bench_members, list):
            return BenchStrength.UNKNOWN

        valid_count = len([m for m in bench_members if m and m.strip()])
        if valid_count >= 5:
            return BenchStrength.CONSTITUTION_BENCH
        if valid_count == 3 or valid_count == 4:
            return BenchStrength.LARGER_BENCH
        if valid_count == 2:
            return BenchStrength.DIVISION_BENCH
        if valid_count == 1:
            return BenchStrength.SINGLE_JUDGE

        return BenchStrength.UNKNOWN

    @classmethod
    def compute_bench_weight(cls, bench_input: any) -> float:
        """Compute bench authority weight multiplier from judge count, bench list, or BenchStrength enum."""
        if isinstance(bench_input, BenchStrength):
            return cls.get_bench_multiplier(bench_input)
        if isinstance(bench_input, list):
            return cls.get_bench_multiplier(cls.determine_bench_strength(bench_input))
        if isinstance(bench_input, (int, float)):
            cnt = int(bench_input)
        elif isinstance(bench_input, str):
            try:
                cnt = int(bench_input.strip())
            except ValueError:
                cnt = 1
        else:
            return 1.0

        if cnt >= 5:
            return cls.get_bench_multiplier(BenchStrength.CONSTITUTION_BENCH)
        elif cnt >= 3:
            return cls.get_bench_multiplier(BenchStrength.LARGER_BENCH)
        elif cnt == 2:
            return cls.get_bench_multiplier(BenchStrength.DIVISION_BENCH)
        else:
            return cls.get_bench_multiplier(BenchStrength.SINGLE_JUDGE)

    @staticmethod
    def get_bench_multiplier(bench_strength: BenchStrength) -> float:
        """Return relative authority weight based on bench composition."""
        weights = {
            BenchStrength.CONSTITUTION_BENCH: 1.25,
            BenchStrength.LARGER_BENCH: 1.15,
            BenchStrength.DIVISION_BENCH: 1.05,
            BenchStrength.SINGLE_JUDGE: 1.0,
            BenchStrength.UNKNOWN: 1.0,
        }
        return weights.get(bench_strength, 1.0)

    @staticmethod
    def compare_hierarchy(court_a: CourtLevel, court_b: CourtLevel) -> int:
        """Compare hierarchy level: +1 if A higher than B, -1 if B higher than A, 0 if equal/incomparable."""
        rank = {
            CourtLevel.SUPREME_COURT: 4,
            CourtLevel.HIGH_COURT: 3,
            CourtLevel.TRIBUNAL: 2,
            CourtLevel.DISTRICT_COURT: 1,
            CourtLevel.OTHER: 0,
            CourtLevel.UNKNOWN: 0,
        }
        r_a = rank.get(court_a, 0)
        r_b = rank.get(court_b, 0)
        if r_a > r_b:
            return 1
        if r_a < r_b:
            return -1
        return 0

    @staticmethod
    def identify_high_court_state(court_name: str) -> Optional[str]:
        """Identify which state/territory a High Court represents."""
        c_lower = court_name.lower()
        for hc_name in HIGH_COURT_TERRITORIES:
            if hc_name in c_lower:
                return hc_name
        return None
