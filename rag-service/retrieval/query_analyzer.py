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

from retrieval.legal_question import LegalQuestion, LegalQuestionAnalyzer, QuestionType


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
    primary_issue: str = "general_legal_inquiry"
    offence: Optional[str] = None
    topic_keywords: List[str] = field(default_factory=list)
    excluded_topics: List[str] = field(default_factory=list)
    legal_question: Optional[LegalQuestion] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        res = {
            "authority_requirement": self.authority_requirement.value,
            "primary_issue": self.primary_issue,
            "offence": self.offence,
            "topic_keywords": self.topic_keywords,
            "excluded_topics": self.excluded_topics,
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
        if self.legal_question:
            res["legal_question"] = self.legal_question.to_dict()
        return res


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

    def __init__(self) -> None:
        self.legal_question_analyzer = LegalQuestionAnalyzer()

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def analyze(self, query: str) -> LegalQueryAnalysis:
        """Perform comprehensive query analysis powered by canonical LegalQuestion."""
        cleaned = self._normalize_text(query)
        lower_query = cleaned.lower()

        # Step 0: Authoritative Canonical Legal Question Analysis (Fact-First)
        lq = self.legal_question_analyzer.analyze(query)

        # Step 1: Detect Explicit Act Mention in query
        detected_act_entry = None
        for act in KNOWN_ACT_REGISTRY:
            for alias in act["aliases"]:
                pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                if re.search(pattern, lower_query):
                    detected_act_entry = act
                    break
            if detected_act_entry:
                break

        # Step 2: Implicit Act Routing driven by canonical primary domain
        if not detected_act_entry:
            domain_to_doc_id = {
                "Cybercrime / Information Technology Law": "it_act",
                "Cybercrime / Digital Investigation": "it_act",
                "Cybercrime / Financial Fraud": "it_act",
                "Criminal Law": "bns_2023",
                "Criminal Law / Sexual Offences": "bns_2023",
                "Criminal Law / Child Protection (POCSO)": "pocso_act_2012",
                "Constitutional Law": "constitution_of_india",
                "Consumer Law": "consumer",
                "Corporate Law": "companies_act_2013",
                "Insolvency Law": "insolvency_bankruptcy_code_2016",
                "Tax / GST Law": "gst_act_2017",
                "RTI / Information Law": "right_to_information_act_2005",
                "Labour Law / Workplace Sexual Harassment (POSH)": "sexual_harassment_workplace_act_2013",
                "Transport & Motor Vehicles Law": "motor_vehicle_act",
                "Law of Evidence": "bsa_2023",
                "Criminal Procedure": "bnss_2023",
            }
            target_doc_id = domain_to_doc_id.get(lq.primary_domain)
            if target_doc_id:
                for act in KNOWN_ACT_REGISTRY:
                    if act["document_id"] == target_doc_id:
                        detected_act_entry = act
                        break

            # Fallback for unindexed or specialized domains
            if not detected_act_entry:
                for act in KNOWN_ACT_REGISTRY:
                    hits = sum(1 for kw in act["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", lower_query))
                    if hits > 0:
                        detected_act_entry = act
                        break

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
                for act in KNOWN_ACT_REGISTRY:
                    for alias in act["aliases"]:
                        if alias.lower() in candidate_act.lower():
                            detected_act_entry = act
                            break
                    if detected_act_entry:
                        break
                if not detected_act_entry:
                    unindexed_act_name = candidate_act

        # Step 3: Extract Section Numbers & Articles
        section_candidates = list(dict.fromkeys(lq.statutory_sections + lq.constitutional_articles))

        # Step 4: Extract Legal Entities
        entities = lq.operative_legal_concepts

        # Step 5: Requested Information Aspects
        requested_info = [f.lower() for f in lq.requested_facets]
        if not requested_info:
            requested_info.append("general_statutory_rule")

        # Step 6: Legal Intent
        intent = "multi_facet_inquiry" if len(lq.requested_facets) > 1 else (lq.requested_facets[0].lower() if lq.requested_facets else "general_inquiry")

        # Step 7: Facet-Specific Multi-Part Sub-Query Planning
        sub_queries: List[SubQuery] = []
        is_multi_part = False

        act_res = detected_act_entry["act_name"] if detected_act_entry else (unindexed_act_name or (lq.governing_enactments[0] if lq.governing_enactments else None))
        act_short_res = detected_act_entry["short_name"] if detected_act_entry else unindexed_act_name
        act_aliases_res = detected_act_entry["aliases"] if detected_act_entry else ([unindexed_act_name] if unindexed_act_name else [])
        doc_id_res = detected_act_entry["document_id"] if detected_act_entry else None
        domain_res = lq.primary_domain or (detected_act_entry["domain"] if detected_act_entry else "Indian Statutory Law")
        is_unindexed = (unindexed_act_name is not None and detected_act_entry is None)

        # Generate facet-targeted sub-queries
        topic_context = lq.primary_legal_issue.replace("_", " ")
        if len(lq.requested_facets) >= 2 or lq.is_multi_part:
            is_multi_part = True
            for facet in lq.requested_facets:
                f_lower = facet.lower()
                if f_lower in ("offence", "offences"):
                    sq_text = f"Offences applicable {topic_context} {act_short_res or ''}".strip()
                    sq_act = act_res
                elif f_lower == "investigation":
                    sq_text = f"Investigation procedure digital forensics preservation {topic_context}".strip()
                    sq_act = "Bharatiya Nagarik Suraksha Sanhita, 2023" if "criminal" in domain_res.lower() or "cyber" in domain_res.lower() else act_res
                elif f_lower == "evidence":
                    sq_text = f"Evidence relevant to prove {topic_context} records logs".strip()
                    sq_act = "Bharatiya Sakshya Adhiniyam, 2023" if domain_res == "Law of Evidence" else act_res
                elif f_lower == "remedy":
                    sq_text = f"Legal remedies relief compensation {topic_context}".strip()
                    sq_act = act_res
                elif f_lower == "appeal":
                    sq_text = f"Appellate procedure forum limitation {topic_context}".strip()
                    sq_act = act_res
                elif f_lower == "rights":
                    sq_text = f"Statutory and legal rights of party {topic_context}".strip()
                    sq_act = act_res
                elif f_lower in ("punishment", "penalty"):
                    sq_text = f"Prescribed punishment penalties sentence {topic_context}".strip()
                    sq_act = act_res
                elif f_lower == "procedure":
                    sq_text = f"Procedure steps required compliance {topic_context}".strip()
                    sq_act = act_res
                else:
                    sq_text = f"{facet} {topic_context}".strip()
                    sq_act = act_res

                sub_queries.append(
                    SubQuery(
                        aspect=f_lower,
                        sub_query_text=sq_text,
                        target_act=sq_act,
                    )
                )

        primary_issue = lq.primary_legal_issue
        topic_keywords = lq.operative_legal_concepts
        excluded_topics: List[str] = []
        detected_offence = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else None

        # Authority requirement dynamically derived from LegalQuestion
        if "STATUTE" in lq.authority_preference and "CASE_LAW" in lq.authority_preference:
            auth_req = AuthorityRequirement.BOTH
        elif "CASE_LAW" in lq.authority_preference:
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
            primary_issue=primary_issue,
            offence=detected_offence,
            topic_keywords=topic_keywords,
            excluded_topics=excluded_topics,
            legal_question=lq,
        )


_QUERY_ANALYZER_INSTANCE = None

def get_query_analyzer() -> LegalQueryAnalyzer:
    """Return singleton instance of LegalQueryAnalyzer."""
    global _QUERY_ANALYZER_INSTANCE
    if _QUERY_ANALYZER_INSTANCE is None:
        _QUERY_ANALYZER_INSTANCE = LegalQueryAnalyzer()
    return _QUERY_ANALYZER_INSTANCE


QueryAnalyzer = LegalQueryAnalyzer

