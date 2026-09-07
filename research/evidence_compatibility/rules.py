"""Declarative Rules, Taxonomy, and Statute Metadata for Evidence Compatibility.

Models Indian statutory metadata:
- Canonical enactment names and aliases
- Effective dates, repeal dates, and supersession links (e.g., IPC -> BNS, CrPC -> BNSS, IEA -> BSA)
- Primary legal roles (Substantive, Procedural, Evidentiary, Constitutional, Special Law)
- Section-level role overrides
- Special law vs General law hierarchy
- Multi-statute compatibility bridges
"""

from typing import Any, Dict, List, Optional, Set
from research.evidence_compatibility.models import LegalRole, TemporalStatus

# Statute Registry & Temporal Grounding
STATUTE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "BNS": {
        "canonical_name": "Bharatiya Nyaya Sanhita, 2023",
        "act_code": "BNS",
        "aliases": ["bns", "bharatiya nyaya sanhita", "bns 2023", "bns_2023"],
        "effective_date": "2024-07-01",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": "IPC",
        "primary_role": LegalRole.SUBSTANTIVE,
        "regime_id": "BNS_SUBSTANTIVE",
        "law_category": "GENERAL_PENAL",
    },
    "BNSS": {
        "canonical_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "act_code": "BNSS",
        "aliases": ["bnss", "bharatiya nagarik suraksha sanhita", "bnss 2023", "bnss_2023"],
        "effective_date": "2024-07-01",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": "CRPC",
        "primary_role": LegalRole.PROCEDURAL,
        "regime_id": "BNSS_PROCEDURAL",
        "law_category": "PROCEDURAL",
    },
    "BSA": {
        "canonical_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "act_code": "BSA",
        "aliases": ["bsa", "bharatiya sakshya adhiniyam", "bsa 2023", "bsa_2023"],
        "effective_date": "2024-07-01",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": "IEA",
        "primary_role": LegalRole.EVIDENTIARY,
        "regime_id": "BSA_EVIDENCE",
        "law_category": "EVIDENTIARY",
    },
    "IPC": {
        "canonical_name": "Indian Penal Code, 1860",
        "act_code": "IPC",
        "aliases": ["ipc", "indian penal code", "ipc 1860"],
        "effective_date": "1862-01-01",
        "repeal_date": "2024-06-30",
        "is_repealed": True,
        "superseded_by": "BNS",
        "primary_role": LegalRole.SUBSTANTIVE,
        "regime_id": "BNS_SUBSTANTIVE",
        "law_category": "LEGACY_PENAL",
    },
    "CRPC": {
        "canonical_name": "Code of Criminal Procedure, 1973",
        "act_code": "CRPC",
        "aliases": ["crpc", "code of criminal procedure", "crpc 1973"],
        "effective_date": "1974-04-01",
        "repeal_date": "2024-06-30",
        "is_repealed": True,
        "superseded_by": "BNSS",
        "primary_role": LegalRole.PROCEDURAL,
        "regime_id": "BNSS_PROCEDURAL",
        "law_category": "LEGACY_PROCEDURAL",
    },
    "IEA": {
        "canonical_name": "Indian Evidence Act, 1872",
        "act_code": "IEA",
        "aliases": ["iea", "indian evidence act", "evidence act", "iea 1872"],
        "effective_date": "1872-09-01",
        "repeal_date": "2024-06-30",
        "is_repealed": True,
        "superseded_by": "BSA",
        "primary_role": LegalRole.EVIDENTIARY,
        "regime_id": "BSA_EVIDENCE",
        "law_category": "LEGACY_EVIDENTIARY",
    },
    "IT_ACT": {
        "canonical_name": "Information Technology Act, 2000",
        "act_code": "IT_ACT",
        "aliases": ["it act", "information technology act", "it act 2000", "ita 2000"],
        "effective_date": "2000-10-17",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": None,
        "primary_role": LegalRole.SPECIAL_LAW,
        "regime_id": "IT_ACT",
        "law_category": "SPECIAL_CYBER",
    },
    "CONSTITUTION": {
        "canonical_name": "Constitution of India",
        "act_code": "CONSTITUTION",
        "aliases": ["constitution of india", "constitution", "coi"],
        "effective_date": "1950-01-26",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": None,
        "primary_role": LegalRole.CONSTITUTIONAL,
        "regime_id": "CONSTITUTION",
        "law_category": "CONSTITUTIONAL_SUPREME",
    },
    "POSH": {
        "canonical_name": "Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "act_code": "POSH",
        "aliases": ["posh", "posh act", "sexual harassment of women at workplace act", "posh_2013"],
        "effective_date": "2013-12-09",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": None,
        "primary_role": LegalRole.SPECIAL_LAW,
        "regime_id": "POSH_LABOUR",
        "law_category": "SPECIAL_PROTECTION",
    },
    "POCSO": {
        "canonical_name": "Protection of Children from Sexual Offences Act, 2012",
        "act_code": "POCSO",
        "aliases": ["pocso", "pocso act", "protection of children from sexual offences"],
        "effective_date": "2012-11-14",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": None,
        "primary_role": LegalRole.SPECIAL_LAW,
        "regime_id": "POCSO_CHILD",
        "law_category": "SPECIAL_CHILD_PROTECTION",
    },
    "CPA": {
        "canonical_name": "Consumer Protection Act, 2019",
        "act_code": "CPA",
        "aliases": ["consumer protection act", "cpa", "cpa 2019"],
        "effective_date": "2020-07-20",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": "CPA_1986",
        "primary_role": LegalRole.SPECIAL_LAW,
        "regime_id": "CONSUMER_PROTECTION",
        "law_category": "SPECIAL_CONSUMER",
    },
    "MVA": {
        "canonical_name": "Motor Vehicles Act, 1988",
        "act_code": "MVA",
        "aliases": ["motor vehicles act", "mva", "motor vehicle act"],
        "effective_date": "1989-07-01",
        "repeal_date": None,
        "is_repealed": False,
        "supersedes": None,
        "primary_role": LegalRole.SPECIAL_LAW,
        "regime_id": "MOTOR_VEHICLES",
        "law_category": "SPECIAL_TRANSPORT",
    },
}

# Regime Cross-Statute Coherence Sets
# Defines groups of statutes that naturally complement one another for multi-statute queries
COHERENT_REGIME_BRIDGES: Dict[str, Set[str]] = {
    "BNS_SUBSTANTIVE": {"BNSS_PROCEDURAL", "BSA_EVIDENCE", "CONSTITUTION"},
    "BNSS_PROCEDURAL": {"BNS_SUBSTANTIVE", "BSA_EVIDENCE", "CONSTITUTION"},
    "BSA_EVIDENCE": {"BNS_SUBSTANTIVE", "BNSS_PROCEDURAL", "IT_ACT"},
    "IT_ACT": {"BNS_SUBSTANTIVE", "BSA_EVIDENCE"},
    "POSH_LABOUR": {"BNS_SUBSTANTIVE", "CONSTITUTION"},
    "POCSO_CHILD": {"BNS_SUBSTANTIVE", "BNSS_PROCEDURAL", "BSA_EVIDENCE"},
    "CONSTITUTION": {"BNS_SUBSTANTIVE", "BNSS_PROCEDURAL"},
}

# Special Law Precedence and Preference Pairs (Lex Specialis)
# Format: special_regime -> {competing_general_regime: reason}
SPECIAL_LAW_PREFERENCES: Dict[str, Dict[str, str]] = {
    "IT_ACT": {
        "BNS_SUBSTANTIVE": "IT Act constitutes specialized statutory enactment for computer and cyber identity offenses over generic criminal law",
        "IPC": "IT Act overrides generic legacy penal provisions for digital offenses",
    },
    "POSH_LABOUR": {
        "BNS_SUBSTANTIVE": "POSH Act provides specialized statutory inquiry and internal redressal mechanism for workplace sexual harassment over general penal provisions",
        "IPC": "POSH Act provides specialized civil and workplace redressal over generic penal code",
    },
    "POCSO_CHILD": {
        "BNS_SUBSTANTIVE": "POCSO Act is a specialized child protection enactment containing statutory presumptions and enhanced procedures over general penal law",
        "IPC": "POCSO Act prevails over generic penal code for offenses against minors",
    },
    "CONSUMER_PROTECTION": {
        "BNS_SUBSTANTIVE": "Consumer Protection Act governs consumer defect and service deficiency claims over generic criminal cheating",
    },
    "MOTOR_VEHICLES": {
        "BNS_SUBSTANTIVE": "Motor Vehicles Act governs vehicular regulatory and licensing offenses over generic penal statutes",
    },
}

# Query Intent to Required/Compatible Legal Roles
INTENT_ROLE_MAP: Dict[str, List[LegalRole]] = {
    "punishment_or_offense": [LegalRole.SUBSTANTIVE, LegalRole.SPECIAL_LAW],
    "definition_of_crime": [LegalRole.SUBSTANTIVE, LegalRole.SPECIAL_LAW],
    "arrest_or_police_power": [LegalRole.PROCEDURAL],
    "bail_or_remand": [LegalRole.PROCEDURAL],
    "investigation_procedure": [LegalRole.PROCEDURAL],
    "fir_registration": [LegalRole.PROCEDURAL],
    "trial_procedure": [LegalRole.PROCEDURAL],
    "admissibility_of_evidence": [LegalRole.EVIDENTIARY],
    "electronic_records": [LegalRole.EVIDENTIARY, LegalRole.SPECIAL_LAW],
    "dying_declaration": [LegalRole.EVIDENTIARY],
    "burden_of_proof": [LegalRole.EVIDENTIARY],
    "fundamental_rights": [LegalRole.CONSTITUTIONAL],
    "writ_remedy": [LegalRole.CONSTITUTIONAL],
    "cyber_crime": [LegalRole.SPECIAL_LAW, LegalRole.SUBSTANTIVE],
    "workplace_harassment": [LegalRole.SPECIAL_LAW, LegalRole.SUBSTANTIVE],
}


import re


def resolve_statute_key(document_name: str, filename: str = "") -> Optional[str]:
    """Resolve a document name or filename to a canonical statute key in STATUTE_REGISTRY."""
    if not document_name and not filename:
        return None

    target = f"{document_name} {filename}".lower()

    # Collect all (pattern, key, is_code) pairs and sort by pattern length descending
    # This guarantees longer specific patterns (e.g. 'bnss', 'bharatiya nagarik suraksha sanhita')
    # match before shorter prefixes (e.g. 'bns')
    candidates = []
    for key, data in STATUTE_REGISTRY.items():
        candidates.append((key.lower(), key, True))
        for alias in data.get("aliases", []):
            candidates.append((alias.lower(), key, False))

    candidates.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern, key, is_code in candidates:
        if is_code or len(pattern) <= 4:
            # Word boundary check prevents 'bns' matching 'bnss'
            if re.search(r"(?<![a-z0-9])" + re.escape(pattern) + r"(?![a-z0-9])", target):
                return key
        else:
            if pattern in target:
                return key

    return None


def validate_configuration(config: Dict[str, Any]) -> bool:
    """Validate weights, thresholds, and operational constraints of compatibility config."""
    if not isinstance(config, dict):
        return False

    scoring = config.get("scoring", {})
    weights = scoring.get("weights", {})
    if weights:
        total_w = sum(weights.values())
        if abs(total_w - 1.0) > 0.01:
            raise ValueError(f"Compatibility scoring weights must sum to 1.0, got {total_w}")
        for k, v in weights.items():
            if v < 0:
                raise ValueError(f"Weight for {k} must be non-negative, got {v}")

    thresholds = scoring.get("thresholds", {})
    if thresholds:
        comp = thresholds.get("compatible", 0.80)
        part = thresholds.get("partially_compatible", 0.55)
        if comp <= part:
            raise ValueError(f"Compatible threshold ({comp}) must exceed partially compatible ({part})")

    return True

