"""
Legal Query Analyzer & Decomposer for NyayaSetu Assistant.

Performs structured query analysis:
1. Act / Statute Detection (Explicit mentions + implicit domain routing)
2. Legal Intent Detection (substantive offence, procedure, evidence, constitution, penalty)
3. Multi-Part Question Detection and Decomposition
4. Section / Concept Candidate Inference
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AuthorityRequirement(str, Enum):
    """Specifies the required legal authority for answering the inquiry."""
    STATUTE = "STATUTE"
    CASE_LAW = "CASE_LAW"
    BOTH = "BOTH"


@dataclass
class SubQuery:
    """Represents an atomic sub-question derived from a multi-part query."""
    aspect: str  # e.g., "definition", "punishment", "exceptions", "procedure", "evidence"
    sub_query_text: str
    target_act: Optional[str] = None
    target_section_candidates: List[str] = field(default_factory=list)


@dataclass
class LegalQueryAnalysis:
    """Structured representation of a legal query."""
    original_query: str
    normalized_query: str
    act: Optional[str] = None
    act_short_name: Optional[str] = None
    act_aliases: List[str] = field(default_factory=list)
    document_id: Optional[str] = None
    legal_domain: str = "General Legal Information"
    intent: str = "general_inquiry"
    entities: List[str] = field(default_factory=list)
    requested_information: List[str] = field(default_factory=list)
    section_candidates: List[str] = field(default_factory=list)
    is_multi_part: bool = False
    sub_queries: List[SubQuery] = field(default_factory=list)
    is_unindexed_statute: bool = False
    authority_requirement: AuthorityRequirement = AuthorityRequirement.STATUTE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "authority_requirement": self.authority_requirement.value,
            "act": self.act,
            "act_short_name": self.act_short_name,
            "act_aliases": self.act_aliases,
            "document_id": self.document_id,
            "legal_domain": self.legal_domain,
            "intent": self.intent,
            "entities": self.entities,
            "requested_information": self.requested_information,
            "section_candidates": self.section_candidates,
            "is_multi_part": self.is_multi_part,
            "sub_queries": [
                {"aspect": sq.aspect, "sub_query_text": sq.sub_query_text, "target_act": sq.target_act}
                for sq in self.sub_queries
            ],
        }


# Canonical Acts in the NyayaSetu Corpus
KNOWN_ACT_REGISTRY = [
    {
        "document_id": "bns_2023",
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "short_name": "BNS",
        "aliases": ["BNS", "BNS 2023", "Bharatiya Nyaya Sanhita", "IPC", "Indian Penal Code"],
        "domain": "Criminal Law",
        "keywords": [
            "murder", "culpable homicide", "punishment for murder", "theft", "rape", "assault",
            "kidnapping", "extortion", "cheating", "defamation", "offence", "offences", "penal",
            "criminal breach of trust", "hurt", "grievous hurt", "criminal conspiracy",
            "abatement", "abetment", "sedition", "general exceptions"
        ],
    },
    {
        "document_id": "bnss_2023",
        "act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "short_name": "BNSS",
        "aliases": ["BNSS", "BNSS 2023", "Bharatiya Nagarik Suraksha Sanhita", "CrPC", "Code of Criminal Procedure"],
        "domain": "Criminal Procedure",
        "keywords": [
            "investigate", "investigation", "how is a murder case investigated", "fir",
            "first information report", "arrest", "arrested", "bail", "anticipatory bail",
            "charge sheet", "cognizable", "non-cognizable", "warrant", "summons", "trial",
            "magistrate", "remand", "custody", "inquest", "search and seizure", "police officer"
        ],
    },
    {
        "document_id": "bsa_2023",
        "act_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "short_name": "BSA",
        "aliases": ["BSA", "BSA 2023", "Bharatiya Sakshya Adhiniyam", "Indian Evidence Act", "IEA", "Evidence Act"],
        "domain": "Evidence Law",
        "keywords": [
            "electronic records", "electronic record", "admissibility", "admissible", "evidence",
            "burden of proof", "presumption", "confession", "dying declaration", "witness",
            "testimony", "expert opinion", "documentary evidence", "primary evidence", "secondary evidence"
        ],
    },
    {
        "document_id": "constitution_of_india",
        "act_name": "Constitution of India",
        "short_name": "Constitution",
        "aliases": ["Constitution", "Constitution of India", "Indian Constitution"],
        "domain": "Constitutional Law",
        "keywords": [
            "article 21", "article 14", "article 19", "article 32", "article 226", "fundamental rights",
            "fundamental right", "writ", "habeas corpus", "mandamus", "certiorari", "quowarranto",
            "equality", "freedom of speech", "right to life", "personal liberty", "directive principles"
        ],
    },
    {
        "document_id": "pocso_act_2012",
        "act_name": "The Protection of Children from Sexual Offences Act, 2012",
        "short_name": "POCSO",
        "aliases": ["POCSO", "POCSO Act", "Protection of Children from Sexual Offences Act"],
        "domain": "Criminal Law / Child Protection",
        "keywords": ["pocso", "child sexual abuse", "child", "penetrative sexual assault", "aggravated sexual assault"],
    },
    {
        "document_id": "sexual_harassment_workplace_act_2013",
        "act_name": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "short_name": "POSH",
        "aliases": ["POSH", "POSH Act", "Sexual Harassment at Workplace", "Sexual Harassment of Women at Workplace"],
        "domain": "Labour Law / Women's Rights",
        "keywords": ["posh", "sexual harassment at workplace", "internal complaints committee", "icc", "local committee"],
    },
    {
        "document_id": "right_to_information_act_2005",
        "act_name": "The Right to Information Act, 2005",
        "short_name": "RTI",
        "aliases": ["RTI", "RTI Act", "Right to Information Act"],
        "domain": "Constitutional Law / Administrative Law",
        "keywords": ["rti", "right to information", "public information officer", "pio", "first appeal", "central information commission", "cic"],
    },
    {
        "document_id": "right_to_education_act_2009",
        "act_name": "The Right of Children to Free and Compulsory Education Act, 2009",
        "short_name": "RTE",
        "aliases": ["RTE", "RTE Act", "Right to Education Act"],
        "domain": "Education Law / Constitutional Rights",
        "keywords": ["rte", "right to education", "free and compulsory education", "neighbourhood school"],
    },
    {
        "document_id": "gst_act_2017",
        "act_name": "The Goods and Services Tax Act, 2017",
        "short_name": "GST",
        "aliases": ["GST", "GST Act", "Goods and Services Tax Act", "CGST"],
        "domain": "Tax Law",
        "keywords": ["gst", "goods and services tax", "input tax credit", "cgst", "sgst", "igst", "tax invoice"],
    },
    {
        "document_id": "companies_act_2013",
        "act_name": "The Companies Act, 2013",
        "short_name": "Companies Act",
        "aliases": ["Companies Act", "Companies Act, 2013", "Companies Act 2013"],
        "domain": "Corporate Law",
        "keywords": ["director", "board of directors", "csr", "corporate social responsibility", "annual general meeting", "agm", "incorporation", "share capital"],
    },
    {
        "document_id": "insolvency_bankruptcy_code_2016",
        "act_name": "The Insolvency and Bankruptcy Code, 2016",
        "short_name": "IBC",
        "aliases": ["IBC", "IBC 2016", "Insolvency and Bankruptcy Code"],
        "domain": "Corporate Law / Insolvency Law",
        "keywords": ["ibc", "cirp", "corporate insolvency resolution process", "nclt", "resolution professional", "liquidation", "operational creditor", "financial creditor"],
    },
    {
        "document_id": "consumer",
        "act_name": "Consumer Protection Act, 2019",
        "short_name": "Consumer Protection",
        "aliases": ["Consumer Protection Act, 2019", "Consumer Protection Act", "Consumer Protection", "CPA", "CPA 2019"],
        "domain": "Consumer Law",
        "keywords": ["consumer", "deficiency in service", "defect in goods", "unfair trade practice", "consumer dispute", "district commission", "remedies", "relief", "compensation"],
    },
    {
        "document_id": "motor_vehicle_act",
        "act_name": "Motor Vehicles Act",
        "short_name": "Motor Vehicles Act",
        "aliases": ["Motor Vehicles Act", "Motor Vehicle Act", "MVA"],
        "domain": "Transport Law",
        "keywords": ["motor vehicle", "driving licence", "traffic violation", "third party insurance", "accident claims tribunal", "speeding", "drunk driving"],
    },
    {
        "document_id": "it_act",
        "act_name": "Information Technology Act",
        "short_name": "IT Act",
        "aliases": ["IT Act", "Information Technology Act", "IT Act 2000"],
        "domain": "Cyber Law",
        "keywords": ["cyber crime", "hacking", "digital signature", "data protection", "cyber terrorism", "tampering computer source code"],
    },
]


class LegalQueryAnalyzer:
    """Analyzes and decomposes legal queries for targeted multi-strategy retrieval."""

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def analyze(self, query: str) -> LegalQueryAnalysis:
        """Perform comprehensive query analysis."""
        cleaned = self._normalize_text(query)
        lower_query = cleaned.lower()

        # Step 1: Detect Explicit Act Mention
        detected_act_entry = None
        for act in KNOWN_ACT_REGISTRY:
            for alias in act["aliases"]:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                if re.search(pattern, lower_query):
                    detected_act_entry = act
                    break
            if detected_act_entry:
                break

        # Step 2: Implicit Act & Domain Routing if no explicit mention
        if not detected_act_entry:
            # Check intent-priority routing rules (Procedure -> BNSS, Evidence -> BSA, Substantive -> BNS)
            if any(w in lower_query for w in [
                "investigate", "investigated", "investigation", "how is a murder case investigated",
                "how is a case investigated", "fir", "first information report", "what happens after an fir",
                "after an fir", "arrest", "arrested", "procedure for arrest", "bail", "anticipatory bail",
                "charge sheet", "cognizable", "remand", "custody", "warrant", "trial procedure"
            ]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "bnss_2023":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in [
                "what evidence", "evidence is relevant", "evidentiary value", "admissibility",
                "admissible", "electronic records", "electronic record", "burden of proof",
                "dying declaration", "expert opinion", "documentary evidence", "primary evidence",
                "secondary evidence", "testimony of witness"
            ]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "bsa_2023":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in ["article 21", "article 14", "article 19", "article 32", "article 226", "fundamental right", "fundamental rights", "writ"]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "constitution_of_india":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in ["pocso", "child sexual", "penetrative sexual assault"]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "pocso_act_2012":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in ["posh", "sexual harassment at workplace", "internal complaints committee", "icc"]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "sexual_harassment_workplace_act_2013":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in ["rti", "right to information", "public information officer", "pio"]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "right_to_information_act_2005":
                        detected_act_entry = act
                        break

            elif any(w in lower_query for w in ["murder", "culpable homicide", "theft", "rape", "assault", "kidnapping", "cheating", "extortion", "defamation"]):
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == "bns_2023":
                        detected_act_entry = act
                        break

            # Fallback: Count keyword hits across registries
            if not detected_act_entry:
                best_match = None
                max_hits = 0
                for act in KNOWN_ACT_REGISTRY:
                    hits = sum(1 for kw in act["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", lower_query))
                    if hits > max_hits:
                        max_hits = hits
                        best_match = act
                if best_match and max_hits > 0:
                    detected_act_entry = best_match

        # Step 2B: Check for Explicit Mentions of Unindexed Statutes
        unindexed_act_name = None
        if not detected_act_entry:
            act_mention_match = re.search(
                r"\b(?:under|in|of|as per|under the|in the|as per the)\s+([A-Z][a-zA-Z\s,]+(?:Act|Sanhita|Adhiniyam|Code|Rules)(?:,\s*\d{4})?)",
                cleaned,
                re.IGNORECASE,
            )
            if act_mention_match:
                candidate_act = act_mention_match.group(1).strip()
                candidate_act = re.sub(r"^(?:the\s+)", "", candidate_act, flags=re.IGNORECASE).strip()
                # Check if it matches any known act aliases
                for act in KNOWN_ACT_REGISTRY:
                    for alias in act["aliases"]:
                        if alias.lower() in candidate_act.lower():
                            detected_act_entry = act
                            break
                    if detected_act_entry:
                        break
                if not detected_act_entry:
                    unindexed_act_name = candidate_act

        # Step 3: Extract Section Numbers if explicitly present
        section_candidates = []
        sec_matches = re.findall(r"\b(?:Section|Sec\.|Article|Art\.|u/s)\s*(\d+[A-Z]?)\b", cleaned, re.IGNORECASE)
        section_candidates.extend(sec_matches)

        sec_context_matches = re.findall(r"\b(\d{1,4})\s*(?:BNS|BNSS|BSA|IPC|CrPC)\b", cleaned, re.IGNORECASE)
        section_candidates.extend(sec_context_matches)

        section_candidates = list(dict.fromkeys(section_candidates))

        # Step 4: Extract Legal Entities
        entities = []
        entity_patterns = [
            "culpable homicide", "murder", "theft", "extortion", "robbery", "dacoity",
            "rape", "assault", "hurt", "grievous hurt", "cheating", "fraud", "defamation",
            "electronic record", "electronic records", "digital signature", "fir",
            "investigation", "arrest", "bail", "anticipatory bail", "charge sheet",
            "fundamental right", "writ", "internal complaints committee", "public information officer"
        ]
        for ent in entity_patterns:
            if re.search(r"\b" + re.escape(ent) + r"\b", lower_query):
                entities.append(ent)

        # Step 5: Detect Requested Information Aspects
        requested_info = []
        if any(w in lower_query for w in ["what constitutes", "definition", "define", "what is", "elements", "meaning", "ingredients"]):
            requested_info.append("definition")
        if any(w in lower_query for w in ["punishment", "penalty", "sentenced", "punished", "imprisonment", "fine", "death penalty", "jail"]):
            requested_info.append("punishment")
        if any(w in lower_query for w in ["exception", "exceptions", "when is it not", "defence", "defenses", "difference"]):
            requested_info.append("exceptions")
        if any(w in lower_query for w in ["how is", "procedure", "how to", "investigate", "steps", "process", "filing"]):
            requested_info.append("procedure")
        if any(w in lower_query for w in ["evidence", "admissible", "admissibility", "prove", "proved", "proof"]):
            requested_info.append("evidence")
        if not requested_info:
            requested_info.append("general_statutory_rule")

        # Step 6: Detect Legal Intent
        intent = "general_inquiry"
        if "definition" in requested_info and "punishment" in requested_info:
            intent = "offence_definition_and_penalty"
        elif "punishment" in requested_info:
            intent = "penalty_punishment"
        elif "definition" in requested_info:
            intent = "substantive_definition"
        elif "procedure" in requested_info:
            intent = "procedural_inquiry"
        elif "evidence" in requested_info:
            intent = "evidentiary_rule"

        # Step 7: Detect Multi-Part Query & Decompose
        sub_queries: List[SubQuery] = []
        is_multi_part = False

        act_name_str = detected_act_entry["act_name"] if detected_act_entry else ""
        act_short_str = detected_act_entry["short_name"] if detected_act_entry else ""
        act_context = f"under {act_short_str or act_name_str}" if (act_short_str or act_name_str) else ""

        has_def = "definition" in requested_info
        has_punishment = "punishment" in requested_info
        has_proc = "procedure" in requested_info
        has_evid = "evidence" in requested_info

        entity_str = entities[0] if entities else "the offence"

        if has_def and has_punishment:
            is_multi_part = True
            sub_queries.append(
                SubQuery(
                    aspect="definition",
                    sub_query_text=f"What constitutes {entity_str} definition elements {act_context}".strip(),
                    target_act=act_name_str,
                )
            )
            sub_queries.append(
                SubQuery(
                    aspect="punishment",
                    sub_query_text=f"Punishment for {entity_str} prescribed imprisonment fine {act_context}".strip(),
                    target_act=act_name_str,
                )
            )
        elif len(requested_info) >= 2:
            is_multi_part = True
            for req in requested_info:
                sub_queries.append(
                    SubQuery(
                        aspect=req,
                        sub_query_text=f"{req} of {entity_str} {act_context}".strip(),
                        target_act=act_name_str,
                    )
                )

        # Cross-domain multi-part: e.g. "What is murder, how is it investigated, and what evidence can prove it?"
        if ("murder" in entities or "offence" in lower_query) and has_proc and has_evid:
            is_multi_part = True
            sub_queries = [
                SubQuery(
                    aspect="definition",
                    sub_query_text=f"What constitutes {entity_str} definition Bharatiya Nyaya Sanhita",
                    target_act="Bharatiya Nyaya Sanhita, 2023",
                ),
                SubQuery(
                    aspect="procedure",
                    sub_query_text=f"How is {entity_str} investigated procedure FIR investigation Bharatiya Nagarik Suraksha Sanhita",
                    target_act="Bharatiya Nagarik Suraksha Sanhita, 2023",
                ),
                SubQuery(
                    aspect="evidence",
                    sub_query_text=f"Evidence relevant to prove {entity_str} admissible Bharatiya Sakshya Adhiniyam",
                    target_act="Bharatiya Sakshya Adhiniyam, 2023",
                ),
            ]

        act_res = detected_act_entry["act_name"] if detected_act_entry else unindexed_act_name
        act_short_res = detected_act_entry["short_name"] if detected_act_entry else unindexed_act_name
        act_aliases_res = detected_act_entry["aliases"] if detected_act_entry else ([unindexed_act_name] if unindexed_act_name else [])
        doc_id_res = detected_act_entry["document_id"] if detected_act_entry else None
        domain_res = detected_act_entry["domain"] if detected_act_entry else ("Unindexed Statutory Law" if unindexed_act_name else "General Legal Information")
        is_unindexed = (unindexed_act_name is not None and detected_act_entry is None)

        # Authority Requirement Detection (Phase 9: STATUTE, CASE_LAW, BOTH)
        case_law_patterns = [
            r"\b(?:court|courts|supreme\s+court|high\s+court|judgment|judgments|precedent|precedents|case\s+law|caselaw)\b",
            r"\b(?:judicial\s+principles?|judicial\s+precedents?|judicial\s+tests?|court\s+interpretations?)\b",
            r"\b(?:what\s+have\s+courts\s+held|what\s+has\s+the\s+court\s+held|what\s+did\s+the\s+court\s+rule|courts?\s+held)\b",
            r"\b(?:holding|ratio\s+decidendi|leading\s+cases?|landmark\s+judgments?|decisions?\s+of\s+courts?)\b",
        ]
        statute_patterns = [
            r"\b(?:section|sections|sec\.?|provisions?|statutory|statute|bns|bnss|bsa|ipc|crpc|act|penal\s+code)\b",
            r"\b(?:punishment|penalty|punished\s+with|prescribed\s+for\s+it|definition\s+of|offence\s+under)\b",
            r"\b(?:procedure|time\s+limit|limitation\s+period|eligibility|remedies|grounds)\b",
        ]

        has_case_law_req = any(re.search(pat, lower_query) for pat in case_law_patterns)
        has_statute_req = any(re.search(pat, lower_query) for pat in statute_patterns) or bool(detected_act_entry) or bool(unindexed_act_name) or bool(section_candidates)

        if has_case_law_req and has_statute_req:
            auth_req = AuthorityRequirement.BOTH
        elif has_case_law_req:
            auth_req = AuthorityRequirement.CASE_LAW
        else:
            auth_req = AuthorityRequirement.STATUTE

        return LegalQueryAnalysis(
            original_query=query,
            normalized_query=cleaned,
            act=act_res,
            act_short_name=act_short_res,
            act_aliases=act_aliases_res,
            document_id=doc_id_res,
            legal_domain=domain_res,
            intent=intent,
            entities=entities,
            requested_information=requested_info,
            section_candidates=section_candidates,
            is_multi_part=is_multi_part,
            sub_queries=sub_queries,
            is_unindexed_statute=is_unindexed,
            authority_requirement=auth_req,
        )


_QUERY_ANALYZER_INSTANCE = None

def get_query_analyzer() -> LegalQueryAnalyzer:
    """Return singleton instance of LegalQueryAnalyzer."""
    global _QUERY_ANALYZER_INSTANCE
    if _QUERY_ANALYZER_INSTANCE is None:
        _QUERY_ANALYZER_INSTANCE = LegalQueryAnalyzer()
    return _QUERY_ANALYZER_INSTANCE


QueryAnalyzer = LegalQueryAnalyzer

