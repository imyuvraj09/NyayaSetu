"""Legal issue identification engine for Fact-First Legal Issue Routing.

Infers candidate legal issues from normalized facts with multi-issue support,
explicit evidence attribution, and deterministic confidence scoring.
"""

from typing import Any, Dict, List, Optional, Set

from research.schemas import IdentifiedLegalIssue, NormalizedFacts

# General Issue Rules mapping factual components to legal issues
ISSUE_TAXONOMY_RULES = [
    {
        "issue_id": "cyber_identity_theft_personation",
        "issue_name": "Identity Theft and Impersonation using Computer Resource",
        "required_actions": ["action:impersonation_cheating", "action:unauthorized_computer_access", "action:theft"],
        "required_objects": ["object:digital_computer_resource", "object:movable_electronic_device"],
        "required_terms": ["concept:identity_theft", "concept:section_66c", "concept:section_66d"],
        "base_regime": "IT_ACT",
    },
    {
        "issue_id": "cyber_unauthorized_access",
        "issue_name": "Unauthorized Computer Access and Data Intrusion",
        "required_actions": ["action:unauthorized_computer_access"],
        "required_objects": ["object:digital_computer_resource"],
        "required_terms": ["concept:section_43", "concept:section_66", "concept:hacking"],
        "base_regime": "IT_ACT",
    },
    {
        "issue_id": "substantive_theft_offence",
        "issue_name": "Substantive Offence of Theft and Property Deprivation",
        "required_actions": ["action:theft"],
        "required_objects": ["object:movable_electronic_device", "object:immovable_or_movable_property", "object:pecuniary_salary_funds"],
        "required_terms": ["concept:section_303", "concept:punishment_for_theft", "concept:theft"],
        "base_regime": "BNS_SUBSTANTIVE",
    },
    {
        "issue_id": "substantive_criminal_conspiracy",
        "issue_name": "Substantive Criminal Conspiracy and Agreement to Commit Offence",
        "required_actions": ["action:criminal_intimidation", "action:theft", "action:culpable_homicide_murder"],
        "required_objects": [],
        "required_terms": ["concept:criminal_conspiracy", "concept:section_61", "concept:section_120b"],
        "base_regime": "BNS_SUBSTANTIVE",
    },
    {
        "issue_id": "substantive_organized_crime",
        "issue_name": "Organized Crime and Syndicated Unlawful Activity",
        "required_actions": ["action:criminal_intimidation", "action:physical_assault_hurt"],
        "required_objects": [],
        "required_terms": ["concept:organized_crime", "concept:section_111"],
        "base_regime": "BNS_SUBSTANTIVE",
    },
    {
        "issue_id": "substantive_homicide_murder",
        "issue_name": "Substantive Offence of Culpable Homicide and Murder",
        "required_actions": ["action:culpable_homicide_murder"],
        "required_objects": [],
        "required_terms": ["concept:section_101", "concept:section_103", "concept:section_302", "concept:murder"],
        "base_regime": "BNS_SUBSTANTIVE",
    },
    {
        "issue_id": "procedural_police_arrest_powers",
        "issue_name": "Statutory Powers of Police to Arrest Without Warrant",
        "required_actions": ["action:arrest_detention"],
        "required_objects": ["object:statutory_process_document"],
        "required_terms": ["concept:section_35", "concept:section_41", "concept:cognizable", "concept:arrest"],
        "base_regime": "BNSS_PROCEDURAL",
    },
    {
        "issue_id": "procedural_bail_investigation",
        "issue_name": "Criminal Procedure Regarding Investigation and Bail",
        "required_actions": ["action:statutory_investigation", "action:lodging_complaint_fir", "action:bail_application"],
        "required_objects": ["object:statutory_process_document"],
        "required_terms": ["concept:anticipatory_bail", "concept:charge_sheet", "concept:fir", "concept:remand"],
        "base_regime": "BNSS_PROCEDURAL",
    },
    {
        "issue_id": "evidentiary_electronic_records_admissibility",
        "issue_name": "Admissibility and Certification of Electronic Records in Evidence",
        "required_actions": [],
        "required_objects": ["object:evidentiary_record", "object:digital_computer_resource"],
        "required_terms": ["concept:electronic_record", "concept:section_63", "concept:section_65b", "concept:admissibility"],
        "base_regime": "BSA_EVIDENCE",
    },
    {
        "issue_id": "evidentiary_dying_declaration",
        "issue_name": "Admissibility of Dying Declarations and Relevant Statements",
        "required_actions": ["action:culpable_homicide_murder"],
        "required_objects": ["object:evidentiary_record"],
        "required_terms": ["concept:dying_declaration", "concept:section_26", "concept:section_32"],
        "base_regime": "BSA_EVIDENCE",
    },
    {
        "issue_id": "constitutional_fundamental_rights",
        "issue_name": "Enforcement of Fundamental Constitutional Rights and Remedies",
        "required_actions": [],
        "required_objects": [],
        "required_terms": ["concept:fundamental_rights", "concept:article_21", "concept:article_14", "concept:article_19", "concept:article_32", "concept:article_226", "concept:writ"],
        "base_regime": "CONSTITUTION",
    },
    {
        "issue_id": "workplace_sexual_harassment_protection",
        "issue_name": "Prevention and Redressal of Workplace Sexual Harassment",
        "required_actions": ["action:workplace_sexual_harassment"],
        "required_objects": [],
        "required_terms": ["concept:internal_complaints_committee", "concept:posh", "concept:section_9"],
        "base_regime": "POSH_LABOUR",
    },
    {
        "issue_id": "child_sexual_abuse_protection",
        "issue_name": "Protection of Children from Sexual Offences",
        "required_actions": ["action:physical_assault_hurt", "action:workplace_sexual_harassment"],
        "required_objects": [],
        "required_terms": ["concept:pocso", "concept:child_sexual_abuse"],
        "base_regime": "POCSO_CHILD",
    },
    {
        "issue_id": "consumer_dispute_deficiency",
        "issue_name": "Consumer Remedies for Deficiency in Service and Unfair Trade Practice",
        "required_actions": ["action:unlawful_withholding_deprivation", "action:fraudulent_cheating"],
        "required_objects": [],
        "required_terms": ["concept:deficiency_in_service", "concept:unfair_trade_practice", "concept:consumer_protection"],
        "base_regime": "CONSUMER_PROTECTION",
    },
    {
        "issue_id": "motor_vehicle_offence_liability",
        "issue_name": "Motor Vehicle Regulatory Offence, Drunk Driving, and Licensing",
        "required_actions": [],
        "required_objects": ["object:motor_vehicle"],
        "required_terms": ["concept:drunk_driving", "concept:driving_licence", "concept:traffic_violation"],
        "base_regime": "MOTOR_VEHICLES",
    },
]


class LegalIssueIdentifier:
    """Infers candidate legal issues from structured normalized facts."""

    def __init__(self) -> None:
        pass

    def identify_issues(
        self,
        normalized_facts: NormalizedFacts,
        raw_query: str = "",
    ) -> List[IdentifiedLegalIssue]:
        """Identify candidate legal issues supported by explicit factual evidence."""
        q_lower = raw_query.lower()
        actions = set(normalized_facts.canonical_actions)
        objects = set(normalized_facts.canonical_objects)
        terms = set(normalized_facts.canonical_terms)
        statutes = set(normalized_facts.canonical_statutes)

        identified: List[IdentifiedLegalIssue] = []

        for rule in ISSUE_TAXONOMY_RULES:
            matched_facts: List[str] = []
            signals: List[str] = []
            score = 0.0

            # 1. Action matches
            act_matches = [a for a in rule["required_actions"] if a in actions]
            if act_matches:
                matched_facts.extend(act_matches)
                signals.append(f"matched_actions:{','.join(act_matches)}")
                score += 0.30

            # 2. Object matches
            obj_matches = [o for o in rule["required_objects"] if o in objects]
            if obj_matches:
                matched_facts.extend(obj_matches)
                signals.append(f"matched_objects:{','.join(obj_matches)}")
                score += 0.20

            # 3. Explicit Term / Section matches
            term_matches = [t for t in rule["required_terms"] if t in terms or t.replace("concept:", "").replace("_", " ") in q_lower]
            if term_matches:
                matched_facts.extend(term_matches)
                signals.append(f"matched_terms:{','.join(term_matches)}")
                score += 0.40

            # 4. Direct statute mention bonus
            rule_regime = rule["base_regime"]
            if rule_regime == "IT_ACT" and "statute:information_technology_act_2000" in statutes:
                score += 0.30
                signals.append("direct_statute:IT_Act")
            elif rule_regime == "BNS_SUBSTANTIVE" and "statute:bharatiya_nyaya_sanhita_2023" in statutes:
                score += 0.30
                signals.append("direct_statute:BNS")
            elif rule_regime == "BNSS_PROCEDURAL" and "statute:bharatiya_nagarik_suraksha_sanhita_2023" in statutes:
                score += 0.30
                signals.append("direct_statute:BNSS")
            elif rule_regime == "BSA_EVIDENCE" and "statute:bharatiya_sakshya_adhiniyam_2023" in statutes:
                score += 0.30
                signals.append("direct_statute:BSA")
            elif rule_regime == "CONSTITUTION" and "statute:constitution_of_india" in statutes:
                score += 0.30
                signals.append("direct_statute:Constitution")
            elif rule_regime == "POSH_LABOUR" and "statute:sexual_harassment_of_women_at_workplace_2013" in statutes:
                score += 0.30
                signals.append("direct_statute:POSH")
            elif rule_regime == "POCSO_CHILD" and "statute:protection_of_children_from_sexual_offences_2012" in statutes:
                score += 0.30
                signals.append("direct_statute:POCSO")
            elif rule_regime == "CONSUMER_PROTECTION" and "statute:consumer_protection_act_2019" in statutes:
                score += 0.30
                signals.append("direct_statute:Consumer_Protection")
            elif rule_regime == "MOTOR_VEHICLES" and "statute:motor_vehicles_act_1988" in statutes:
                score += 0.30
                signals.append("direct_statute:Motor_Vehicles")

            if score >= 0.30 and matched_facts:
                conf = min(0.98, score)
                identified.append(
                    IdentifiedLegalIssue(
                        issue_id=rule["issue_id"],
                        issue_name=rule["issue_name"],
                        confidence=round(conf, 4),
                        supporting_facts=matched_facts,
                        reasoning_signals=signals,
                    )
                )

        # Sort descending by confidence
        identified.sort(key=lambda x: x.confidence, reverse=True)

        if not identified:
            # Fallback general issue
            identified.append(
                IdentifiedLegalIssue(
                    issue_id="general_legal_inquiry",
                    issue_name="General Legal Inquiry with Unspecified Regime",
                    confidence=0.25,
                    supporting_facts=[],
                    reasoning_signals=["insufficient_factual_signals"],
                )
            )

        return identified
