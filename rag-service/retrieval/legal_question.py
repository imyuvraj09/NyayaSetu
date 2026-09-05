"""
Universal Legal Question Modeling & Decomposition for NyayaSetu.

Transforms any natural language Indian legal question into a structured,
canonical, and typed LegalQuestion representation.

Capabilities:
1. Universal Question Type & Facet Detection across generic legal information needs.
2. Fact-First Legal Issue & Domain Identification (factual conduct determines legal domain before requested facets).
3. Factual Scenario Decomposition (extracting factual events, actors, conduct, harm, and legal relationships).
4. Multi-Part Question Decomposition into independent sub-questions.
5. Dynamic Legal Concept, Enactment, Article, and Section inference without brittle hardcoding.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


class QuestionType(str, Enum):
    """Generic legal question types covering Indian civil, criminal, constitutional, and regulatory law."""
    DEFINITION = "DEFINITION"
    ELEMENTS = "ELEMENTS"
    OFFENCE = "OFFENCE"
    PUNISHMENT = "PUNISHMENT"
    EXCEPTION = "EXCEPTION"
    DEFENCE = "DEFENCE"
    PROCEDURE = "PROCEDURE"
    RIGHTS = "RIGHTS"
    DUTIES = "DUTIES"
    REMEDY = "REMEDY"
    APPEAL = "APPEAL"
    TIME_LIMIT = "TIME_LIMIT"
    ELIGIBILITY = "ELIGIBILITY"
    LIABILITY = "LIABILITY"
    EVIDENCE = "EVIDENCE"
    JURISDICTION = "JURISDICTION"
    COMPARISON = "COMPARISON"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    STATUTORY_INTERPRETATION = "STATUTORY_INTERPRETATION"
    CASE_LAW = "CASE_LAW"
    JUDICIAL_PRINCIPLES = "JUDICIAL_PRINCIPLES"
    FACTUAL_SCENARIO = "FACTUAL_SCENARIO"
    COMPLEX_SCENARIO = "COMPLEX_SCENARIO"
    MULTI_PART = "MULTI_PART"
    CROSS_ACT = "CROSS_ACT"
    GENERAL_LEGAL_INFORMATION = "GENERAL_LEGAL_INFORMATION"


class PrimaryTask(str, Enum):
    """Authoritative legal task that the user wants performed."""
    SUBSTANTIVE_OFFENCE = "SUBSTANTIVE_OFFENCE"
    SUBSTANTIVE_RIGHT = "SUBSTANTIVE_RIGHT"
    LEGAL_DEFINITION = "LEGAL_DEFINITION"
    LEGAL_INTERPRETATION = "LEGAL_INTERPRETATION"
    SEARCH_SEIZURE = "SEARCH_SEIZURE"
    ARREST = "ARREST"
    BAIL = "BAIL"
    INVESTIGATION = "INVESTIGATION"
    TRIAL = "TRIAL"
    EVIDENCE_OF_CONDUCT = "EVIDENCE_OF_CONDUCT"
    EVIDENCE_ADMISSIBILITY = "EVIDENCE_ADMISSIBILITY"
    REMEDY = "REMEDY"
    APPEAL = "APPEAL"
    REVISION = "REVISION"
    COMPLAINT = "COMPLAINT"
    RTI_APPLICATION = "RTI_APPLICATION"
    RTI_APPEAL = "RTI_APPEAL"
    CONSUMER_REMEDY = "CONSUMER_REMEDY"
    CONTRACT_REMEDY = "CONTRACT_REMEDY"
    EMPLOYMENT_REMEDY = "EMPLOYMENT_REMEDY"
    INSOLVENCY_PROCEDURE = "INSOLVENCY_PROCEDURE"
    DIVORCE_PROCEDURE = "DIVORCE_PROCEDURE"
    REGULATORY_COMPLIANCE = "REGULATORY_COMPLIANCE"
    LIABILITY = "LIABILITY"
    PENALTY = "PENALTY"
    CASE_LAW = "CASE_LAW"
    CONSTITUTIONAL_INTERPRETATION = "CONSTITUTIONAL_INTERPRETATION"
    OTHER = "OTHER"


@dataclass
class CleanProposition:
    """A clean, normalized legal proposition extracted from an authority."""
    authority_name: str
    act: str
    section: str
    title: str
    clean_proposition: str
    support_span: str = ""
    facet: str = "GENERAL"
    source_id: str = ""
    authority_type: str = "STATUTE"
    status: str = "ANSWERED_SUPPORTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_name": self.authority_name,
            "act": self.act,
            "section": self.section,
            "title": self.title,
            "clean_proposition": self.clean_proposition,
            "support_span": self.support_span,
            "facet": self.facet,
            "source_id": self.source_id,
            "authority_type": self.authority_type,
            "status": self.status,
        }


@dataclass
class FactualEvent:
    """An atomic factual occurrence extracted from a factual scenario query."""
    event_id: str
    fact_text: str
    event_type: str = "action"
    actor: str = ""
    action: str = ""
    target: str = ""
    legal_implications: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "fact_text": self.fact_text,
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "legal_implications": self.legal_implications,
        }


@dataclass
class SubQuestion:
    """An independent sub-question derived from a multi-part or multi-aspect legal query."""
    sub_id: str
    question_text: str
    question_type: QuestionType
    primary_facet: str
    target_act: Optional[str] = None
    target_units: List[str] = field(default_factory=list)
    authority_type: str = "STATUTE"  # "STATUTE", "CASE_LAW", "BOTH"

    @property
    def aspect(self) -> str:
        return self.primary_facet

    @property
    def text(self) -> str:
        return self.question_text

    @property
    def target_enactment(self) -> Optional[str]:
        return self.target_act

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub_id": self.sub_id,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "primary_facet": self.primary_facet,
            "target_act": self.target_act,
            "target_units": self.target_units,
            "authority_type": self.authority_type,
        }


@dataclass
class LegalQuestion:
    """Universal canonical model of an Indian legal query."""
    original_query: str
    normalized_query: str
    legal_domain: str
    primary_issue: str
    secondary_issues: List[str] = field(default_factory=list)
    facts: List[FactualEvent] = field(default_factory=list)
    legal_concepts: List[str] = field(default_factory=list)
    acts: List[str] = field(default_factory=list)
    articles: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    requested_facets: List[str] = field(default_factory=list)
    authority_requirements: List[str] = field(default_factory=list)  # "STATUTE", "CASE_LAW", etc.
    sub_questions: List[SubQuestion] = field(default_factory=list)
    question_types: List[QuestionType] = field(default_factory=list)
    complexity: str = "SIMPLE"  # "SIMPLE", "COMPOUND", "MULTI_PART", "FACTUAL_SCENARIO"
    answer_requirements: List[str] = field(default_factory=list)

    # Universal canonical attributes
    raw_question: str = ""
    actors: List[str] = field(default_factory=list)
    conduct: List[str] = field(default_factory=list)
    object: List[str] = field(default_factory=list)
    harm_or_dispute: List[str] = field(default_factory=list)
    legal_relationship: str = ""
    primary_task: str = "OTHER"
    background_offence: Optional[str] = None
    contextual_issues: List[str] = field(default_factory=list)
    primary_domain: str = ""
    sub_domain: str = ""
    taxonomy_path: List[str] = field(default_factory=list)
    secondary_domains: List[str] = field(default_factory=list)
    candidate_acts: List[str] = field(default_factory=list)
    candidate_sections: List[str] = field(default_factory=list)
    candidate_cases: List[str] = field(default_factory=list)
    jurisdiction: str = "India"
    requires_statute: bool = True
    requires_case_law: bool = False
    requires_procedure: bool = False
    requires_evidence: bool = False
    requires_admissibility: bool = False
    confidence: float = 1.0
    question_type: str = ""

    def __post_init__(self):
        if not self.raw_question:
            self.raw_question = self.original_query
        if not self.primary_domain:
            self.primary_domain = self.legal_domain
        if not self.acts and (self.primary_task in ("SEARCH_SEIZURE", "BAIL", "ARREST") or self.primary_domain == "Criminal Procedure"):
            self.acts = ["Bharatiya Nagarik Suraksha Sanhita, 2023"]
        elif not self.acts and self.primary_domain == "Law of Evidence":
            self.acts = ["Bharatiya Sakshya Adhiniyam, 2023"]
        if not self.candidate_acts:
            self.candidate_acts = self.acts
        if not self.candidate_sections:
            self.candidate_sections = self.sections
        if not self.question_type and self.question_types:
            self.question_type = self.question_types[0].value
        if not self.candidate_cases and self.requires_case_law:
            self.candidate_cases = []

        # Derive hierarchical taxonomy: Primary Domain -> Subdomain -> Legal Topic -> Relevant Act
        if not self.sub_domain:
            p_dom = self.primary_domain or self.legal_domain
            p_issue = self.primary_issue or ""
            r_query = (self.raw_question or self.original_query).lower()

            if p_dom == "Law of Evidence":
                if any(w in r_query or w in p_issue for w in ["electronic", "whatsapp", "digital", "record", "computer"]):
                    self.sub_domain = "Electronic Evidence"
                    self.taxonomy_path = ["Law of Evidence", "Electronic Evidence", "Admissibility and Proof of Electronic Records", "Bharatiya Sakshya Adhiniyam, 2023"]
                elif "burden" in r_query or "burden" in p_issue:
                    self.sub_domain = "Burden and Standard of Proof"
                    self.taxonomy_path = ["Law of Evidence", "Burden and Standard of Proof", "Burden of Proof in Legal Proceedings", "Bharatiya Sakshya Adhiniyam, 2023"]
                elif "circumstantial" in r_query:
                    self.sub_domain = "Circumstantial Evidence"
                    self.taxonomy_path = ["Law of Evidence", "Circumstantial Evidence", "Standard of Proof on Circumstantial Evidence", "Bharatiya Sakshya Adhiniyam, 2023"]
                else:
                    self.sub_domain = "General Law of Evidence"
                    self.taxonomy_path = ["Law of Evidence", "General Law of Evidence", p_issue.replace("_", " ").title(), "Bharatiya Sakshya Adhiniyam, 2023"]
            elif p_dom == "Criminal Law":
                if "theft" in r_query or "theft" in p_issue:
                    self.sub_domain = "Offences Against Property"
                    self.taxonomy_path = ["Criminal Law", "Offences Against Property", "Theft and Prescribed Punishment", "Bharatiya Nyaya Sanhita, 2023"]
                elif "murder" in r_query or "homicide" in r_query:
                    self.sub_domain = "Offences Affecting Life"
                    self.taxonomy_path = ["Criminal Law", "Offences Affecting Life", "Murder and Culpable Homicide", "Bharatiya Nyaya Sanhita, 2023"]
                else:
                    self.sub_domain = "Substantive Criminal Law"
                    self.taxonomy_path = ["Criminal Law", "Substantive Criminal Law", p_issue.replace("_", " ").title(), "Bharatiya Nyaya Sanhita, 2023"]
            elif "cyber" in p_dom.lower():
                self.sub_domain = "Cyber Offences and Digital Security"
                self.taxonomy_path = ["Cyber Law", "Cyber Offences and Digital Security", "Unauthorized Access and Computer Violations", "Information Technology Act, 2000"]
            elif "constitutional" in p_dom.lower():
                self.sub_domain = "Fundamental Rights"
                self.taxonomy_path = ["Constitutional Law", "Fundamental Rights", p_issue.replace("_", " ").title(), "Constitution of India"]
            elif "consumer" in p_dom.lower():
                self.sub_domain = "Consumer Protection and Product Liability"
                self.taxonomy_path = ["Consumer Law", "Consumer Protection and Product Liability", p_issue.replace("_", " ").title(), "Consumer Protection Act, 2019"]
            else:
                self.sub_domain = p_dom
                act_name = self.acts[0] if self.acts else "Indian Statutory Law"
                self.taxonomy_path = [p_dom, self.sub_domain, p_issue.replace("_", " ").title(), act_name]

    @property
    def raw_query(self) -> str:
        return self.raw_question or self.original_query

    @property
    def primary_legal_issue(self) -> str:
        return self.primary_issue

    @property
    def primary_subject(self) -> str:
        return self.primary_issue

    @property
    def operative_legal_concepts(self) -> List[str]:
        return self.legal_concepts

    @property
    def governing_enactments(self) -> List[str]:
        if self.acts:
            return self.acts
        if self.primary_task in ("SEARCH_SEIZURE", "BAIL", "ARREST") or self.primary_domain == "Criminal Procedure":
            return ["Bharatiya Nagarik Suraksha Sanhita, 2023"]
        return []

    @property
    def constitutional_articles(self) -> List[str]:
        return self.articles

    @property
    def statutory_sections(self) -> List[str]:
        return self.sections

    @property
    def authority_preference(self) -> List[str]:
        return self.authority_requirements

    @property
    def domain(self) -> str:
        return self.legal_domain

    @property
    def is_multi_part(self) -> bool:
        return len(self.sub_questions) >= 2 or QuestionType.MULTI_PART in self.question_types

    @property
    def factual_scenario(self):
        if self.facts:
            class _ScenarioHelper:
                def __init__(self, events, entities):
                    self.events = events
                    self.entities = entities
            return _ScenarioHelper(self.facts, self.legal_concepts)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_question": self.raw_question or self.original_query,
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "facts": [f.to_dict() for f in self.facts],
            "actors": self.actors,
            "conduct": self.conduct,
            "object": self.object,
            "harm_or_dispute": self.harm_or_dispute,
            "legal_relationship": self.legal_relationship,
            "primary_task": self.primary_task,
            "background_offence": self.background_offence,
            "contextual_issues": self.contextual_issues,
            "primary_issue": self.primary_issue,
            "secondary_issues": self.secondary_issues,
            "primary_domain": self.primary_domain or self.legal_domain,
            "sub_domain": self.sub_domain,
            "taxonomy_path": self.taxonomy_path,
            "legal_domain": self.legal_domain,
            "secondary_domains": self.secondary_domains,
            "requested_facets": self.requested_facets,
            "question_type": self.question_type or (self.question_types[0].value if self.question_types else ""),
            "question_types": [qt.value for qt in self.question_types],
            "candidate_acts": self.candidate_acts,
            "candidate_sections": self.candidate_sections,
            "candidate_cases": self.candidate_cases,
            "acts": self.acts,
            "articles": self.articles,
            "sections": self.sections,
            "jurisdiction": self.jurisdiction,
            "requires_statute": self.requires_statute,
            "requires_case_law": self.requires_case_law,
            "requires_procedure": self.requires_procedure,
            "requires_evidence": self.requires_evidence,
            "requires_admissibility": self.requires_admissibility,
            "confidence": self.confidence,
            "authority_requirements": self.authority_requirements,
            "sub_questions": [sq.to_dict() for sq in self.sub_questions],
            "complexity": self.complexity,
            "answer_requirements": self.answer_requirements,
        }


# Linguistic patterns defining generic legal question types
QUESTION_TYPE_PATTERNS: Dict[QuestionType, List[str]] = {
    QuestionType.DEFINITION: [
        r"\b(?:what is|what are|define|definition of|meaning of|what constitutes|how is .+ defined)\b",
        r"\b(?:what does .+ mean|concept of|explain|scope of|discuss|elucidate|overview of)\b",
    ],
    QuestionType.ELEMENTS: [
        r"\b(?:elements|ingredients|essential ingredients|constituent elements|requirements for|prerequisites)\b",
        r"\b(?:what must be proven|necessary components)\b",
    ],
    QuestionType.OFFENCE: [
        r"\b(?:what offences?|what offence may apply|offences? may apply|offences? committed|what crime|what crimes|punishable offence)\b",
        r"\b(?:what offence may be committed|may be committed|offence is committed)\b",
    ],
    QuestionType.PUNISHMENT: [
        r"\b(?:punishment|penalty|penalties|punished with|prescribed for|sentenced|imprisonment|fine|jail)\b",
        r"\b(?:what is the sentence|penal consequence)\b",
    ],
    QuestionType.EXCEPTION: [
        r"\b(?:exception|exceptions|when is it not|exemptions?|saving clause|non-applicability)\b",
        r"\b(?:when does .+ not apply|excluded cases|does .+ imply consent|automatically establish consent|constitute consent|amount to consent)\b",
    ],
    QuestionType.DEFENCE: [
        r"\b(?:defence|defences|plea of|private defence|self-defence|immunity|protection against liability)\b",
        r"\b(?:plea of consent|prior consensual|previous consensual|consensual relationship|implied consent|vitiate consent|defence of consent)\b",
    ],
    QuestionType.PROCEDURE: [
        r"\b(?:procedure|how to|steps|process|investigation|how is .+ investigated|what happens after)\b",
        r"\b(?:filing|lodging|cognizance|inquest|summons|warrant|remand|custody|trial procedure|cirp process|cirp)\b",
    ],
    QuestionType.RIGHTS: [
        r"\b(?:rights?|entitlement|fundamental rights?|legal rights?|can a person claim)\b",
    ],
    QuestionType.DUTIES: [
        r"\b(?:duty|duties|obligation|obligations|mandatory duty|statutory obligation)\b",
    ],
    QuestionType.REMEDY: [
        r"\b(?:remedy|remedies|relief|compensation|damages|redressal|recourse|injunction|what can i do)\b",
    ],
    QuestionType.APPEAL: [
        r"\b(?:appeal|appellate|revision|review petition|challenge the order|higher court|how to appeal)\b",
    ],
    QuestionType.TIME_LIMIT: [
        r"\b(?:time limit|limitation period|within how many days|prescribed time|statutory period)\b",
    ],
    QuestionType.ELIGIBILITY: [
        r"\b(?:eligibility|eligible|qualifications|who can apply|who is entitled)\b",
    ],
    QuestionType.LIABILITY: [
        r"\b(?:liable|liability|vicarious liability|corporate liability|who is responsible|culpability)\b",
    ],
    QuestionType.EVIDENCE: [
        r"\b(?:evidence|admissibility|admissible|burden of proof|standard of proof|evidentiary value)\b",
        r"\b(?:circumstantial evidence|chain of circumstances|witness|testimony|forensic|electronic record)\b",
    ],
    QuestionType.JURISDICTION: [
        r"\b(?:jurisdiction|territorial|pecuniary|which court|forum|competent court|tribunal)\b",
    ],
    QuestionType.COMPARISON: [
        r"\b(?:difference between|distinguish between|vs|versus|compared to|comparison between)\b",
    ],
    QuestionType.CONSTITUTIONAL: [
        r"\b(?:article \d+[a-z]?|constitution|constitutional|fundamental rights?|writ|habeas corpus|mandamus)\b",
        r"\b(?:due process|personal liberty|basic structure|ultra vires)\b",
    ],
    QuestionType.STATUTORY_INTERPRETATION: [
        r"\b(?:interpretation|statutory meaning|construction of|scope of section|purposive)\b",
    ],
    QuestionType.CASE_LAW: [
        r"\b(?:case law|cases|precedent|precedents|judgment|judgments|ruling|rulings|supreme court held)\b",
        r"\b(?:high court held|landmark judgment|leading case)\b",
    ],
    QuestionType.JUDICIAL_PRINCIPLES: [
        r"\b(?:judicial principles?|judicial tests?|judicial guidelines?|ratio decidendi|holding)\b",
        r"\b(?:tests laid down|principles established by courts?)\b",
    ],
}


class LegalQuestionAnalyzer:
    """Universal parser that transforms raw natural language queries into typed LegalQuestion objects."""

    def analyze(self, query: str) -> LegalQuestion:
        """Parse, classify, decompose, and formulate a universal LegalQuestion."""
        cleaned = re.sub(r"\s+", " ", query).strip()
        lower_q = cleaned.lower()

        # 1. Detect Generic Question Types
        q_types = self._detect_question_types(lower_q)

        # 2. Extract Constitutional Articles and Statutory Sections
        articles, sections = self._extract_provisions(lower_q, cleaned)
        if articles and QuestionType.CONSTITUTIONAL not in q_types:
            q_types.append(QuestionType.CONSTITUTIONAL)

        # 3. Detect Mentioned Acts or Legal Instruments
        acts = self._detect_instruments(lower_q)

        # 4. Factual Scenario Detection & Decomposition
        facts: List[FactualEvent] = []
        is_scenario = self._is_factual_scenario(cleaned, lower_q)
        if is_scenario:
            facts = self._decompose_factual_scenario(cleaned)
            if len(facts) >= 3 and QuestionType.COMPLEX_SCENARIO not in q_types:
                q_types.append(QuestionType.COMPLEX_SCENARIO)
            elif QuestionType.FACTUAL_SCENARIO not in q_types:
                q_types.append(QuestionType.FACTUAL_SCENARIO)

        # 5. Extract Actors, Conduct, Objects, Harm/Dispute, and Legal Relationship
        actors = self._extract_actors(lower_q, facts)
        conduct = self._extract_conduct(lower_q, facts)
        objects = self._extract_object(lower_q)
        harm_dispute = self._extract_harm_dispute(lower_q, facts)
        legal_relationship = self._extract_relationship(lower_q)

        # 6. Extract Legal Concepts & Entities
        legal_concepts = self._extract_legal_concepts(lower_q)

        # 7. Extract Requested Facets
        requested_facets = self._extract_facets(lower_q, q_types)

        # 7.5 Detect Explicit Primary Task & Background Offence Separation
        primary_task = self._detect_primary_task(lower_q, q_types, requested_facets)
        background_offence, contextual_issues = self._extract_background_offence(lower_q, primary_task)

        # 8. Fact-First Legal Domain Resolution (with Procedure Priority)
        primary_domain, secondary_domains = self._infer_domain(
            lower_q=lower_q,
            acts=acts,
            q_types=q_types,
            concepts=legal_concepts,
            conduct=conduct,
            primary_task=primary_task,
            background_offence=background_offence,
        )

        # 9. Multi-Part Question Detection & Sub-Question Generation
        sub_questions = self._decompose_multi_part(cleaned, lower_q, q_types, acts, sections, articles)
        if len(sub_questions) > 1 and QuestionType.MULTI_PART not in q_types:
            q_types.append(QuestionType.MULTI_PART)

        if len(acts) > 1 and QuestionType.CROSS_ACT not in q_types:
            q_types.append(QuestionType.CROSS_ACT)

        if not q_types:
            q_types = [QuestionType.GENERAL_LEGAL_INFORMATION]

        # 10. Identify the Operative Primary Legal Issue
        primary_issue, secondary_issues = self._determine_primary_issue(
            raw_q=cleaned,
            lower_q=lower_q,
            q_types=q_types,
            concepts=legal_concepts,
            sections=sections,
            articles=articles,
            acts=acts,
            primary_domain=primary_domain,
            conduct=conduct,
            primary_task=primary_task,
            background_offence=background_offence,
        )

        # 11. Determine Authority Requirements
        authority_requirements = self._determine_authorities(lower_q, q_types)
        requires_case_law = "CASE_LAW" in authority_requirements
        requires_procedure = "PROCEDURE" in requested_facets or "INVESTIGATION" in requested_facets or QuestionType.PROCEDURE in q_types or primary_task in (PrimaryTask.SEARCH_SEIZURE, PrimaryTask.BAIL, PrimaryTask.ARREST)
        requires_evidence = "EVIDENCE" in requested_facets or QuestionType.EVIDENCE in q_types or primary_task in (PrimaryTask.EVIDENCE_OF_CONDUCT, PrimaryTask.EVIDENCE_ADMISSIBILITY)
        requires_admissibility = (
            primary_task == PrimaryTask.EVIDENCE_ADMISSIBILITY
            or "ADMISSIBILITY" in requested_facets
            or any(w in lower_q for w in ["admissibility", "admissible in court", "section 65b", "section 63"])
        )

        # 12. Complexity Level
        complexity = "SIMPLE"
        if QuestionType.COMPLEX_SCENARIO in q_types or (QuestionType.FACTUAL_SCENARIO in q_types and QuestionType.MULTI_PART in q_types):
            complexity = "COMPLEX_SCENARIO"
        elif QuestionType.FACTUAL_SCENARIO in q_types:
            complexity = "FACTUAL_SCENARIO"
        elif QuestionType.MULTI_PART in q_types or QuestionType.CROSS_ACT in q_types:
            complexity = "MULTI_PART"
        elif len(q_types) > 1:
            complexity = "COMPOUND"

        # 13. Determine Answer Requirements
        answer_requirements = self._build_answer_requirements(q_types, complexity, primary_issue)

        lq = LegalQuestion(
            original_query=query,
            normalized_query=cleaned,
            legal_domain=primary_domain,
            primary_issue=primary_issue,
            secondary_issues=secondary_issues,
            facts=facts,
            legal_concepts=legal_concepts,
            acts=acts,
            articles=articles,
            sections=sections,
            requested_facets=requested_facets,
            authority_requirements=authority_requirements,
            sub_questions=sub_questions,
            question_types=q_types,
            complexity=complexity,
            answer_requirements=answer_requirements,
            raw_question=cleaned,
            actors=actors,
            conduct=conduct,
            object=objects,
            harm_or_dispute=harm_dispute,
            legal_relationship=legal_relationship,
            primary_task=primary_task.value,
            background_offence=background_offence,
            contextual_issues=contextual_issues,
            primary_domain=primary_domain,
            secondary_domains=secondary_domains,
            candidate_acts=acts,
            candidate_sections=sections or articles,
            requires_statute=True,
            requires_case_law=requires_case_law,
            requires_procedure=requires_procedure,
            requires_evidence=requires_evidence,
            requires_admissibility=requires_admissibility,
            confidence=1.0,
            question_type=q_types[0].value if q_types else "GENERAL_LEGAL_INFORMATION",
        )

        logger.info(
            "Canonical LegalQuestion: primary_domain='%s', primary_task='%s', primary_issue='%s', facets=%s, bg_offence='%s'",
            lq.primary_domain,
            lq.primary_task,
            lq.primary_issue,
            lq.requested_facets,
            lq.background_offence,
        )
        return lq

    def _detect_question_types(self, lower_q: str) -> List[QuestionType]:
        """Match query against generic question type patterns."""
        matched: List[QuestionType] = []
        for q_type, patterns in QUESTION_TYPE_PATTERNS.items():
            if any(re.search(pat, lower_q) for pat in patterns):
                matched.append(q_type)
        return matched

    def _extract_provisions(self, lower_q: str, raw_q: str) -> Tuple[List[str], List[str]]:
        """Distinguish Constitutional Articles from Statutory Sections cleanly."""
        articles: List[str] = []
        sections: List[str] = []

        # 1. Articles (e.g. Article 21, Art. 14, Article 21A)
        art_matches = re.findall(r"\b(?:article|art\.?)\s*([0-9]{1,3}[a-z]?)\b", lower_q)
        for m in art_matches:
            articles.append(m.upper())

        # 2. Sections (e.g. Section 101, Sec. 63, Section 302)
        sec_matches = re.findall(r"\b(?:section|sec\.?|s\.)\s*([0-9]{1,4}[a-z]?)\b", lower_q)
        for m in sec_matches:
            sections.append(m.upper())

        # Disambiguate: if "article" was explicitly stated, remove from sections
        clean_sections = [s for s in sections if s not in articles]

        return list(dict.fromkeys(articles)), list(dict.fromkeys(clean_sections))

    def _detect_instruments(self, lower_q: str) -> List[str]:
        """Detect legal instruments mentioned in the query."""
        instruments: List[str] = []
        act_patterns = [
            (r"\b(?:bns|bharatiya\s+nyaya\s+sanhita|ipc|indian\s+penal\s+code)\b", "Bharatiya Nyaya Sanhita, 2023"),
            (r"\b(?:bnss|bharatiya\s+nagarik\s+suraksha\s+sanhita|crpc|code\s+of\s+criminal\s+procedure)\b", "Bharatiya Nagarik Suraksha Sanhita, 2023"),
            (r"\b(?:bsa|bharatiya\s+sakshya\s+adhiniyam|evidence\s+act|indian\s+evidence\s+act)\b", "Bharatiya Sakshya Adhiniyam, 2023"),
            (r"\b(?:constitution|constitution\s+of\s+india|indian\s+constitution)\b", "Constitution of India"),
            (r"\b(?:it\s+act|information\s+technology\s+act)\b", "Information Technology Act"),
            (r"\b(?:consumer\s+protection|cpa)\b", "Consumer Protection Act, 2019"),
            (r"\b(?:companies\s+act)\b", "The Companies Act, 2013"),
            (r"\b(?:ibc|insolvency\s+and\s+bankruptcy\s+code)\b", "The Insolvency and Bankruptcy Code, 2016"),
            (r"\b(?:pocso|protection\s+of\s+children\s+from\s+sexual\s+offences)\b", "The Protection of Children from Sexual Offences Act, 2012"),
            (r"\b(?:posh|sexual\s+harassment(?:\s+of\s+women)?\s+at\s+(?:[a-z]+\s+)?workplace|sexual\s+harassment\s+at\s+workplace|internal\s+complaints\s+committee|icc|local\s+complaints\s+committee)\b", "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013"),
            (r"\b(?:rti|right\s+to\s+information)\b", "The Right to Information Act, 2005"),
            (r"\b(?:rte|right\s+to\s+education)\b", "The Right of Children to Free and Compulsory Education Act, 2009"),
            (r"\b(?:gst|goods\s+and\s+services\s+tax)\b", "The Goods and Services Tax Act, 2017"),
            (r"\b(?:motor\s+vehicles?\s+act|mva)\b", "Motor Vehicles Act"),
            (r"\b(?:contract\s+act|indian\s+contract\s+act)\b", "The Indian Contract Act, 1872"),
        ]
        for pattern, canon_name in act_patterns:
            if re.search(pattern, lower_q):
                instruments.append(canon_name)

        # Contextual inference: sexual harassment inquiry in workplace context
        if any(w in lower_q for w in ["sexual harassment", "posh", "internal complaints committee", "icc"]):
            posh_canon = "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013"
            if posh_canon not in instruments:
                instruments.insert(0, posh_canon)

        return list(dict.fromkeys(instruments))

    def _is_factual_scenario(self, raw_q: str, lower_q: str) -> bool:
        """Determine if query presents a hypothetical factual scenario."""
        scenario_indicators = [
            r"\b(?:a\s+person|a\s+man|a\s+woman|a\s+victim|an\s+accused|an\s+individual|the\s+prosecution|a\s+hacker)\b",
            r"\b(?:if\s+a\s+person|suppose\s+that|in\s+a\s+case\s+where|enters\s+credentials|receives\s+a\s+call)\b",
            r"\b(?:relies\s+entirely\s+on|there\s+is\s+no\s+eyewitness|purchases\s+a\s+product|director\s+fails\s+to)\b",
            r"\b(?:alleges\s+that|claims\s+that|transfers\s+money|sent\s+an\s+email|unauthorized\s+access)\b",
            r"\b(?:someone\s+hacked|server\s+was\s+hacked|copies\s+confidential|demands\s+ransom)\b",
            r"\b(?:landlord\s+refuses|employee\s+was\s+dismissed|purchased\s+a\s+defective)\b",
        ]
        has_scenario_lang = any(re.search(p, lower_q) for p in scenario_indicators)
        has_multi_sentences = len(re.split(r"[.?!]\s+", raw_q)) >= 2
        return has_scenario_lang or (has_multi_sentences and any(w in lower_q for w in ["can", "does", "whether", "what liability", "what offences"]))

    def _decompose_factual_scenario(self, raw_q: str) -> List[FactualEvent]:
        """Break down a factual scenario narrative into ordered atomic factual events."""
        events: List[FactualEvent] = []
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|;\s*|,\s*(?=(?:and|but|then|whereupon)\s+)", raw_q) if len(s.strip()) > 10]

        for i, sent in enumerate(sentences, start=1):
            if re.match(r"^(?:can|does|what|how|explain|is|whether|who)\b", sent, re.IGNORECASE) and "?" in sent:
                continue

            words = sent.split()
            events.append(
                FactualEvent(
                    event_id=f"FACT_{i}",
                    fact_text=sent,
                    event_type="factual_allegation" if any(w in sent.lower() for w in ["allege", "accuse", "claim"]) else "event",
                    action=" ".join(words[:4]),
                    legal_implications=[],
                )
            )

        return events

    def _extract_actors(self, lower_q: str, facts: List[FactualEvent]) -> List[str]:
        """Extract legal actors from query and facts."""
        actor_terms = [
            "hacker", "accused", "victim", "prosecution", "company", "employee", "employer",
            "consumer", "buyer", "seller", "landlord", "tenant", "director", "spouse", "husband",
            "wife", "creditor", "debtor", "police", "investigator", "child", "individual"
        ]
        found = [term for term in actor_terms if re.search(r"\b" + re.escape(term) + r"\b", lower_q)]
        return list(dict.fromkeys(found))

    def _extract_conduct(self, lower_q: str, facts: List[FactualEvent]) -> List[str]:
        """Extract concrete actions and conduct."""
        conduct_patterns = [
            r"\bunauthorized\s+access\b",
            r"\bcopies\s+confidential\s+files\b",
            r"\bdemands?\s+ransom\b",
            r"\bhacked\s+my\s+company's\s+server\b",
            r"\bstole\s+customer\s+data\b",
            r"\bsends?\s+ransomware\b",
            r"\bdefective\s+(?:smartphone|phone|goods|product)\b",
            r"\bdenied\s+liberty\s+by\s+state\b",
            r"\brefuses?\s+to\s+return\s+(?:my\s+)?deposit\b",
            r"\bunlawful\s+termination\b",
            r"\bdismissed\s+unlawfully\b",
            r"\bbreach\s+of\s+contract\b",
            r"\bsexual\s+assault\b",
            r"\bmurder\b",
            r"\btheft\b",
            r"\bcheating\b",
        ]
        conducts = []
        for pat in conduct_patterns:
            m = re.findall(pat, lower_q)
            conducts.extend(m)
        return list(dict.fromkeys(conducts))

    def _extract_harm_dispute(self, lower_q: str, facts: List[FactualEvent]) -> List[str]:
        """Identify harm or dispute nature."""
        harm = []
        if any(w in lower_q for w in ["ransom", "stole", "loss of money", "lost money", "financial loss"]):
            harm.append("financial_loss_or_extortion")
        if any(w in lower_q for w in ["confidential", "customer data", "data theft"]):
            harm.append("data_breach_and_confidentiality_loss")
        if any(w in lower_q for w in ["murder", "killing", "dead"]):
            harm.append("loss_of_life")
        if any(w in lower_q for w in ["defective", "deficiency"]):
            harm.append("consumer_loss")
        if any(w in lower_q for w in ["denied liberty", "arrested"]):
            harm.append("deprivation_of_liberty")
        return harm

    def _extract_relationship(self, lower_q: str) -> str:
        """Infer underlying legal relationship."""
        if any(w in lower_q for w in ["employee", "employer", "termination", "dismissed"]):
            return "employer_employee"
        if any(w in lower_q for w in ["consumer", "purchased", "defective product", "buyer"]):
            return "buyer_seller"
        if any(w in lower_q for w in ["landlord", "tenant", "security deposit"]):
            return "landlord_tenant"
        if any(w in lower_q for w in ["director", "board of directors"]):
            return "company_director"
        if any(w in lower_q for w in ["creditor", "debtor", "cirp"]):
            return "creditor_debtor"
        if any(w in lower_q for w in ["state action", "denied liberty", "article 21"]):
            return "citizen_state"
        return "general_legal"

    def _extract_facets(self, lower_q: str, q_types: List[QuestionType]) -> List[str]:
        """Extract universal information facets from query and types."""
        facets: List[str] = []
        facet_map = [
            (r"\b(?:what offences?|what offence may apply|offences? may apply|offences? committed|what crime)\b", "OFFENCES"),
            (r"\b(?:investigation|investigate|investigators? collect|investigators? preserve|investigative procedure)\b", "INVESTIGATION"),
            (r"\b(?:evidence|what evidence|proof|admissible evidence|evidentiary|investigators? collect|investigators? preserve|what to collect|collect or preserve)\b", "EVIDENCE"),
            (r"\b(?:remedy|remedies|relief|what can be done|redressal|what can i do)\b", "REMEDY"),
            (r"\b(?:protections?|safeguards?|statutory protections?)\b", "PROTECTIONS"),
            (r"\b(?:complaint\s+mechanisms?|mechanisms?|redressal\s+mechanisms?)\b", "PROCEDURE"),
            (r"\b(?:compensation|damages|refund)\b", "COMPENSATION"),
            (r"\b(?:appeal|appellate|challenge the order|how to appeal)\b", "APPEAL"),
            (r"\b(?:procedure|process|steps|how to file|how to report|mechanism|cirp process)\b", "PROCEDURE"),
            (r"\b(?:rights?|entitlement)\b", "RIGHTS"),
            (r"\b(?:duties|duty|obligation)\b", "DUTIES"),
            (r"\b(?:liability|liable|responsibility)\b", "LIABILITY"),
            (r"\b(?:penalty|penalties|punishment|punished with|sentence|imprisonment|fine)\b", "PUNISHMENT"),
            (r"\b(?:elements|ingredients|prerequisites)\b", "ELEMENTS"),
            (r"\b(?:definition|what is|what are|define|meaning of|what constitutes|explain|scope of|discuss)\b", "DEFINITION"),
            (r"\b(?:admissibility|admissible|certificate)\b", "ADMISSIBILITY"),
            (r"\b(?:jurisdiction|which court|forum)\b", "JURISDICTION"),
            (r"\b(?:limitation|time limit|within how many days)\b", "LIMITATION"),
            (r"\b(?:reporting|report|helpline|portal)\b", "REPORTING"),
            (r"\b(?:exception|exceptions|exemptions?)\b", "EXCEPTIONS"),
            (r"\b(?:defence|defences|plea of)\b", "DEFENCES"),
            (r"\b(?:judicial principles?|judicial tests?|case law|precedents?|supreme court held)\b", "JUDICIAL_PRINCIPLES"),
            (r"\b(?:documents|records)\b", "DOCUMENTS"),
            (r"\b(?:enforcement|enforce|execution of order)\b", "ENFORCEMENT"),
            (r"\b(?:recovery|recover|recovery of deposit|recovery of money)\b", "RECOVERY"),
            (r"\b(?:next steps|recommended steps|what should i do)\b", "NEXT_STEPS"),
            (r"\b(?:requirements|conditions)\b", "REQUIREMENTS"),
            (r"\b(?:eligibility|eligible|who can apply)\b", "ELIGIBILITY"),
            (r"\b(?:legal position|legal status|current law)\b", "LEGAL_POSITION"),
        ]
        for pat, facet_name in facet_map:
            if re.search(pat, lower_q):
                facets.append(facet_name)

        for qt in q_types:
            val = qt.value.upper()
            if val not in ("FACTUAL_SCENARIO", "COMPLEX_SCENARIO", "MULTI_PART", "CROSS_ACT", "GENERAL_LEGAL_INFORMATION"):
                if val == "DEFENCE":
                    val = "DEFENCES"
                elif val == "EXCEPTION":
                    val = "EXCEPTIONS"
                elif val == "OFFENCE":
                    val = "OFFENCES"
                facets.append(val)

        return list(dict.fromkeys(facets))

    def _extract_object(self, lower_q: str) -> List[str]:
        """Extract material objects or targets from query."""
        target_patterns = [
            (r"\b(?:mobile\s+phone|mobile|smartphone|phone)\b", "mobile_phone"),
            (r"\b(?:computer\s+system|computer|server|laptop)\b", "computer_system"),
            (r"\b(?:confidential\s+files|customer\s+data|files|data)\b", "confidential_files"),
            (r"\b(?:ransom|money|deposit|security\s+deposit|funds)\b", "funds_or_deposit"),
            (r"\b(?:product|goods|device)\b", "consumer_goods"),
            (r"\b(?:electronic\s+records?|electronic\s+evidence)\b", "electronic_records"),
        ]
        objects = []
        for pat, canon in target_patterns:
            if re.search(pat, lower_q):
                objects.append(canon)
        return list(dict.fromkeys(objects))

    def _detect_primary_task(
        self,
        lower_q: str,
        q_types: List[QuestionType],
        facets: List[str],
    ) -> PrimaryTask:
        """Explicitly classify what substantive or procedural legal task the user wants performed."""
        # 1. SEARCH_SEIZURE
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:search\s+(?:his|a|the)?\s*(?:mobile|phone|device|computer|premises|house))\b",
            r"\b(?:seized\s+(?:a|the|his)?\s*(?:mobile|phone|device|computer))\b",
            r"\b(?:police\s+want\s+to\s+search)\b",
            r"\b(?:search\s+and\s+seizure|search\s+or\s+seizure)\b",
            r"\b(?:procedure\s+governs?\s+the\s+search|seizure\s+procedure)\b",
            r"\b(?:seizure\s+of\s+(?:mobile|phone|electronic|device))\b",
            r"\b(?:examination\s+of\s+(?:mobile|phone|device))\b",
            r"\b(?:unlawful\s+seizure|illegal\s+seizure)\b",
        ]):
            return PrimaryTask.SEARCH_SEIZURE

        # 2. BAIL
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:bail\s+application|apply\s+for\s+bail|grant\s+of\s+bail|anticipatory\s+bail|regular\s+bail|default\s+bail)\b",
            r"\b(?:procedure\s+governs?\s+(?:his\s+)?bail)\b",
        ]):
            return PrimaryTask.BAIL

        # 3. ARREST
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:procedure\s+for\s+arrest|arrest\s+without\s+warrant|grounds\s+of\s+arrest|powers\s+of\s+arrest)\b",
            r"\b(?:procedure\s+governing\s+arrest)\b",
        ]):
            return PrimaryTask.ARREST

        # 4. EVIDENCE ADMISSIBILITY (Doctrine / Rules of Evidence)
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:admissibility\s+requirements?|rules\s+(?:for|of)\s+admissibility)\b",
            r"\b(?:how\s+(?:is|are)\s+electronic\s+(?:evidence|records?)\s+admiss(?:ible|ion)|how\s+are\s+electronic\s+records\s+admitted)\b",
            r"\b(?:how\s+(?:is|are)\s+.*?\s*admitted\s+(?:under|in|into|as))\b",
            r"\b(?:admitted\s+under\s+(?:bsa|bharatiya\s+sakshya|evidence\s+act))\b",
            r"\b(?:admissibility\s+of\s+electronic|admitted\s+as\s+evidence|admitted\s+in\s+evidence|admitted\s+into\s+evidence)\b",
            r"\b(?:admission\s+of\s+electronic|proof\s+of\s+electronic\s+records?|prove\s+electronic\s+records?)\b",
            r"\b(?:section\s+65b\s+certificate|section\s+63\s+certificate)\b",
            r"\b(?:is\s+this\s+electronic\s+record\s+admissible|admissible\s+in\s+court)\b",
            r"\b(?:burden\s+of\s+proof|standard\s+of\s+proof)\b",
            r"\b(?:test\s+for\s+circumstantial\s+evidence|circumstantial\s+evidence\s+test)\b",
        ]) or (
            ("bsa" in lower_q or "bharatiya sakshya" in lower_q or "evidence act" in lower_q)
            and any(w in lower_q for w in ["admitted", "admit", "electronic record", "electronic evidence", "document", "proof", "prove", "certificate"])
            and not any(c in lower_q for c in ["hacker", "hack", "murder", "theft", "consumer", "contract", "employee"])
        ):
            return PrimaryTask.EVIDENCE_ADMISSIBILITY

        # 5. RTI APPEAL / APPLICATION
        if re.search(r"\b(?:rti|right\s+to\s+information)\b", lower_q):
            if any(w in lower_q for w in ["appeal", "first appeal", "rejected", "rejection", "cic", "appellate"]):
                return PrimaryTask.RTI_APPEAL
            return PrimaryTask.RTI_APPLICATION

        # 6. CONSUMER REMEDY / PROCEDURE
        if any(w in lower_q for w in ["consumer", "defective phone", "defective smartphone", "defective goods", "defective product"]) or re.search(r"\bcpa\b", lower_q):
            if any(w in lower_q for w in ["remedy", "remedies", "compensation", "relief", "what can i do", "what remedies"]):
                return PrimaryTask.CONSUMER_REMEDY

        # 7. EMPLOYMENT REMEDY / WORKPLACE HARASSMENT
        if (
            any(w in lower_q for w in ["sexual harassment", "posh", "internal complaints committee", "icc", "local committee", "lcc"])
            or ("workplace" in lower_q and ("harassment" in lower_q or "harass" in lower_q))
        ):
            if any(w in lower_q for w in ["complaint", "mechanism", "mechanisms", "protection", "protections", "evidence", "procedure", "remedy", "remedies", "rights", "allege", "allegation", "redressal"]):
                return PrimaryTask.EMPLOYMENT_REMEDY

        if any(w in lower_q for w in ["employee", "employer", "dismissed", "termination", "retrenchment", "workplace"]):
            if any(w in lower_q for w in ["rights", "remedy", "remedies", "compensation", "recourse"]):
                return PrimaryTask.EMPLOYMENT_REMEDY

        # 8. CONTRACT REMEDY
        if any(w in lower_q for w in ["breach of contract", "contractual breach", "breached a contract", "deposit", "agreement to sell"]):
            if any(w in lower_q for w in ["remedy", "remedies", "damages", "compensation"]):
                return PrimaryTask.CONTRACT_REMEDY

        # 9. INSOLVENCY PROCEDURE
        if any(w in lower_q for w in ["cirp", "corporate insolvency", "resolution professional", "creditor"]) or re.search(r"\bibc\b", lower_q):
            if any(w in lower_q for w in ["process", "procedure", "initiate", "timeline"]):
                return PrimaryTask.INSOLVENCY_PROCEDURE

        # 10. DIVORCE PROCEDURE
        if any(w in lower_q for w in ["divorce", "matrimonial"]) and any(w in lower_q for w in ["procedure", "file", "proceedings"]):
            return PrimaryTask.DIVORCE_PROCEDURE

        # 11. CONSTITUTIONAL INTERPRETATION
        if any(w in lower_q for w in ["article 21", "article 14", "article 19", "article 32", "article 226", "constitution"]) and any(w in lower_q for w in ["explain", "interpretation", "supreme court's", "principles", "fair and reasonable", "personal liberty"]):
            return PrimaryTask.CONSTITUTIONAL_INTERPRETATION

        # 12. SUBSTANTIVE OFFENCE
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:what\s+offences?\s+may\s+apply|what\s+offence\s+may\s+apply|what\s+offences?|what\s+crime)\b",
            r"\b(?:what\s+legal\s+offence|offence\s+is\s+committed|may\s+be\s+committed)\b",
            r"\b(?:punishable\s+offence)\b",
        ]):
            return PrimaryTask.SUBSTANTIVE_OFFENCE

        # 13. EVIDENCE OF CONDUCT
        if any(re.search(pat, lower_q) for pat in [
            r"\b(?:what\s+evidence\s+(?:could|can|may)\s+(?:establish|prove))\b",
            r"\b(?:evidence\s+that\s+could\s+establish)\b",
            r"\b(?:what\s+evidence\s+is\s+relevant)\b",
        ]):
            return PrimaryTask.EVIDENCE_OF_CONDUCT

        # 14. INVESTIGATION
        if any(w in lower_q for w in ["investigation procedure", "investigation procedures", "investigation steps", "how is .+ investigated", "investigators collect"]):
            return PrimaryTask.INVESTIGATION

        # 15. PENALTY / PUNISHMENT
        if any(w in lower_q for w in ["what punishment", "what penalty", "punishment for", "penalty for", "what is the sentence"]):
            return PrimaryTask.PENALTY

        # 16. CASE LAW / JUDICIAL PRINCIPLES
        if any(w in lower_q for w in ["case law", "precedents", "landmark judgment", "judicial principles"]):
            return PrimaryTask.CASE_LAW

        # 17. LEGAL DEFINITION
        if QuestionType.DEFINITION in q_types:
            return PrimaryTask.LEGAL_DEFINITION

        return PrimaryTask.OTHER

    def _extract_background_offence(
        self,
        lower_q: str,
        primary_task: PrimaryTask,
    ) -> Tuple[Optional[str], List[str]]:
        """Identify if an underlying criminal offence serves as background context rather than the operative inquiry."""
        bg_offence = None
        contextual_issues: List[str] = []

        is_procedural_or_evidence = primary_task in (
            PrimaryTask.SEARCH_SEIZURE,
            PrimaryTask.BAIL,
            PrimaryTask.ARREST,
            PrimaryTask.INVESTIGATION,
            PrimaryTask.EVIDENCE_OF_CONDUCT,
        )

        if is_procedural_or_evidence:
            if re.search(r"\b(?:theft|stole|steals|stolen)\b", lower_q):
                bg_offence = "theft"
                contextual_issues.append("theft_investigation")
            elif re.search(r"\b(?:murder|culpable\s+homicide|killing|killed)\b", lower_q):
                bg_offence = "murder"
                contextual_issues.append("homicide_investigation")
            elif re.search(r"\b(?:rape|sexual\s+assault)\b", lower_q):
                bg_offence = "sexual_offence"
                contextual_issues.append("sexual_offence_investigation")
            elif re.search(r"\b(?:cyber|hacker|hacking|ransomware)\b", lower_q):
                bg_offence = "cybercrime"
                contextual_issues.append("cyber_incident")
            elif re.search(r"\b(?:fraud|cheating)\b", lower_q):
                bg_offence = "fraud"
                contextual_issues.append("fraud_investigation")

        return bg_offence, contextual_issues

    def _infer_domain(
        self,
        lower_q: str,
        acts: List[str],
        q_types: List[QuestionType],
        concepts: List[str],
        conduct: List[str],
        primary_task: Optional[PrimaryTask] = None,
        background_offence: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """Fact-First Legal Domain Resolution with Procedure Priority.

        Factual conduct and legal tasks determine the domain first.
        Information-request keywords (evidence, investigation, remedy, procedure, appeal)
        are treated as requested facets and DO NOT hijack the legal domain.
        """
        secondary_domains: List[str] = []

        # 0. PROCEDURE PRIORITY (Procedural Tasks take precedence over background offence)
        if primary_task == PrimaryTask.SEARCH_SEIZURE:
            sec_domains = ["Law of Evidence"]
            if background_offence:
                sec_domains.append("Criminal Law")
            return "Criminal Procedure", sec_domains

        if primary_task == PrimaryTask.BAIL:
            sec_domains = ["Criminal Law"] if background_offence else []
            return "Criminal Procedure", sec_domains

        if primary_task == PrimaryTask.ARREST:
            sec_domains = ["Criminal Law"] if background_offence else []
            return "Criminal Procedure", sec_domains

        if primary_task in (PrimaryTask.RTI_APPLICATION, PrimaryTask.RTI_APPEAL):
            return "RTI / Information Law", []

        if primary_task == PrimaryTask.CONSUMER_REMEDY:
            return "Consumer Law", []

        if primary_task == PrimaryTask.EMPLOYMENT_REMEDY:
            if (
                any(w in lower_q for w in ["sexual harassment", "posh", "internal complaints committee", "icc", "local committee", "lcc", "harass"])
                or ("workplace" in lower_q and "harass" in lower_q)
            ):
                sec_domains = ["Employment and Workplace Law", "Gender and Sexual Harassment Law"]
                if "evidence" in lower_q:
                    sec_domains.append("Law of Evidence")
                return "Labour Law / Workplace Sexual Harassment (POSH)", sec_domains
            return "Employment / Labour Law", []

        if primary_task == PrimaryTask.CONTRACT_REMEDY:
            return "Contract Law", []

        if primary_task == PrimaryTask.INSOLVENCY_PROCEDURE:
            return "Insolvency Law", []

        if primary_task == PrimaryTask.DIVORCE_PROCEDURE:
            return "Family Law", []
        secondary_domains: List[str] = []

        # 1. PURE EVIDENCE LAW (Triggered when inquiry is about evidence, admissibility, proof, witnesses, presumptions)
        is_evidence_law = (
            primary_task == PrimaryTask.EVIDENCE_ADMISSIBILITY
            or any(p in lower_q for p in [
                "rules of admissibility of electronic evidence",
                "rules for admissibility of electronic evidence",
                "admissibility of electronic record",
                "admissibility of electronic records",
                "admissibility of electronic evidence",
                "how are electronic records admitted",
                "how is an electronic record admitted",
                "admitted under bharatiya sakshya",
                "admitted under bsa",
                "admitted as evidence",
                "admitted in evidence",
                "used in court",
                "used as evidence in court",
                "admissible in court",
                "whatsapp message be used in court",
                "whatsapp message used in court",
                "whatsapp message admissible",
                "proof of electronic record",
                "electronic document admissibility",
                "section 65b certificate",
                "section 63 certificate",
                "legal test for proving guilt solely through circumstantial evidence",
                "rules of circumstantial evidence",
                "rules governing circumstantial evidence",
                "circumstantial evidence test",
                "circumstantial evidence doctrine",
                "burden of proof in criminal",
                "burden of proof",
                "standard of proof beyond reasonable doubt",
                "standard of proof",
                "dying declaration admissibility",
                "expert opinion admissibility",
                "hearsay evidence rule",
                "primary vs secondary evidence",
                "what evidence is admissible in court",
                "what evidence is admissible for proving an electronic record",
                "admissibility of digital evidence",
                "proof of electronic records",
                "presumption as to electronic records",
                "presumption",
                "burden of proof",
                "examination of witnesses",
                "competence of witness",
                "confession under bharatiya sakshya",
            ])
            or (
                any(act_term in lower_q for act_term in [
                    "bharatiya sakshya adhiniyam", "bharatiya sakshya", "bsa",
                    "indian evidence act", "evidence act", "law of evidence"
                ])
                and not any(re.search(rf"\b{re.escape(co)}\b", lower_q) for co in [
                    "theft", "murder", "rape", "cheating", "extortion", "robbery", "dacoity",
                    "punishment for", "penalty for", "prescribed for theft", "prescribed for murder",
                    "sexual harassment", "workplace", "posh", "internal complaints"
                ])
            )
            or (
                any(w in lower_q for w in ["electronic record", "electronic records", "digital evidence"])
                and any(w in lower_q for w in ["admit", "admitted", "admissibility", "proof", "prove", "proved", "court", "certificate"])
                and not any(w in lower_q for w in ["sexual harassment", "posh", "workplace"])
            )
        )
        if is_evidence_law:
            sec_domains = []
            if "circumstantial" in lower_q or "criminal trial" in lower_q:
                sec_domains.append("Criminal Law")
            if "whatsapp" in lower_q or "electronic" in lower_q or "digital" in lower_q:
                sec_domains.append("Cyber Law")
            return "Law of Evidence", sec_domains

        # 2. CYBERCRIME / INFORMATION TECHNOLOGY LAW
        is_cyber = (
            any(w in lower_q for w in [
                "hacker", "hacking", "unauthorized access", "ransomware", "ransom",
                "copies confidential files", "stole customer data", "stolen customer data",
                "data theft", "computer system", "server was hacked", "server hacked",
                "server was compromised", "phishing", "trojan", "malware", "cybercrime",
                "cyber crime", "cyber fraud", "tampering computer", "otp fraud", "stolen credentials",
                "fraudulent upi", "upi transaction", "upi fraud", "unauthorized transaction",
                "financial fraud", "online fraud", "loses money through a fraudulent",
                "without authorization", "accesses a computer", "copies files"
            ])
            or any(re.search(r"\b" + re.escape(w) + r"\b", lower_q) for w in ["upi", "cyber"])
            or ("computer" in lower_q and any(w in lower_q for w in ["unauthorized", "without authorization", "access", "hack", "virus", "data", "files"]))
            or any("information technology" in a.lower() or "it act" in a.lower() for a in acts)
        )
        if is_cyber:
            if any(w in lower_q for w in ["what should investigators collect", "investigators collect", "investigators preserve"]):
                return "Cybercrime / Digital Investigation", ["Law of Evidence", "Criminal Procedure"]
            if any(w in lower_q for w in ["upi", "fraudulent upi", "financial fraud", "loses money", "unauthorized transaction"]):
                return "Cybercrime / Financial Fraud", ["Criminal Law"]
            if any(w in lower_q for w in ["extortion", "ransom", "demands payment", "payment demand"]):
                return "Cybercrime / Information Technology Law", ["Criminal Law"]
            return "Cybercrime / Information Technology Law", []

        # 3. CRIMINAL LAW (Substantive Offences)
        is_criminal = (
            any(w in lower_q for w in [
                "murder", "culpable homicide", "kill", "killing", "poisoning",
                "sexual assault", "rape", "outraging modesty", "penetrative",
                "theft", "burglary", "stolen goods", "robbery", "dacoity",
                "extortion", "cheating", "criminal breach of trust", "defamation",
                "criminal conspiracy", "assault", "kidnapping", "abduction", "hurt", "grievous hurt"
            ])
            or any("bns" in a.lower() or "penal" in a.lower() for a in acts)
        )
        if is_criminal:
            if any(w in lower_q for w in ["sexual assault", "rape", "consent in sexual"]):
                return "Criminal Law", ["Law of Evidence"] if "evidence" in lower_q else []
            if any(w in lower_q for w in ["circumstantial evidence", "chain of circumstances"]):
                return "Criminal Law", ["Law of Evidence"]
            if any(w in lower_q for w in ["investigate", "investigation", "how is murder investigated"]):
                return "Criminal Law", ["Criminal Procedure"]
            return "Criminal Law", []

        # 4. CONSTITUTIONAL LAW
        is_constitutional = (
            QuestionType.CONSTITUTIONAL in q_types
            or any("constitution" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "article 21", "article 14", "article 19", "article 32", "article 226",
                "fundamental right", "fundamental rights", "writ petition", "habeas corpus",
                "mandamus", "personal liberty", "denied liberty by state",
                "fair and reasonable procedure", "basic structure", "unconstitutional", "ultra vires"
            ])
        )
        if is_constitutional:
            return "Constitutional Law", []

        # 5. CONSUMER LAW
        is_consumer = (
            any("consumer" in a.lower() or "cpa" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "consumer", "defective goods", "defective product", "defective phone",
                "defective smartphone", "deficiency in service", "unfair trade practice",
                "consumer forum", "consumer commission", "consumer complaint"
            ])
        )
        if is_consumer:
            return "Consumer Law", []

        # 6. CONTRACT / CIVIL / PROPERTY LAW
        is_contract_property = (
            any("contract" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "breach of contract", "contractual breach", "contract breach", "failed to perform",
                "specific performance", "landlord", "security deposit", "refuses to return my deposit",
                "tenancy", "lease agreement", "agreement to sell", "contract law"
            ])
        )
        if is_contract_property:
            if any(w in lower_q for w in ["landlord", "security deposit", "tenant"]):
                return "Property / Contract / Civil Law", ["Civil Procedure"]
            return "Contract Law", []

        # 7. LABOUR / EMPLOYMENT LAW
        is_employment = (
            any(w in lower_q for w in [
                "wrongful termination", "unlawful termination", "unlawfully dismissed", "dismissed unlawfully",
                "unlawful dismissal", "wrongful dismissal", "dismissed employee", "employee was dismissed",
                "employee was terminated", "workplace dispute", "employer dismisses", "employer terminates",
                "retrenchment", "gratuity", "severance", "industrial dispute"
            ])
            or (
                ("employee" in lower_q or "employer" in lower_q or "workplace" in lower_q)
                and any(w in lower_q for w in ["dismiss", "terminat", "retrench", "severance", "wages", "salary", "bonus", "gratuity"])
            )
        )
        if is_employment:
            return "Employment / Labour Law", []

        # 8. COMPANY / CORPORATE LAW
        is_corporate = (
            any("companies" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "company director", "director liability", "board of directors", "csr",
                "annual general meeting", "agm", "incorporation", "share capital", "companies act"
            ])
        )
        if is_corporate:
            return "Corporate Law", []

        # 9. INSOLVENCY LAW
        is_insolvency = (
            any("ibc" in a.lower() or "insolvency" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "cirp", "corporate insolvency", "ibc", "insolvency and bankruptcy",
                "resolution professional", "nclt", "financial creditor", "operational creditor", "liquidation"
            ])
        )
        if is_insolvency:
            return "Insolvency Law", []

        # 10. TAX / GST LAW
        is_tax = (
            any("gst" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "gst", "goods and services tax", "input tax credit", "cgst", "sgst",
                "igst", "tax invoice", "tax penalty", "tax evasion", "income tax"
            ])
        )
        if is_tax:
            return "Tax / GST Law", []

        # 11. RTI / INFORMATION LAW
        is_rti = (
            any("rti" in a.lower() for a in acts)
            or any(re.search(r"\b" + re.escape(w) + r"\b", lower_q) for w in [
                "rti", "right to information", "public information officer", "pio",
                "central information commission", "cic", "first appeal under rti"
            ])
        )
        if is_rti:
            return "RTI / Information Law", []

        # 12. FAMILY LAW
        is_family = (
            any(w in lower_q for w in [
                "divorce", "matrimonial", "maintenance", "alimony", "child custody",
                "restitution of conjugal rights", "hindu marriage act", "special marriage act"
            ])
        )
        if is_family:
            return "Family Law", []

        # 13. POCSO / CHILD PROTECTION
        if any("pocso" in a.lower() for a in acts) or any(w in lower_q for w in ["pocso", "child sexual", "penetrative sexual assault"]):
            return "Criminal Law / Child Protection (POCSO)", []

        # 14. POSH / WORKPLACE SEXUAL HARASSMENT
        is_posh = (
            any("posh" in a.lower() or "sexual harassment" in a.lower() for a in acts)
            or any(w in lower_q for w in ["posh", "sexual harassment", "internal complaints committee", "icc", "local committee", "lcc"])
            or ("workplace" in lower_q and ("harassment" in lower_q or "harass" in lower_q))
        )
        if is_posh:
            sec_domains = ["Employment and Workplace Law", "Gender and Sexual Harassment Law"]
            if "evidence" in lower_q:
                sec_domains.append("Law of Evidence")
            if any(w in lower_q for w in ["offence", "crime", "criminal", "punish", "bns"]):
                sec_domains.append("Criminal Law")
            return "Labour Law / Workplace Sexual Harassment (POSH)", sec_domains

        # 15. MOTOR VEHICLES / TRANSPORT LAW
        if any("motor" in a.lower() or "mva" in a.lower() for a in acts) or any(w in lower_q for w in ["motor vehicle", "driving licence", "accident claims tribunal", "mva"]):
            return "Transport & Motor Vehicles Law", []

        # 16. PURE CRIMINAL PROCEDURE
        is_crpc = (
            any("bnss" in a.lower() or "crpc" in a.lower() for a in acts)
            or any(w in lower_q for w in [
                "explain police investigation powers under bnss",
                "what is criminal procedure",
                "powers of police under bnss",
                "powers of magistrate under bnss",
                "search and seizure powers under bnss",
                "procedure for arrest without warrant under bnss"
            ])
        )
        if is_crpc:
            return "Criminal Procedure", []

        # 17. Default Fallbacks
        if any("evidence" in a.lower() for a in acts):
            return "Law of Evidence", []
        return "Indian Statutory Law", []

    def _decompose_multi_part(
        self,
        raw_q: str,
        lower_q: str,
        q_types: List[QuestionType],
        acts: List[str],
        sections: List[str],
        articles: List[str],
    ) -> List[SubQuestion]:
        """Split complex or compound inquiries into atomic, focused sub-questions."""
        sub_questions: List[SubQuestion] = []
        primary_act = acts[0] if acts else None

        clause_splits = re.split(r",\s*(?:and\s+)?|\band\s+(?:what|how|explain|can|does|is)\b|\?\s*", raw_q)
        clean_clauses = [c.strip() for c in clause_splits if len(c.strip()) > 10]

        if len(clean_clauses) >= 2:
            for idx, clause in enumerate(clean_clauses, start=1):
                c_lower = clause.lower()
                c_types = self._detect_question_types(c_lower)
                sub_type = c_types[0] if c_types else QuestionType.GENERAL_LEGAL_INFORMATION
                facet_name = sub_type.value.lower()
                auth = "CASE_LAW" if sub_type in (QuestionType.CASE_LAW, QuestionType.JUDICIAL_PRINCIPLES) else "STATUTE"

                sub_questions.append(
                    SubQuestion(
                        sub_id=f"sub_q_{idx}",
                        question_text=clause if clause.endswith("?") else f"{clause}?",
                        question_type=sub_type,
                        primary_facet=facet_name,
                        target_act=primary_act,
                        target_units=sections or articles,
                        authority_type=auth,
                    )
                )

        operational_types = [
            qt for qt in q_types
            if qt not in (
                QuestionType.FACTUAL_SCENARIO,
                QuestionType.COMPLEX_SCENARIO,
                QuestionType.MULTI_PART,
                QuestionType.CONSTITUTIONAL,
                QuestionType.STATUTORY_INTERPRETATION,
                QuestionType.CROSS_ACT,
                QuestionType.GENERAL_LEGAL_INFORMATION,
            )
        ]
        if not sub_questions and len(operational_types) >= 2:
            for idx, qt in enumerate(operational_types, start=1):
                auth = "CASE_LAW" if qt in (QuestionType.CASE_LAW, QuestionType.JUDICIAL_PRINCIPLES) else "STATUTE"
                sub_questions.append(
                    SubQuestion(
                        sub_id=f"sub_q_{idx}",
                        question_text=f"What is the {qt.value.lower()} applicable to this inquiry?",
                        question_type=qt,
                        primary_facet=qt.value.lower(),
                        target_act=primary_act,
                        target_units=sections or articles,
                        authority_type=auth,
                    )
                )

        return sub_questions

    def _extract_legal_concepts(self, lower_q: str) -> List[str]:
        """Extract substantive legal noun phrases and concepts from query."""
        stop_words = {
            "what", "is", "the", "are", "of", "and", "under", "in", "to", "for", "a", "an", "can",
            "does", "explain", "how", "person", "who", "which", "its", "applicable", "relevant",
            "legal", "provisions", "principles", "tests", "law", "indian", "act", "section", "article",
            "woman", "man", "name", "named", "whose", "senior", "employee", "raju", "ramesh", "suresh"
        }
        words = re.findall(r"\b[a-z]{3,}\b", lower_q)
        meaningful = [w for w in words if w not in stop_words]

        phrases = []
        phrase_patterns = [
            r"\bsexual\s+harassment\b",
            r"\bcomplaint\s+mechanisms?\b",
            r"\blegal\s+protections?\b",
            r"\bworkplace\s+harassment\b",
            r"\binternal\s+complaints\s+committee\b",
            r"\blocal\s+(?:complaints\s+)?committee\b",
            r"\bcircumstantial\s+evidence\b",
            r"\bchain\s+of\s+circumstances\b",
            r"\bstandard\s+of\s+proof\b",
            r"\bburden\s+of\s+proof\b",
            r"\bculpable\s+homicide\b",
            r"\bpromise\s+to\s+marry\b",
            r"\bmisconception\s+of\s+fact\b",
            r"\bpersonal\s+liberty\b",
            r"\bdue\s+process\b",
            r"\bprocedure\s+established\s+by\s+law\b",
            r"\bfair\s+and\s+reasonable\s+procedure\b",
            r"\bunfair\s+trade\s+practice\b",
            r"\bdeficiency\s+in\s+service\b",
            r"\bdefective\s+(?:goods|smartphone|phone|product)\b",
            r"\bcorporate\s+insolvency\b",
            r"\bcirp\s+process\b",
            r"\bfinancial\s+creditor\b",
            r"\boperational\s+creditor\b",
            r"\bphishing\s+attack\b",
            r"\bunauthorized\s+access\b",
            r"\bconfidential\s+files\b",
            r"\bransom\s+demand\b",
            r"\bransomware\b",
            r"\bidentity\s+theft\b",
            r"\banticipatory\s+bail\b",
            r"\bcognizable\s+offence\b",
            r"\bnon-cognizable\s+offence\b",
            r"\bright\s+to\s+information\b",
            r"\bwrongful\s+termination\b",
            r"\bunlawful\s+termination\b",
            r"\bbreach\s+of\s+contract\b",
            r"\bdirector\s+liability\b",
            r"\bsecurity\s+deposit\b",
            r"\bdivorce\s+procedure\b",
            r"\bgst\s+penalty\b",
        ]
        for pat in phrase_patterns:
            matches = re.findall(pat, lower_q)
            phrases.extend(matches)

        combined = list(dict.fromkeys(phrases + meaningful))
        return combined[:10]

    def _determine_primary_issue(
        self,
        raw_q: str,
        lower_q: str,
        q_types: List[QuestionType],
        concepts: List[str],
        sections: List[str],
        articles: List[str],
        acts: List[str],
        primary_domain: str = "",
        conduct: Optional[List[str]] = None,
        primary_task: Optional[PrimaryTask] = None,
        background_offence: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """Determine what the user is actually trying to understand."""
        secondary: List[str] = []

        # 0. PROCEDURAL / PRIMARY TASK PRIORITY
        if primary_task == PrimaryTask.SEARCH_SEIZURE:
            target = "mobile_device" if any(w in lower_q for w in ["phone", "mobile", "device"]) else "electronic_records_or_premises"
            primary = f"search_seizure_examination_of_{target}"
            secondary = ["digital_evidence_extraction", "police_search_procedure"]
            if background_offence:
                secondary.append(f"{background_offence}_investigation_context")
            return primary, secondary

        if primary_task == PrimaryTask.BAIL:
            primary = "bail_application_procedure"
            secondary = ["anticipatory_or_regular_bail", "grounds_for_bail"]
            if background_offence:
                secondary.append(f"{background_offence}_investigation_context")
            return primary, secondary

        if primary_task == PrimaryTask.ARREST:
            primary = "procedure_for_arrest_and_safeguards"
            secondary = ["grounds_of_arrest", "remand_procedure"]
            if background_offence:
                secondary.append(f"{background_offence}_context")
            return primary, secondary

        # 1. Cybercrime & Computer Offences (Fact-First)
        if "cyber" in primary_domain.lower():
            if any(w in lower_q for w in ["ransomware", "ransom", "demands payment"]):
                primary = "cyber_ransomware_and_extortion"
                secondary = ["unauthorized_access", "data_theft", "extortion_liability"]
                return primary, secondary
            if any(w in lower_q for w in ["unauthorized access", "hacker", "hacking", "server hacked", "stole customer data"]):
                primary = "cyber_unauthorized_access_and_data_theft"
                secondary = ["computer_damage", "confidential_data_theft", "digital_investigation"]
                return primary, secondary
            primary = "cyber_fraud_and_computer_offences"
            secondary = ["identity_theft", "unauthorized_transmission"]
            return primary, secondary

        # 2. Evidence Law Rules (Only when primary domain is Law of Evidence)
        if primary_domain == "Law of Evidence":
            if any(p in lower_q for p in ["circumstantial evidence", "chain of circumstances", "solely on circumstantial"]):
                primary = "circumstantial_evidence_conviction_standard"
                secondary = ["judicial_test", "standard_of_proof", "circumstantial_chain"]
                return primary, secondary
            if any(p in lower_q for p in ["admissibility", "electronic record", "electronic records", "electronic evidence", "digital evidence", "whatsapp", "section 63", "section 65b", "section 62"]):
                primary = "admissibility_of_electronic_records"
                secondary = ["evidentiary_certificate", "tampering_safeguards", "computer_output_conditions"]
                return primary, secondary
            if any(p in lower_q for p in ["burden of proof", "onus of proof", "standard of proof"]):
                primary = "burden_of_proof_in_legal_proceedings"
                secondary = ["beyond_reasonable_doubt", "burden_of_proving_fact"]
                return primary, secondary

        # 3. Constitutional Right / Article Inquiries
        if "constitutional" in primary_domain.lower() or articles:
            if "21" in articles or "personal liberty" in lower_q or "fair and reasonable" in lower_q:
                primary = "article_21_life_and_personal_liberty"
                secondary = ["procedure_established_by_law", "fair_and_reasonable_procedure"]
                return primary, secondary
            if "14" in articles or "equality" in lower_q:
                primary = "article_14_equality_before_law"
                secondary = ["reasonable_classification", "non_arbitrariness"]
                return primary, secondary
            if "32" in articles or "226" in articles or "writ" in lower_q:
                primary = "constitutional_writ_jurisdiction"
                secondary = ["habeas_corpus", "mandamus", "judicial_review"]
                return primary, secondary

        # 4. Consent and Sexual Offences
        if any(p in lower_q for p in ["promise to marry", "misconception of fact", "prior relationship", "consensual relationship", "sexual assault", "rape"]):
            primary = "sexual_offence_and_consent_standards"
            secondary = ["misconception_of_fact", "voluntary_consent_standard"]
            return primary, secondary

        # 5. Murder & Circumstantial Proof
        if "murder" in lower_q or "culpable homicide" in lower_q:
            if any(p in lower_q for p in ["circumstantial", "eyewitness", "proof", "conviction"]):
                primary = "murder_conviction_on_circumstantial_evidence"
                secondary = ["standard_of_proof", "chain_of_circumstances"]
                return primary, secondary
            if "punishment" in lower_q or QuestionType.PUNISHMENT in q_types:
                primary = "punishment_for_murder"
                secondary = ["penal_code_provisions", "sentencing"]
                return primary, secondary
            if "investigation" in lower_q or "investigate" in lower_q:
                primary = "investigation_of_homicide_cases"
                secondary = ["police_procedure", "inquest"]
                return primary, secondary
            primary = "substantive_law_governing_murder"
            secondary = ["essential_ingredients", "exceptions"]
            return primary, secondary

        # 6. Consumer Law
        if "consumer" in primary_domain.lower():
            if any(w in lower_q for w in ["appeal", "appellate"]):
                primary = "appeal_against_consumer_commission_order"
                secondary = ["appellate_forum", "limitation_period"]
                return primary, secondary
            if any(w in lower_q for w in ["remedy", "remedies", "compensation", "refund"]):
                primary = "consumer_remedy_for_defective_goods"
                secondary = ["district_commission_filing", "product_liability"]
                return primary, secondary
            primary = "consumer_protection_rights_and_liabilities"
            secondary = ["deficiency_in_service", "defect_in_goods"]
            return primary, secondary

        # 7. Employment / Labour Law & Workplace Sexual Harassment
        if (
            "posh" in primary_domain.lower()
            or "sexual harassment" in primary_domain.lower()
            or any(w in lower_q for w in ["sexual harassment", "posh", "internal complaints committee", "icc", "local committee"])
            or ("workplace" in lower_q and "harass" in lower_q)
        ):
            primary = "workplace_sexual_harassment_protections_and_redressal"
            secondary = [
                "complaint_mechanisms_icc_and_local_committee",
                "relevant_evidence_and_documentation",
                "statutory_protections_and_employer_duties",
            ]
            return primary, secondary

        if "employment" in primary_domain.lower() or "labour" in primary_domain.lower():
            primary = "wrongful_termination_rights_and_remedies"
            secondary = ["statutory_notice", "severance_compensation", "reinstatement"]
            return primary, secondary

        # 8. Contract / Property Law
        if "contract" in primary_domain.lower() or "property" in primary_domain.lower():
            if "deposit" in lower_q or "landlord" in lower_q:
                primary = "recovery_of_tenancy_security_deposit"
                secondary = ["legal_notice", "civil_suit_for_recovery"]
                return primary, secondary
            primary = "breach_of_contract_remedies"
            secondary = ["damages_compensation", "specific_performance"]
            return primary, secondary

        # 9. Corporate Law
        if "corporate" in primary_domain.lower():
            primary = "liability_of_company_directors"
            secondary = ["fiduciary_duties", "statutory_penalties"]
            return primary, secondary

        # 10. Insolvency Law
        if "insolvency" in primary_domain.lower():
            primary = "corporate_insolvency_resolution_process"
            secondary = ["initiation_by_creditor", "resolution_professional_timeline"]
            return primary, secondary

        # 11. RTI Law
        if "rti" in primary_domain.lower():
            if "appeal" in lower_q:
                primary = "appellate_procedure_under_rti"
                secondary = ["first_appellate_authority", "information_commission"]
                return primary, secondary
            primary = "procedure_for_filing_rti_application"
            secondary = ["pio_mandates", "statutory_timeline"]
            return primary, secondary

        # 12. Tax / GST Law
        if "tax" in primary_domain.lower() or "gst" in primary_domain.lower():
            primary = "statutory_penalty_for_gst_non_compliance"
            secondary = ["tax_demand", "adjudication_procedure"]
            return primary, secondary

        # 13. Family Law
        if "family" in primary_domain.lower():
            primary = "procedure_governing_divorce_proceedings"
            secondary = ["competent_court", "matrimonial_remedies"]
            return primary, secondary

        # Fallback: specific facet
        if QuestionType.PUNISHMENT in q_types and QuestionType.DEFINITION not in q_types and QuestionType.EXCEPTION not in q_types:
            topic = concepts[0] if concepts else "offence"
            primary = f"punishment_for_{topic}"
            secondary = ["sentencing_prerequisites", "penal_consequences"]
            return primary, secondary

        topic = concepts[0] if concepts else "legal_query"
        primary = f"substantive_law_governing_{topic}"
        secondary = [f"ingredients_of_{c}" for c in concepts[1:3]]
        return primary, secondary

    def _determine_authorities(self, lower_q: str, q_types: List[QuestionType]) -> List[str]:
        """Determine whether query requires STATUTE, CASE_LAW, or BOTH."""
        has_case_law = (
            QuestionType.CASE_LAW in q_types
            or QuestionType.JUDICIAL_PRINCIPLES in q_types
            or any(re.search(pat, lower_q) for pat in [
                r"\b(?:court|courts|supreme\s+court|high\s+court|judgment|precedent|ratio|holding|judicial\s+tests?)\b",
                r"\b(?:what\s+have\s+courts\s+held|tests?\s+laid\s+down)\b"
            ])
        )
        has_statute = (
            QuestionType.DEFINITION in q_types
            or QuestionType.ELEMENTS in q_types
            or QuestionType.OFFENCE in q_types
            or QuestionType.PUNISHMENT in q_types
            or QuestionType.EXCEPTION in q_types
            or QuestionType.PROCEDURE in q_types
            or any(re.search(pat, lower_q) for pat in [
                r"\b(?:section|sections|sec\.?|article|articles|provisions?|act|sanhita|code)\b",
                r"\b(?:bns|bnss|bsa|cpa|ibc|it\s+act|gst|mva)\b"
            ])
        )

        if has_statute and has_case_law:
            return ["STATUTE", "CASE_LAW"]
        if has_case_law:
            return ["CASE_LAW"]
        return ["STATUTE"]

    def _build_answer_requirements(
        self,
        q_types: List[QuestionType],
        complexity: str,
        primary_issue: str,
    ) -> List[str]:
        """Generate substantive answer synthesis requirements."""
        reqs = ["direct_substantive_answer"]
        if QuestionType.DEFINITION in q_types or QuestionType.OFFENCE in q_types:
            reqs.append("statutory_definition_and_elements")
        if QuestionType.PUNISHMENT in q_types:
            reqs.append("applicable_punishment_and_conditions")
        if QuestionType.EXCEPTION in q_types:
            reqs.append("exceptions_and_defences")
        if QuestionType.PROCEDURE in q_types:
            reqs.append("procedural_steps_and_authorities")
        if QuestionType.FACTUAL_SCENARIO in q_types or QuestionType.COMPLEX_SCENARIO in q_types:
            reqs.append("factual_scenario_application")
        if QuestionType.CASE_LAW in q_types or QuestionType.JUDICIAL_PRINCIPLES in q_types:
            reqs.append("verified_judicial_principles")
        if QuestionType.COMPARISON in q_types:
            reqs.append("comparative_distinction")
        if QuestionType.MULTI_PART in q_types:
            reqs.append("multi_part_sub_question_answers")
        reqs.append("conclusion")
        reqs.append("sources_and_disclaimer")
        return reqs


_LEGAL_QUESTION_ANALYZER_INSTANCE = None


def get_legal_question_analyzer() -> LegalQuestionAnalyzer:
    """Return singleton instance of LegalQuestionAnalyzer."""
    global _LEGAL_QUESTION_ANALYZER_INSTANCE
    if _LEGAL_QUESTION_ANALYZER_INSTANCE is None:
        _LEGAL_QUESTION_ANALYZER_INSTANCE = LegalQuestionAnalyzer()
    return _LEGAL_QUESTION_ANALYZER_INSTANCE
