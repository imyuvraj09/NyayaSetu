"""Claim classification and risk weighting module for legal claim grounding.

Classifies atomic claims according to their legal function (punishment,
statutory rule, procedural requirement, etc.) and assigns risk levels
and importance weights.
"""

import re
from typing import Dict, List, Optional, Tuple

from research.claim_grounding.models import AtomicClaim, ClaimType, RiskLevel

DEFAULT_IMPORTANCE_WEIGHTS: Dict[ClaimType, float] = {
    ClaimType.PUNISHMENT: 1.00,
    ClaimType.STATUTORY_PROVISION: 1.00,
    ClaimType.LEGAL_CONSEQUENCE: 0.95,
    ClaimType.PROCEDURAL_REQUIREMENT: 0.90,
    ClaimType.EVIDENTIARY_REQUIREMENT: 0.90,
    ClaimType.TEMPORAL_CLAIM: 0.90,
    ClaimType.LEGAL_INTERPRETATION: 0.80,
    ClaimType.FACTUAL_APPLICATION: 0.75,
    ClaimType.LEGAL_RULE: 0.70,
    ClaimType.GENERAL_INFORMATION: 0.50,
}

RISK_MAPPING: Dict[ClaimType, RiskLevel] = {
    ClaimType.PUNISHMENT: RiskLevel.HIGH,
    ClaimType.STATUTORY_PROVISION: RiskLevel.HIGH,
    ClaimType.LEGAL_CONSEQUENCE: RiskLevel.HIGH,
    ClaimType.PROCEDURAL_REQUIREMENT: RiskLevel.HIGH,
    ClaimType.TEMPORAL_CLAIM: RiskLevel.HIGH,
    ClaimType.EVIDENTIARY_REQUIREMENT: RiskLevel.MEDIUM,
    ClaimType.LEGAL_INTERPRETATION: RiskLevel.MEDIUM,
    ClaimType.FACTUAL_APPLICATION: RiskLevel.MEDIUM,
    ClaimType.LEGAL_RULE: RiskLevel.MEDIUM,
    ClaimType.GENERAL_INFORMATION: RiskLevel.LOW,
}


class ClaimClassifier:
    """Classifies atomic claims into structured legal roles and assigns risk weights."""

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = dict(DEFAULT_IMPORTANCE_WEIGHTS)
        if custom_weights:
            for k, v in custom_weights.items():
                try:
                    ct = ClaimType(k) if isinstance(k, str) else k
                    self.weights[ct] = float(v)
                except (ValueError, KeyError):
                    pass

    def classify_claim(self, claim: AtomicClaim) -> AtomicClaim:
        """Classify a single claim, updating claim_type, importance_weight, and risk_level."""
        text = claim.claim_text.lower()

        c_type = self._determine_claim_type(text, claim)
        claim.claim_type = c_type
        claim.importance_weight = self.weights.get(c_type, 0.70)
        claim.risk_level = RISK_MAPPING.get(c_type, RiskLevel.MEDIUM)

        return claim

    def classify_claims(self, claims: List[AtomicClaim]) -> List[AtomicClaim]:
        """Classify a batch of atomic claims."""
        return [self.classify_claim(c) for c in claims]

    def _determine_claim_type(self, text: str, claim: AtomicClaim) -> ClaimType:
        """Heuristic rule-based legal classifier."""
        # 1. Punishment
        punishment_patterns = [
            r"\bpunish(?:ed|able)?\b",
            r"\bimprisonment\b",
            r"\bfine\s+(?:up\s+to|of|not\s+exceeding)?\s*(?:rs|rupees|lakh)?\b",
            r"\blife\s+imprisonment\b",
            r"\bdeath\s+penalty\b",
            r"\bdeath\s+sentence\b",
            r"\bhanging\b",
            r"\bcapital\s+punishment\b",
            r"\brigorous\s+imprisonment\b",
            r"\bsimple\s+imprisonment\b",
            r"\byears?\s+(?:in\s+prison|imprisonment)\b",
            r"\bpenal(?:ty|ties)?\b",
        ]
        if any(re.search(pat, text) for pat in punishment_patterns):
            return ClaimType.PUNISHMENT

        # 2. Temporal claim
        temporal_patterns = [
            r"\bprior\s+to\s+(?:1st\s+)?july\s+2024\b",
            r"\bafter\s+(?:1st\s+)?july\s+2024\b",
            r"\bpre-2024\b",
            r"\bpost-2024\b",
            r"\b(?:came\s+into\s+effect|came\s+into\s+force|in\s+force)\b",
            r"\b(?:1st\s+)?july\s+2024\b",
            r"\brepeal(?:ed|s)?\b",
            r"\bsupersed(?:ed|es)?\b",
            r"\bcommence(?:d|ment)?\s+date\b",
            r"\bprospectively\b",
            r"\bretrospectively\b",
            r"\bex\s+post\s+facto\b",
        ]
        if any(re.search(pat, text) for pat in temporal_patterns):
            return ClaimType.TEMPORAL_CLAIM

        # 3. Procedural requirement
        procedural_patterns = [
            r"\barrest\s+(?:without\s+a?\s*warrant|with\s+a?\s*warrant)\b",
            r"\bbail\b",
            r"\banticipatory\s+bail\b",
            r"\bcognizable\b",
            r"\bnon-cognizable\b",
            r"\bbailable\b",
            r"\bnon-bailable\b",
            r"\bfir\b",
            r"\bfirst\s+information\s+report\b",
            r"\bmagistrate\b",
            r"\binvestigat(?:ion|ing|or)\b",
            r"\bsummons?\b",
            r"\bwarrant\b",
            r"\bcharge\s*sheet\b",
            r"\bremand\b",
            r"\bpolice\s+custody\b",
        ]
        if any(re.search(pat, text) for pat in procedural_patterns):
            return ClaimType.PROCEDURAL_REQUIREMENT

        # 4. Evidentiary requirement
        evidentiary_patterns = [
            r"\belectronic\s+(?:record|evidence|certificate)\b",
            r"\badmissib(?:le|ility)\b",
            r"\bsection\s+65b\b",
            r"\bsection\s+63\b",
            r"\bburden\s+of\s+proof\b",
            r"\bpresumption\b",
            r"\bprimary\s+evidence\b",
            r"\bsecondary\s+evidence\b",
            r"\bcertificate\s+under\b",
            r"\bhash\s+value\b",
            r"\bchain\s+of\s+custody\b",
        ]
        if any(re.search(pat, text) for pat in evidentiary_patterns):
            return ClaimType.EVIDENTIARY_REQUIREMENT

        # 5. Statutory provision declaration
        if claim.attached_citations or re.search(r"\bsection\s+\d+[a-z]?\b", text):
            if re.search(r"\b(?:provides|defines|states|deals\s+with|prescribes|governs)\b", text):
                return ClaimType.STATUTORY_PROVISION

        # 6. Legal consequence
        consequence_patterns = [
            r"\bvoid\s+ab\s+initio\b",
            r"\bliab(?:le|ility)\b",
            r"\bdisqualif(?:ied|ication)\b",
            r"\bforfeit(?:ed|ure)\b",
            r"\bnull\s+and\s+void\b",
            r"\bactionable\s+per\s+se\b",
            r"\bcompensat(?:ion|ory)\b",
            r"\bdamages\b",
            r"\binjunction\b",
        ]
        if any(re.search(pat, text) for pat in consequence_patterns):
            return ClaimType.LEGAL_CONSEQUENCE

        # 7. Legal rule
        rule_patterns = [
            r"\boffence\s+(?:is|consists\s+of|means)\b",
            r"\belements\s+of\b",
            r"\bmens\s+rea\b",
            r"\bactus\s+reus\b",
            r"\bwhoever\b",
            r"\bprohibited\s+by\s+law\b",
            r"\bunlawful\b",
        ]
        if any(re.search(pat, text) for pat in rule_patterns):
            return ClaimType.LEGAL_RULE

        # 8. Factual application / interpretation
        if re.search(r"\b(?:in\s+the\s+instant\s+case|based\s+on\s+these\s+facts|the\s+accused|the\s+complainant|here)\b", text):
            return ClaimType.FACTUAL_APPLICATION

        if re.search(r"\b(?:interpreted|held\s+that|construed|meaning\s+of)\b", text):
            return ClaimType.LEGAL_INTERPRETATION

        return ClaimType.GENERAL_INFORMATION
