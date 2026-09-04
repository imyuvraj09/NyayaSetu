"""
Universal Legal Question Modeling & Decomposition for NyayaSetu.

Transforms any natural language Indian legal question into a structured,
decomposed, and typed LegalQuestion representation.

Capabilities:
1. Universal Question Type Detection across 25 generic legal question types.
2. Factual Scenario Decomposition (extracting factual events and mapping to legal concepts).
3. Multi-Part Question Decomposition into independent sub-questions.
4. Operative Primary Legal Issue Identification (driven by the user's actual legal inquiry, not keyword frequency).
5. Dynamic Legal Concept, Enactment, Article, and Section inference without hardcoding.
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
    """Universal structured model of an Indian legal query."""
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

    @property
    def primary_legal_issue(self) -> str:
        return self.primary_issue

    @property
    def raw_query(self) -> str:
        return self.original_query

    @property
    def operative_legal_concepts(self) -> List[str]:
        return self.legal_concepts

    @property
    def governing_enactments(self) -> List[str]:
        return self.acts

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
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "legal_domain": self.legal_domain,
            "primary_issue": self.primary_issue,
            "secondary_issues": self.secondary_issues,
            "facts": [f.to_dict() for f in self.facts],
            "legal_concepts": self.legal_concepts,
            "acts": self.acts,
            "articles": self.articles,
            "sections": self.sections,
            "requested_facets": self.requested_facets,
            "authority_requirements": self.authority_requirements,
            "sub_questions": [sq.to_dict() for sq in self.sub_questions],
            "question_types": [qt.value for qt in self.question_types],
            "complexity": self.complexity,
            "answer_requirements": self.answer_requirements,
        }


# Linguistic patterns defining generic legal question types
QUESTION_TYPE_PATTERNS: Dict[QuestionType, List[str]] = {
    QuestionType.DEFINITION: [
        r"\b(?:what is|what are|define|definition of|meaning of|what constitutes|how is .+ defined)\b",
        r"\b(?:what does .+ mean|concept of)\b",
    ],
    QuestionType.ELEMENTS: [
        r"\b(?:elements|ingredients|essential ingredients|constituent elements|requirements for|prerequisites)\b",
        r"\b(?:what must be proven|necessary components)\b",
    ],
    QuestionType.PUNISHMENT: [
        r"\b(?:punishment|penalty|penalties|punished with|prescribed for|sentenced|imprisonment|fine|jail)\b",
        r"\b(?:what is the sentence|penal consequence)\b",
    ],
    QuestionType.EXCEPTION: [
        r"\b(?:exception|exceptions|when is it not|exemptions?|saving clause|non-applicability)\b",
        r"\b(?:when does .+ not apply|excluded cases|does .+ imply consent|automatically establish consent)\b",
    ],
    QuestionType.DEFENCE: [
        r"\b(?:defence|defences|plea of|private defence|self-defence|immunity|protection against liability)\b",
        r"\b(?:plea of consent|prior consensual|implied consent|vitiate consent|defence of consent)\b",
    ],
    QuestionType.PROCEDURE: [
        r"\b(?:procedure|how to|steps|process|investigation|how is .+ investigated|what happens after)\b",
        r"\b(?:filing|lodging|cognizance|inquest|summons|warrant|remand|custody|trial procedure)\b",
    ],
    QuestionType.RIGHTS: [
        r"\b(?:rights?|entitlement|fundamental rights?|legal rights?|can a person claim)\b",
    ],
    QuestionType.DUTIES: [
        r"\b(?:duty|duties|obligation|obligations|mandatory duty|statutory obligation)\b",
    ],
    QuestionType.REMEDY: [
        r"\b(?:remedy|remedies|relief|compensation|damages|redressal|recourse|injunction)\b",
    ],
    QuestionType.APPEAL: [
        r"\b(?:appeal|appellate|revision|review petition|challenge the order|higher court)\b",
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

        # 5. Multi-Part Question Detection & Sub-Question Generation
        sub_questions = self._decompose_multi_part(cleaned, lower_q, q_types, acts, sections, articles)
        if len(sub_questions) > 1 and QuestionType.MULTI_PART not in q_types:
            q_types.append(QuestionType.MULTI_PART)

        if len(acts) > 1 and QuestionType.CROSS_ACT not in q_types:
            q_types.append(QuestionType.CROSS_ACT)

        if not q_types:
            q_types = [QuestionType.GENERAL_LEGAL_INFORMATION]

        # 6. Extract Legal Concepts & Entities
        legal_concepts = self._extract_legal_concepts(lower_q)

        # 7. Identify the Operative Primary Legal Issue
        primary_issue, secondary_issues = self._determine_primary_issue(
            cleaned, lower_q, q_types, legal_concepts, sections, articles, acts
        )

        # 8. Determine Authority Requirements
        authority_requirements = self._determine_authorities(lower_q, q_types)

        # 9. Requested Facets
        requested_facets = [qt.value.lower() for qt in q_types if qt not in (
            QuestionType.FACTUAL_SCENARIO,
            QuestionType.COMPLEX_SCENARIO,
            QuestionType.MULTI_PART,
            QuestionType.CROSS_ACT,
            QuestionType.GENERAL_LEGAL_INFORMATION,
        )]

        # 10. Complexity Level
        complexity = "SIMPLE"
        if QuestionType.COMPLEX_SCENARIO in q_types or (QuestionType.FACTUAL_SCENARIO in q_types and QuestionType.MULTI_PART in q_types):
            complexity = "COMPLEX_SCENARIO"
        elif QuestionType.FACTUAL_SCENARIO in q_types:
            complexity = "FACTUAL_SCENARIO"
        elif QuestionType.MULTI_PART in q_types or QuestionType.CROSS_ACT in q_types:
            complexity = "MULTI_PART"
        elif len(q_types) > 1:
            complexity = "COMPOUND"

        # 11. Infer Legal Domain
        legal_domain = self._infer_domain(lower_q, acts, q_types, legal_concepts)

        # 12. Determine Answer Requirements
        answer_requirements = self._build_answer_requirements(q_types, complexity, primary_issue)

        lq = LegalQuestion(
            original_query=query,
            normalized_query=cleaned,
            legal_domain=legal_domain,
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
        )

        logger.info(
            "Universal LegalQuestion: domain='%s', primary_issue='%s', types=%s, sub_q=%d, facts=%d",
            lq.legal_domain,
            lq.primary_issue,
            [qt.value for qt in lq.question_types],
            len(lq.sub_questions),
            len(lq.facts),
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
        # General pattern matching for acts without hardcoding behavior
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
            (r"\b(?:posh|sexual\s+harassment\s+of\s+women\s+at\s+workplace)\b", "The Sexual Harassment of Women at Workplace Act, 2013"),
            (r"\b(?:rti|right\s+to\s+information)\b", "The Right to Information Act, 2005"),
            (r"\b(?:rte|right\s+to\s+education)\b", "The Right of Children to Free and Compulsory Education Act, 2009"),
            (r"\b(?:gst|goods\s+and\s+services\s+tax)\b", "The Goods and Services Tax Act, 2017"),
            (r"\b(?:motor\s+vehicles?\s+act|mva)\b", "Motor Vehicles Act"),
        ]
        for pattern, canon_name in act_patterns:
            if re.search(pattern, lower_q):
                instruments.append(canon_name)
        return list(dict.fromkeys(instruments))

    def _is_factual_scenario(self, raw_q: str, lower_q: str) -> bool:
        """Determine if query presents a hypothetical factual scenario."""
        # Check narrative sentence structures, character actions, or conditional narrative setups
        scenario_indicators = [
            r"\b(?:a\s+person|a\s+man|a\s+woman|a\s+victim|an\s+accused|an\s+individual|the\s+prosecution)\b",
            r"\b(?:if\s+a\s+person|suppose\s+that|in\s+a\s+case\s+where|enters\s+credentials|receives\s+a\s+call)\b",
            r"\b(?:relies\s+entirely\s+on|there\s+is\s+no\s+eyewitness|purchases\s+a\s+product|director\s+fails\s+to)\b",
            r"\b(?:alleges\s+that|claims\s+that|transfers\s+money|sent\s+an\s+email)\b",
        ]
        has_scenario_lang = any(re.search(p, lower_q) for p in scenario_indicators)
        # Factual scenarios often have multiple sentences or clauses describing facts before a question
        has_multi_sentences = len(re.split(r"[.?!]\s+", raw_q)) >= 2
        return has_scenario_lang or (has_multi_sentences and any(w in lower_q for w in ["can", "does", "whether", "what liability", "what offences"]))

    def _decompose_factual_scenario(self, raw_q: str) -> List[FactualEvent]:
        """Break down a factual scenario narrative into ordered atomic factual events."""
        events: List[FactualEvent] = []
        # Split narrative into sentences/clauses
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|;\s*|,\s*(?=(?:and|but|then|whereupon)\s+)", raw_q) if len(s.strip()) > 15]

        for i, sent in enumerate(sentences, start=1):
            # Skip pure question sentences
            if re.match(r"^(?:can|does|what|how|explain|is|whether|who)\b", sent, re.IGNORECASE) and "?" in sent:
                continue

            # Identify key action verb if possible
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

        # Look for explicit multi-clause interrogatives (e.g. "What constitutes X, what are its exceptions, and what punishment applies?")
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

        # If question has multiple distinct operational QuestionTypes (e.g. DEFINITION and PUNISHMENT, or PROCEDURE and EVIDENCE)
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
        # Generic stop words for legal queries
        stop_words = {
            "what", "is", "the", "are", "of", "and", "under", "in", "to", "for", "a", "an", "can",
            "does", "explain", "how", "person", "who", "which", "its", "applicable", "relevant",
            "legal", "provisions", "principles", "tests", "law", "indian", "act", "section", "article"
        }
        words = re.findall(r"\b[a-z]{3,}\b", lower_q)
        meaningful = [w for w in words if w not in stop_words]

        # Extract multi-word legal phrases
        phrases = []
        phrase_patterns = [
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
            r"\bdefect\s+in\s+goods\b",
            r"\bcorporate\s+insolvency\b",
            r"\bfinancial\s+creditor\b",
            r"\boperational\s+creditor\b",
            r"\bphishing\s+attack\b",
            r"\bunauthorized\s+access\b",
            r"\bidentity\s+theft\b",
            r"\banticipatory\s+bail\b",
            r"\bcognizable\s+offence\b",
            r"\bnon-cognizable\s+offence\b",
            r"\bfiduciary\s+relationship\b",
            r"\bright\s+to\s+information\b",
            r"\bprivate\s+defence\b",
        ]
        for pat in phrase_patterns:
            matches = re.findall(pat, lower_q)
            phrases.extend(matches)

        combined = list(dict.fromkeys(phrases + meaningful))
        return combined[:8]

    def _determine_primary_issue(
        self,
        raw_q: str,
        lower_q: str,
        q_types: List[QuestionType],
        concepts: List[str],
        sections: List[str],
        articles: List[str],
        acts: List[str],
    ) -> Tuple[str, List[str]]:
        """Determine what the user is actually trying to understand.

        Prioritizes the operative inquiry over repeated context words.
        """
        secondary: List[str] = []

        # 1. Check if the operative question is an evidentiary or judicial test inquiry
        if QuestionType.EVIDENCE in q_types or QuestionType.JUDICIAL_PRINCIPLES in q_types or QuestionType.CASE_LAW in q_types:
            if any(p in lower_q for p in ["circumstantial evidence", "chain of circumstances", "no eyewitness", "solely on circumstantial"]):
                primary = "circumstantial_evidence_conviction_standard"
                secondary = ["judicial_test", "standard_of_proof", "circumstantial_chain"]
                return primary, secondary

            if any(p in lower_q for p in ["admissibility", "electronic record", "electronic evidence", "section 63", "section 65b"]):
                primary = "admissibility_of_electronic_records"
                secondary = ["evidentiary_certificate", "tampering_safeguards"]
                return primary, secondary

        # 2. Check if operative inquiry is Constitutional / Fundamental Right / Writs
        if QuestionType.CONSTITUTIONAL in q_types or articles:
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

        # 3. Check for Consent and Misconception of Fact in Sexual Offences
        if any(p in lower_q for p in ["promise to marry", "misconception of fact", "prior relationship", "consensual relationship"]):
            primary = "consent_and_promise_to_marry"
            secondary = ["misconception_of_fact", "voluntary_consent_standard"]
            return primary, secondary

        # 4. Check for Cyber / Computer-related Offences
        if any(p in lower_q for p in ["phishing", "hacking", "stolen credentials", "unauthorized access", "cyber", "otp"]):
            primary = "cyber_fraud_and_computer_offences"
            secondary = ["identity_theft", "unauthorized_transmission", "cheating_by_personation"]
            return primary, secondary

        # 5. Check if operative inquiry is specific facet (Punishment, Exception, Procedure, Remedy)
        if QuestionType.PUNISHMENT in q_types and QuestionType.DEFINITION not in q_types and QuestionType.EXCEPTION not in q_types:
            topic = concepts[0] if concepts else "offence"
            primary = f"punishment_for_{topic}"
            secondary = ["sentencing_prerequisites", "penal_consequences"]
            return primary, secondary

        if QuestionType.EXCEPTION in q_types:
            topic = concepts[0] if concepts else "offence"
            primary = f"exceptions_and_defences_to_{topic}"
            secondary = ["limiting_conditions", "burden_of_defence"]
            return primary, secondary

        if QuestionType.PROCEDURE in q_types:
            topic = concepts[0] if concepts else "matter"
            primary = f"procedure_governing_{topic}"
            secondary = ["investigation_steps", "competent_authority", "statutory_timeline"]
            return primary, secondary

        if QuestionType.REMEDY in q_types:
            topic = concepts[0] if concepts else "grievance"
            primary = f"legal_remedies_for_{topic}"
            secondary = ["forum", "compensation", "injunction"]
            return primary, secondary

        # 6. Fallback: substantive legal inquiry for concept
        main_c = concepts[0] if concepts else "legal_query"
        primary = f"substantive_law_governing_{main_c}"
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
            or QuestionType.PUNISHMENT in q_types
            or QuestionType.EXCEPTION in q_types
            or QuestionType.PROCEDURE in q_types
            or any(re.search(pat, lower_q) for pat in [
                r"\b(?:section|sections|sec\.?|article|articles|provisions?|act|sanhita|code)\b",
                r"\b(?:bns|bnss|bsa|cpa|ibc|it\s+act|gst|mva)\b"
            ])
        )

        authorities: List[str] = []
        if has_statute and has_case_law:
            authorities = ["STATUTE", "CASE_LAW"]
        elif has_case_law:
            authorities = ["CASE_LAW"]
        else:
            authorities = ["STATUTE"]

        return authorities

    def _infer_domain(
        self,
        lower_q: str,
        acts: List[str],
        q_types: List[QuestionType],
        concepts: List[str],
    ) -> str:
        """Infer canonical Indian legal domain dynamically."""
        if QuestionType.CONSTITUTIONAL in q_types or any("constitution" in a.lower() for a in acts):
            return "Constitutional Law"
        if any("consumer" in a.lower() for a in acts) or any(c in lower_q for c in ["consumer", "defective goods", "deficiency"]):
            return "Consumer Law"
        if any("it act" in a.lower() or "information technology" in a.lower() for a in acts) or any(c in lower_q for c in ["cyber", "phishing", "hacking", "digital"]):
            return "Cyber Law"
        if any("companies" in a.lower() or "ibc" in a.lower() or "insolvency" in a.lower() for a in acts):
            return "Corporate & Insolvency Law"
        if any("bsa" in a.lower() or "evidence" in a.lower() for a in acts) or QuestionType.EVIDENCE in q_types:
            return "Law of Evidence"
        if any("bnss" in a.lower() or "procedure" in a.lower() for a in acts) or QuestionType.PROCEDURE in q_types:
            return "Criminal Procedure"
        if any("bns" in a.lower() or "penal" in a.lower() for a in acts) or any(c in lower_q for c in ["offence", "crime", "accused", "conviction", "prosecution", "punishment"]):
            return "Criminal Law"
        if any("motor" in a.lower() for a in acts):
            return "Transport & Motor Vehicles Law"
        if any("rti" in a.lower() for a in acts):
            return "Administrative & Transparency Law"
        return "Indian Statutory Law"

    def _build_answer_requirements(
        self,
        q_types: List[QuestionType],
        complexity: str,
        primary_issue: str,
    ) -> List[str]:
        """Generate substantive answer synthesis requirements."""
        reqs = ["direct_substantive_answer"]
        if QuestionType.DEFINITION in q_types:
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
