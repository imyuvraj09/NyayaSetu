"""Conservative factual structure extractor for legal inquiries.

Follows the primary research constraint: ZERO HALLUCINATION.
Identifies only explicitly stated or lexically grounded actors, actions, objects,
events, temporal context, and statutory citations without inferring unsupported facts.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from research.schemas import ExtractedFacts

# Explicit Actor Lexicon
ACTOR_PATTERNS: Dict[str, List[str]] = {
    "unknown_person": [r"\bsomeone\b", r"\bsomebody\b", r"\bunknown person\b", r"\ba person\b", r"\bstranger\b"],
    "police": [r"\bpolice\b", r"\bpolice officer\b", r"\bcop\b", r"\binvestigating officer\b", r"\bio\b"],
    "employer": [r"\bemployer\b", r"\bboss\b", r"\bcompany management\b"],
    "employee": [r"\bworker\b", r"\bemployee\b", r"\bstaff\b", r"\blabourer\b", r"\blaborer\b"],
    "accused": [r"\baccused\b", r"\bsuspect\b", r"\bculprit\b", r"\boffender\b"],
    "victim": [r"\bvictim\b", r"\bcomplainant\b", r"\baggrieved person\b", r"\baggrieved woman\b"],
    "magistrate": [r"\bmagistrate\b", r"\bjudge\b", r"\bcourt\b", r"\btribunal\b"],
    "spouse": [r"\bhusband\b", r"\bwife\b", r"\bspouse\b"],
    "child": [r"\bchild\b", r"\bminor\b", r"\bkid\b", r"\bjuvenile\b"],
    "director": [r"\bdirector\b", r"\bboard of directors\b"],
    "consumer": [r"\bconsumer\b", r"\bbuyer\b", r"\bcustomer\b"],
    "driver": [r"\bdriver\b", r"\bmotorist\b"],
}

# Explicit Action Patterns
ACTION_PATTERNS: Dict[str, List[str]] = {
    "theft": [r"\bstole\b", r"\bstealing\b", r"\btheft\b", r"\btook away\b"],
    "murder": [r"\bmurder\b", r"\bkilled\b", r"\bkilling\b", r"\bhomicide\b"],
    "arrest": [r"\barrest\b", r"\barrested\b", r"\barresting\b", r"\btaken into custody\b"],
    "assault": [r"\bassault\b", r"\bassaulted\b", r"\battacked\b", r"\bhit\b", r"\bbeaten\b"],
    "cyber_access": [r"\bhacked\b", r"\bhacking\b", r"\bunauthorized access\b", r"\btampered\b"],
    "impersonation": [r"\bimpersonated\b", r"\bimpersonating\b", r"\bimpersonation\b", r"\bpretended to be\b"],
    "threat": [r"\bthreatened\b", r"\bthreatening\b", r"\bthreat\b", r"\bintimidated\b"],
    "sale": [r"\bsold\b", r"\bselling\b", r"\bsale\b"],
    "withholding": [r"\bwithheld\b", r"\bwithholding\b", r"\brefused to pay\b"],
    "cheating": [r"\bcheated\b", r"\bcheating\b", r"\bfraud\b", r"\bdefrauded\b"],
    "investigation": [r"\binvestigate\b", r"\binvestigated\b", r"\binvestigating\b", r"\binvestigation\b"],
    "filing": [r"\bfiled\b", r"\bfiling\b", r"\blodged\b", r"\blodging\b", r"\bregistered\b"],
    "bail": [r"\bbail\b", r"\banticipatory bail\b"],
    "sexual_harassment": [r"\bsexual harassment\b", r"\bharassed sexually\b", r"\bsexual abuse\b"],
}

# Explicit Object Patterns
OBJECT_PATTERNS: Dict[str, List[str]] = {
    "mobile_phone": [r"\bmobile phone\b", r"\bmobile\b", r"\bphone\b", r"\bsmartphone\b"],
    "computer_resource": [r"\bcomputer\b", r"\blaptop\b", r"\baccount\b", r"\bserver\b", r"\bcomputer resource\b", r"\bemail\b"],
    "property": [r"\bproperty\b", r"\bhouse\b", r"\bland\b", r"\bgoods\b"],
    "money_salary": [r"\bsalary\b", r"\bwages\b", r"\bmoney\b", r"\bcash\b", r"\bfunds\b"],
    "vehicle": [r"\bvehicle\b", r"\bcar\b", r"\bbike\b", r"\bmotorcycle\b", r"\btruck\b"],
    "legal_document": [r"\bfir\b", r"\bfirst information report\b", r"\bwarrant\b", r"\bsummons\b", r"\bcharge sheet\b", r"\bcheque\b"],
    "evidence_record": [r"\belectronic record\b", r"\belectronic evidence\b", r"\bdying declaration\b", r"\bconfession\b", r"\bcctv\b"],
}

# Explicit Statutory Citations
STATUTE_PATTERNS: Dict[str, List[str]] = {
    "BNS": [r"\bbns\b", r"\bbharatiya nyaya sanhita\b", r"\bipc\b", r"\bindian penal code\b"],
    "BNSS": [r"\bbnss\b", r"\bbharatiya nagarik suraksha sanhita\b", r"\bcrpc\b", r"\bcode of criminal procedure\b"],
    "BSA": [r"\bbsa\b", r"\bbharatiya sakshya adhiniyam\b", r"\bindian evidence act\b", r"\bevidence act\b"],
    "Constitution": [r"\bconstitution\b", r"\barticle \d+[a-z]?\b", r"\bconstitution of india\b"],
    "IT_Act": [r"\bit act\b", r"\binformation technology act\b"],
    "POCSO": [r"\bpocso\b", r"\bprotection of children from sexual offences\b"],
    "POSH": [r"\bposh\b", r"\bsexual harassment of women at workplace\b"],
    "Consumer_Protection": [r"\bconsumer protection\b", r"\bconsumer protection act\b", r"\bcpa\b"],
    "Motor_Vehicles": [r"\bmotor vehicles? act\b", r"\bmva\b"],
}


class ConservativeFactExtractor:
    """Extracts verifiable, explicit factual anchors from queries."""

    def __init__(self) -> None:
        pass

    def extract(self, query: str) -> ExtractedFacts:
        """Extract explicit factual components without fabricating unmentioned facts."""
        if not query or not query.strip():
            return ExtractedFacts()

        q_clean = re.sub(r"\s+", " ", query).strip()
        q_lower = q_clean.lower()

        extracted_actors: Set[str] = set()
        extracted_actions: Set[str] = set()
        extracted_objects: Set[str] = set()
        extracted_terms: Set[str] = set()
        extracted_statutes: Set[str] = set()
        extracted_relationships: Set[str] = set()

        # 1. Actors
        for canonical_actor, pats in ACTOR_PATTERNS.items():
            for p in pats:
                if re.search(p, q_lower):
                    extracted_actors.add(canonical_actor)
                    break

        # 2. Actions
        for canonical_action, pats in ACTION_PATTERNS.items():
            for p in pats:
                if re.search(p, q_lower):
                    extracted_actions.add(canonical_action)
                    break

        # 3. Objects
        for canonical_object, pats in OBJECT_PATTERNS.items():
            for p in pats:
                if re.search(p, q_lower):
                    extracted_objects.add(canonical_object)
                    break

        # 4. Statutory Citations & Sections
        for canon_stat, pats in STATUTE_PATTERNS.items():
            for p in pats:
                if re.search(p, q_lower):
                    extracted_statutes.add(canon_stat)
                    break

        sec_matches = re.findall(r"\bsection\s+(\d+[a-z]?)\b", q_lower)
        for s in sec_matches:
            extracted_terms.add(f"section_{s}")

        art_matches = re.findall(r"\barticle\s+(\d+[a-z]?)\b", q_lower)
        for a in art_matches:
            extracted_terms.add(f"article_{a}")

        # 5. Explicit Legal Terms & Concepts
        legal_term_lexicon = [
            "fundamental rights", "writ", "habeas corpus", "anticipatory bail",
            "cognizable", "non-cognizable", "charge sheet", "remand", "custody",
            "search and seizure", "electronic record", "dying declaration",
            "burden of proof", "admissibility", "cross examination",
            "criminal conspiracy", "organized crime", "identity theft",
            "deficiency in service", "unfair trade practice", "drunk driving",
            "corporate insolvency", "internal complaints committee",
        ]
        for lt in legal_term_lexicon:
            if lt in q_lower:
                extracted_terms.add(lt.replace(" ", "_"))

        # 6. Relationships (only if explicitly co-occurring)
        if "employer" in extracted_actors and "employee" in extracted_actors:
            extracted_relationships.add("employer_employee")
        if "spouse" in extracted_actors:
            extracted_relationships.add("matrimonial")

        # 7. Temporal context (only if explicitly stated)
        temporal_context = None
        if re.search(r"\b(?:after|post|on or after)\s+(?:july|1st july)\s+2024\b", q_lower):
            temporal_context = "post_july_2024"
        elif re.search(r"\b(?:before|prior to)\s+(?:july|1st july)\s+2024\b", q_lower):
            temporal_context = "pre_july_2024"

        # 8. Events inferred strictly from co-occurring action + object
        events: List[str] = []
        if "theft" in extracted_actions and "mobile_phone" in extracted_objects:
            events.append("phone_theft")
        if "cyber_access" in extracted_actions and "computer_resource" in extracted_objects:
            events.append("unauthorized_computer_intrusion")
        if "theft" in extracted_actions and "impersonation" in extracted_actions:
            events.append("theft_by_personation")

        return ExtractedFacts(
            actors=sorted(list(extracted_actors)),
            actions=sorted(list(extracted_actions)),
            objects=sorted(list(extracted_objects)),
            events=events,
            temporal_context=temporal_context,
            location_context=None,  # Not inferred unless explicit
            relationships=sorted(list(extracted_relationships)),
            explicit_legal_terms=sorted(list(extracted_terms)),
            jurisdiction="India",
            statutory_references=sorted(list(extracted_statutes)),
        )
