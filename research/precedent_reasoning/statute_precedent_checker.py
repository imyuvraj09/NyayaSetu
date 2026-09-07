"""Statute-Precedent Compatibility Checker.

Evaluates whether a judicial precedent is compatible with the query's target statutory provisions:
1. Direct Statutory Concordance:
   - Precedent directly interprets the target statute and section (e.g. Section 63 BNS / Section 375 IPC).
2. Transitional Statutory Equivalence:
   - Recognizes that IPC interpretations apply to corresponding BNS provisions (e.g. IPC 375 <-> BNS 63; IPC 420 <-> BNS 318).
3. Cross-Domain Incompatibility Penalty:
   - A precedent discussing a superficially similar topic under an unrelated commercial statute
     (e.g., consumer protection or contract law) when a criminal penal offense is sought
     receives an explainable soft compatibility penalty [0.70 to 0.85].
4. Soft Adjustment:
   - Preserves candidate in the pool; never catastrophically deletes useful context.
"""

from typing import Dict, List, Optional, Set, Tuple

from research.precedent_reasoning.models import JudicialPrecedent

# Known statutory cross-regime bridges (IPC <-> BNS, CrPC <-> BNSS, IEA <-> BSA)
TRANSITIONAL_SECTION_BRIDGES: Dict[str, List[str]] = {
    "375": ["63", "64", "69"],  # Rape / Consent in IPC <-> BNS
    "63": ["375", "90"],        # BNS Rape / Consent <-> IPC
    "90": ["27", "63"],         # Consent under misconception IPC <-> BNS
    "27": ["90"],               # BNS consent under fear/misconception
    "300": ["100", "101"],      # Murder IPC <-> BNS
    "302": ["103"],             # Murder punishment IPC <-> BNS
    "100": ["299", "300"],      # BNS culpable homicide / murder
    "103": ["302"],             # BNS murder punishment
    "420": ["318"],             # Cheating IPC <-> BNS
    "318": ["420", "415"],      # Cheating BNS <-> IPC
    "406": ["316"],             # Criminal breach of trust IPC <-> BNS
    "316": ["406", "405"],      # CBT BNS <-> IPC
    "65b": ["63"],              # Electronic records admissibility IEA <-> BSA
    "63_bsa": ["65b"],          # BSA electronic evidence
    "438": ["482", "484"],      # Anticipatory bail CrPC <-> BNSS
}


class StatutePrecedentChecker:
    """Computes explainable statute-precedent compatibility scores."""

    @classmethod
    def evaluate_compatibility(
        cls,
        precedent: JudicialPrecedent,
        target_statutes: Optional[List[str]] = None,
        target_sections: Optional[List[str]] = None,
        routed_regime: Optional[str] = None,
    ) -> Tuple[float, str]:
        """Compute compatibility multiplier [0.70 to 1.15] and explanation.

        Args:
            precedent: The judicial precedent candidate.
            target_statutes: List of statutes sought by query.
            target_sections: List of section numbers sought by query.
            routed_regime: Legal regime identified by Phase 3 router.

        Returns:
            Tuple of (multiplier, reasoning).
        """
        prec_secs = [str(s).strip().lower().lstrip("0") for s in precedent.sections_referred]
        prec_statutes = [str(st).strip().lower() for st in precedent.statutes_referred]

        # 1. Exact section concordance
        if target_sections:
            clean_targets = [str(s).strip().lower().lstrip("0") for s in target_sections]
            direct_matches = set(clean_targets) & set(prec_secs)
            if direct_matches:
                return (
                    1.15,
                    f"Direct statutory concordance: precedent explicitly interprets target section(s) {list(direct_matches)}."
                )

            # Check transitional bridge concordance (e.g. IPC 375 <-> BNS 63)
            bridged_matches = set()
            for t_sec in clean_targets:
                equivs = TRANSITIONAL_SECTION_BRIDGES.get(t_sec, [])
                for eq in equivs:
                    if eq in prec_secs:
                        bridged_matches.add(f"{t_sec} <-> {eq}")

            if bridged_matches:
                return (
                    1.10,
                    f"Transitional statutory concordance: precedent interprets corresponding provision(s) {list(bridged_matches)}."
                )

        # 2. General statute match without specific section match
        if target_statutes:
            statute_match = False
            for ts in target_statutes:
                ts_lower = ts.lower()
                if any(ts_lower in ps or ps in ts_lower for ps in prec_statutes):
                    statute_match = True
                    break

            if statute_match:
                return (
                    1.02,
                    f"Statutory alignment: precedent interprets target enactment ({target_statutes})."
                )

        # 3. Mismatch penalty if precedent clearly interprets an unrelated specialized regime
        if routed_regime and routed_regime in ("CRIMINAL_SUBSTANTIVE", "CRIMINAL_PROCEDURAL"):
            # If precedent is strictly civil / arbitration / consumer
            if any(term in prec_statutes for term in ["arbitration", "consumer protection", "negotiable instruments"]):
                return (
                    0.75,
                    f"Cross-domain mismatch: criminal query routed, but precedent interprets commercial/civil statute ({prec_statutes})."
                )

        # Default neutral compatibility
        return (
            1.0,
            "General compatibility: precedent provides legal principles on related factual topics."
        )
