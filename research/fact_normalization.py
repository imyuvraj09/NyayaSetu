"""Fact normalization and legal canonicalization layer.

Maps extracted factual variations, colloquial expressions, and legal terms to
canonical representations while strictly preserving original evidence and provenance.
"""

from typing import Dict, List, Optional

from research.schemas import ExtractedFacts, NormalizedFactItem, NormalizedFacts

ACTION_CANONICAL_MAP: Dict[str, str] = {
    "theft": "action:theft",
    "murder": "action:culpable_homicide_murder",
    "arrest": "action:arrest_detention",
    "assault": "action:physical_assault_hurt",
    "cyber_access": "action:unauthorized_computer_access",
    "impersonation": "action:impersonation_cheating",
    "threat": "action:criminal_intimidation",
    "sale": "action:transfer_sale",
    "withholding": "action:unlawful_withholding_deprivation",
    "cheating": "action:fraudulent_cheating",
    "investigation": "action:statutory_investigation",
    "filing": "action:lodging_complaint_fir",
    "bail": "action:bail_application",
    "sexual_harassment": "action:workplace_sexual_harassment",
}

OBJECT_CANONICAL_MAP: Dict[str, str] = {
    "mobile_phone": "object:movable_electronic_device",
    "computer_resource": "object:digital_computer_resource",
    "property": "object:immovable_or_movable_property",
    "money_salary": "object:pecuniary_salary_funds",
    "vehicle": "object:motor_vehicle",
    "legal_document": "object:statutory_process_document",
    "evidence_record": "object:evidentiary_record",
}

ACTOR_CANONICAL_MAP: Dict[str, str] = {
    "unknown_person": "party:unidentified_individual",
    "police": "party:police_investigating_authority",
    "employer": "party:commercial_employer",
    "employee": "party:employed_worker",
    "accused": "party:accused_person",
    "victim": "party:victim_complainant",
    "magistrate": "party:judicial_magistrate_court",
    "spouse": "party:marital_spouse",
    "child": "party:protected_minor_child",
    "director": "party:corporate_director",
    "consumer": "party:protected_consumer",
    "driver": "party:motor_vehicle_operator",
}

STATUTE_CANONICAL_MAP: Dict[str, str] = {
    "BNS": "statute:bharatiya_nyaya_sanhita_2023",
    "BNSS": "statute:bharatiya_nagarik_suraksha_sanhita_2023",
    "BSA": "statute:bharatiya_sakshya_adhiniyam_2023",
    "Constitution": "statute:constitution_of_india",
    "IT_Act": "statute:information_technology_act_2000",
    "POCSO": "statute:protection_of_children_from_sexual_offences_2012",
    "POSH": "statute:sexual_harassment_of_women_at_workplace_2013",
    "Consumer_Protection": "statute:consumer_protection_act_2019",
    "Motor_Vehicles": "statute:motor_vehicles_act_1988",
}


class FactNormalizer:
    """Canonicalizes extracted factual components while preserving original evidence."""

    def __init__(self) -> None:
        pass

    def normalize(self, facts: ExtractedFacts, raw_query: str = "") -> NormalizedFacts:
        """Produce NormalizedFacts containing both raw facts and canonicalized items."""
        items: List[NormalizedFactItem] = []

        # 1. Actions
        for act in facts.actions:
            canon = ACTION_CANONICAL_MAP.get(act, f"action:{act}")
            items.append(
                NormalizedFactItem(
                    category="action",
                    original_value=act,
                    canonical_value=canon,
                    normalization_source="action_canonical_map",
                )
            )

        # 2. Objects
        for obj in facts.objects:
            canon = OBJECT_CANONICAL_MAP.get(obj, f"object:{obj}")
            items.append(
                NormalizedFactItem(
                    category="object",
                    original_value=obj,
                    canonical_value=canon,
                    normalization_source="object_canonical_map",
                )
            )

        # 3. Actors
        for actor in facts.actors:
            canon = ACTOR_CANONICAL_MAP.get(actor, f"party:{actor}")
            items.append(
                NormalizedFactItem(
                    category="actor",
                    original_value=actor,
                    canonical_value=canon,
                    normalization_source="actor_canonical_map",
                )
            )

        # 4. Explicit Statutes
        for stat in facts.statutory_references:
            canon = STATUTE_CANONICAL_MAP.get(stat, f"statute:{stat.lower()}")
            items.append(
                NormalizedFactItem(
                    category="statutory_reference",
                    original_value=stat,
                    canonical_value=canon,
                    normalization_source="statute_canonical_map",
                )
            )

        # 5. Explicit Legal Terms & Concepts
        for term in facts.explicit_legal_terms:
            items.append(
                NormalizedFactItem(
                    category="legal_term",
                    original_value=term,
                    canonical_value=f"concept:{term.lower()}",
                    normalization_source="term_canonicalizer",
                )
            )

        # 6. Relationships
        for rel in facts.relationships:
            items.append(
                NormalizedFactItem(
                    category="relationship",
                    original_value=rel,
                    canonical_value=f"relationship:{rel}",
                    normalization_source="relationship_canonicalizer",
                )
            )

        return NormalizedFacts(items=items, raw_facts=facts)
