"""
Answer Facet Analyzer for NyayaSetu Legal Assistant.

Inspects user legal questions to identify all requested legal facets (definition,
elements, exceptions, punishment, procedure, rights, time limits, remedies, etc.).
Enforces strict requested vs implied requirement rules, handles multi-part questions,
and generates facet-specific retrieval subqueries.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class QuestionFacet:
    """Represents an individual legal facet requested by the question."""
    name: str
    display_name: str
    query_component: str = ""
    required: bool = True
    implied: bool = False
    retrieval_keywords: List[str] = field(default_factory=list)
    suggested_subquery: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "query_component": self.query_component,
            "required": self.required,
            "implied": self.implied,
            "retrieval_keywords": self.retrieval_keywords,
            "suggested_subquery": self.suggested_subquery,
        }


@dataclass
class FacetAnalysisResult:
    """Complete facet analysis for a legal query."""
    original_query: str
    facets: List[QuestionFacet]
    required_facets: List[str]
    optional_facets: List[str]
    has_multi_aspects: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "facets": [f.to_dict() for f in self.facets],
            "required_facets": self.required_facets,
            "optional_facets": self.optional_facets,
            "has_multi_aspects": self.has_multi_aspects,
        }


# Canonical Legal Facet Registry
LEGAL_FACET_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "definition": {
        "display_name": "Definition",
        "patterns": [
            r"\b(?:define|definition of|meaning of|what constitutes|how is .+ defined)\b",
            r"\b(?:meaning)\b",
            r"\b(?:what is|what are)\s+(?!(?:the\s+)?(?:[a-zA-Z0-9_\-]+\s+){0,3}(?:punishment|penalty|penalties|procedure|exception|exceptions|rights?|time\s+limit|limitation|eligibility|evidence|remedy|remedies|consequence|consequences|requirements?|grounds?)\b)",
        ],
        "keywords": ["definition", "means", "shall mean", "defined", "meaning"],
    },
    "elements": {
        "display_name": "Elements & Ingredients",
        "patterns": [
            r"\b(?:elements|ingredients|essential ingredients|constituent elements|what constitutes)\b",
            r"\b(?:ingredients of|components of)\b",
        ],
        "keywords": ["essential ingredients", "elements", "whoever", "commits", "constitutes"],
    },
    "exceptions": {
        "display_name": "Exceptions & Defences",
        "patterns": [
            r"\b(?:exception|exceptions|when is it not|defence|defences|except in the cases|saving clause|exemptions)\b",
            r"\b(?:unless|except when|cases excepted)\b",
        ],
        "keywords": ["exception", "except", "not amounting to", "private defence", "provocation", "sudden fight"],
    },
    "punishment": {
        "display_name": "Punishment & Sentencing",
        "patterns": [
            r"\b(?:punishment|penalty|punished|sentenced|imprisonment|fine|death penalty|jail|life imprisonment)\b",
            r"\b(?:prescribed for it|what punishment|punishable with)\b",
        ],
        "keywords": ["punishment", "punished with", "imprisonment", "fine", "death", "liable to"],
    },
    "penalty": {
        "display_name": "Penalty",
        "patterns": [
            r"\b(?:penalty|penalties|penal action|financial penalty|pecuniary penalty)\b",
        ],
        "keywords": ["penalty", "liable to a penalty", "fine", "contravention"],
    },
    "procedure": {
        "display_name": "Procedure",
        "patterns": [
            r"\b(?:procedure|how is .+ investigated|how to|process|steps|filing|conduct of inquiry|investigation procedure)\b",
            r"\b(?:how to file|manner of|how does)\b",
        ],
        "keywords": ["procedure", "investigation", "inquiry", "manner", "steps", "police officer", "magistrate"],
    },
    "rights": {
        "display_name": "Rights",
        "patterns": [
            r"\b(?:rights|right to|entitled to|right of person|legal rights|what rights)\b",
            r"\b(?:fundamental right|fundamental rights)\b",
        ],
        "keywords": ["right", "rights", "entitled", "liberty", "equality", "protection"],
    },
    "duties": {
        "display_name": "Duties & Obligations",
        "patterns": [
            r"\b(?:duty|duties|obligations|shall be the duty|responsible for|responsibility)\b",
        ],
        "keywords": ["duty", "obligations", "shall be the duty", "duty of", "responsible"],
    },
    "eligibility": {
        "display_name": "Eligibility & Criteria",
        "patterns": [
            r"\b(?:eligibility|eligible|qualification|qualifications|who can|criteria)\b",
        ],
        "keywords": ["eligible", "eligibility", "qualification", "disqualification", "criteria"],
    },
    "time_limit": {
        "display_name": "Time Limit & Limitation",
        "patterns": [
            r"\b(?:time limit|limitation|limitation period|within what time|period of limitation|timeline|deadline|days to respond)\b",
            r"\b(?:within \d+ days|within thirty days|within forty[- ]five days)\b",
        ],
        "keywords": ["time limit", "within", "days", "period of limitation", "timeline", "months"],
    },
    "grounds": {
        "display_name": "Grounds & Basis",
        "patterns": [
            r"\b(?:grounds?|grounds for|ground of|basis for|on what ground|on what grounds|grounds of divorce|grounds of arrest)\b",
        ],
        "keywords": ["grounds", "ground", "on the ground that", "grounds of", "basis"],
    },
    "jurisdiction": {
        "display_name": "Jurisdiction & Forum",
        "patterns": [
            r"\b(?:jurisdiction|competent court|which court|tribunal|cognizance|forum|territorial jurisdiction)\b",
        ],
        "keywords": ["jurisdiction", "court of session", "magistrate", "high court", "tribunal", "cognizance"],
    },
    "authorities": {
        "display_name": "Authorities & Officers",
        "patterns": [
            r"\b(?:competent authority|who is the authority|which authority|designated authority|powers of authority|public information officer|internal committee|icc)\b",
        ],
        "keywords": ["authority", "officer", "public information officer", "internal committee", "commission"],
    },
    "evidence": {
        "display_name": "Evidence & Admissibility",
        "patterns": [
            r"\b(?:evidence|relevant evidence|evidentiary value|admissibility|admissible|admitted|admit|admitting|proof|burden of proof|prove|proved|electronic record|digital record|certificate)\b",
        ],
        "keywords": ["evidence", "admissible", "admitted", "relevant fact", "burden of proof", "documentary evidence", "testimony", "electronic record", "certificate"],
    },
    "defences": {
        "display_name": "Legal Defences",
        "patterns": [
            r"\b(?:defences|defence|plea|justification|excuse|immunity)\b",
        ],
        "keywords": ["defence", "general exceptions", "good faith", "private defence", "intoxication", "unsound mind"],
    },
    "remedies": {
        "display_name": "Remedies & Relief",
        "patterns": [
            r"\b(?:remedy|remedies|redressal|relief|compensation|damages|what happens if .+ does not respond)\b",
            r"\b(?:what can .+ do|legal remedy)\b",
        ],
        "keywords": ["remedy", "relief", "compensation", "redressal", "complaint", "order"],
    },
    "appeals": {
        "display_name": "Appeals & Revision",
        "patterns": [
            r"\b(?:appeal|appeals|appellate|first appeal|second appeal|revision|review)\b",
        ],
        "keywords": ["appeal", "appellate authority", "appellate tribunal", "revision", "order appealed against"],
    },
    "consequences": {
        "display_name": "Consequences & Default",
        "patterns": [
            r"\b(?:consequences|consequence|what happens if|what happens after|default|failure to|effect of non-compliance)\b",
        ],
        "keywords": ["failure", "default", "consequence", "liable", "penalty", "deemed"],
    },
    "requirements": {
        "display_name": "Requirements & Conditions",
        "patterns": [
            r"\b(?:requirements|requirement|conditions precedent|mandatory requirements|necessary conditions)\b",
        ],
        "keywords": ["requirements", "mandatory", "shall", "required to", "condition"],
    },
    "offences": {
        "display_name": "Offences",
        "patterns": [
            r"\b(?:offence|offences|crime|illegal act|contravention|violation)\b",
        ],
        "keywords": ["offence", "contravention", "violation", "punishable", "cognizable"],
    },
    "exemptions": {
        "display_name": "Exemptions",
        "patterns": [
            r"\b(?:exemption|exemptions|exempted from|not applicable to)\b",
        ],
        "keywords": ["exemption", "exempted", "shall not apply", "nothing in this section"],
    },
    "applicability": {
        "display_name": "Applicability & Scope",
        "patterns": [
            r"\b(?:applicability|applicable to|extent and commencement|scope of the act|who is covered)\b",
        ],
        "keywords": ["applicability", "extends to", "applies to", "commencement", "scope"],
    },
    "registration": {
        "display_name": "Registration & Incorporation",
        "patterns": [
            r"\b(?:registration|register|incorporation|license|licence|registered office)\b",
        ],
        "keywords": ["registration", "register", "certificate of incorporation", "registrar", "license"],
    },
    "reporting_obligations": {
        "display_name": "Reporting Obligations",
        "patterns": [
            r"\b(?:reporting|report to|furnish report|intimation|inform the authority)\b",
        ],
        "keywords": ["report", "reporting", "intimation", "furnish", "submit report"],
    },
    "disclosure_obligations": {
        "display_name": "Disclosure Obligations",
        "patterns": [
            r"\b(?:disclosure|disclose|mandatory disclosure|publish information)\b",
        ],
        "keywords": ["disclosure", "disclose", "publish", "proactive disclosure"],
    },
    "judicial_principles": {
        "display_name": "Judicial Principles",
        "patterns": [
            r"\b(?:judicial\s+principles?|legal\s+principles?|principles\s+governing|principles\s+laid\s+down)\b",
        ],
        "keywords": ["judicial principle", "principles", "laid down by", "principles governing", "jurisprudence"],
    },
    "precedent": {
        "display_name": "Precedents & Judicial Authority",
        "patterns": [
            r"\b(?:precedents?|judicial\s+precedents?|binding\s+precedents?|past\s+rulings?)\b",
        ],
        "keywords": ["precedent", "precedents", "bench", "ratio", "binding"],
    },
    "case_law": {
        "display_name": "Case Law & Judgments",
        "patterns": [
            r"\b(?:case\s+law|caselaw|judgments?|landmark\s+cases?|leading\s+cases?|decisions?\s+of\s+courts?)\b",
        ],
        "keywords": ["case law", "judgment", "ruling", "decision", "court held"],
    },
    "court_interpretation": {
        "display_name": "Court Interpretation",
        "patterns": [
            r"\b(?:court\s+interpretations?|how\s+have\s+courts\s+interpreted|interpretation\s+by\s+courts?|judicial\s+construction)\b",
        ],
        "keywords": ["interpreted by", "court observed", "construction", "interpretation"],
    },
    "judicial_test": {
        "display_name": "Judicial Tests & Standards",
        "patterns": [
            r"\b(?:judicial\s+tests?|legal\s+tests?|two-fold\s+test|three-fold\s+test|dual\s+test|standard\s+applied\s+by\s+courts?)\b",
        ],
        "keywords": ["test", "conditions satisfied", "dual test", "standard"],
    },
    "ratio": {
        "display_name": "Ratio Decidendi",
        "patterns": [
            r"\b(?:ratio|ratio\s+decidendi|proposition\s+of\s+law|rule\s+of\s+law\s+established)\b",
        ],
        "keywords": ["ratio decidendi", "ratio", "proposition of law"],
    },
    "holding": {
        "display_name": "Court Holding & Ruling",
        "patterns": [
            r"\b(?:holding|what\s+have\s+courts\s+held|what\s+has\s+the\s+court\s+held|what\s+did\s+the\s+supreme\s+court\s+hold|courts?\s+held)\b",
        ],
        "keywords": ["held that", "court held", "ruled that", "concluded that"],
    },
    "distinguishing_principle": {
        "display_name": "Distinguishing Principles",
        "patterns": [
            r"\b(?:distinguish|distinguishing|difference\s+between|how\s+to\s+distinguish|distinction\s+between)\b",
        ],
        "keywords": ["distinction between", "distinguished from", "clear distinction", "contrast"],
    },
    "circumstantial_evidence": {
        "display_name": "Circumstantial Evidence",
        "patterns": [
            r"\b(?:circumstantial\s+evidence|circumstances|chain\s+of\s+circumstances|no\s+eyewitness|solely\s+on\s+circumstantial)\b",
        ],
        "keywords": ["circumstantial evidence", "chain of circumstances", "circumstances", "inference of guilt"],
    },
    "standard_of_proof": {
        "display_name": "Standard of Proof & Evidentiary Sufficiency",
        "patterns": [
            r"\b(?:standard\s+of\s+proof|burden\s+of\s+proof|beyond\s+reasonable\s+doubt|conviction\s+based\s+solely|evidentiary\s+sufficiency)\b",
        ],
        "keywords": ["standard of proof", "beyond reasonable doubt", "solely on", "conviction based on", "evidentiary standard"],
    },
}


class AnswerFacetAnalyzer:
    """Analyzes legal queries to extract requested and implied information facets."""

    @staticmethod
    def _split_clauses(text: str) -> List[str]:
        """Split a query into logical clauses around conjunctions."""
        splits = re.split(
            r"\b(?:and\s+what\s+is|and\s+what\s+are|and\s+how|and\s+what|and\s+where|and|as\s+well\s+as|along\s+with|\;|\,)\b",
            text,
            flags=re.IGNORECASE,
        )
        return [s.strip() for s in splits if s.strip()]

    def analyze_facets(self, query: str, detected_entities: Optional[List[str]] = None) -> FacetAnalysisResult:
        """Analyze a legal query to detect all explicitly or implicitly requested legal facets."""
        return self._do_analyze_facets(query, detected_entities)

    analyze = analyze_facets

    def _do_analyze_facets(self, query: str, detected_entities: Optional[List[str]] = None) -> FacetAnalysisResult:
        """Perform legal facet extraction on the user's query.

        Args:
            query: The user question.
            detected_entities: Extracted legal entities/offences from query analysis.

        Returns:
            FacetAnalysisResult with structured QuestionFacet items.
        """
        cleaned_query = query.strip()
        lower_query = cleaned_query.lower()
        clauses = self._split_clauses(cleaned_query)

        detected_facets: Dict[str, QuestionFacet] = {}

        # 1. Match explicit facets from clause patterns
        for facet_name, f_def in LEGAL_FACET_DEFINITIONS.items():
            for clause in clauses:
                clause_lower = clause.lower()
                for pattern in f_def["patterns"]:
                    match = re.search(pattern, clause_lower)
                    if match:
                        if facet_name not in detected_facets:
                            detected_facets[facet_name] = QuestionFacet(
                                name=facet_name,
                                display_name=f_def["display_name"],
                                query_component=clause,
                                required=True,
                                implied=False,
                                retrieval_keywords=f_def["keywords"],
                                suggested_subquery=f"{f_def['display_name']} of {clause}".strip(),
                            )
                        break
                if facet_name in detected_facets:
                    break

        # 2. Implication rules:
        # Rule A: "what constitutes X" implies definition + elements + exceptions
        if re.search(r"\b(?:what constitutes|elements of)\b", lower_query):
            if "definition" not in detected_facets:
                detected_facets["definition"] = QuestionFacet(
                    name="definition",
                    display_name=LEGAL_FACET_DEFINITIONS["definition"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["definition"]["keywords"],
                    suggested_subquery="definition of the offence",
                )
            if "elements" not in detected_facets:
                detected_facets["elements"] = QuestionFacet(
                    name="elements",
                    display_name=LEGAL_FACET_DEFINITIONS["elements"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["elements"]["keywords"],
                    suggested_subquery="elements and ingredients",
                )
            if "exceptions" not in detected_facets and any(w in lower_query for w in ["murder", "culpable homicide", "theft", "defamation"]):
                detected_facets["exceptions"] = QuestionFacet(
                    name="exceptions",
                    display_name=LEGAL_FACET_DEFINITIONS["exceptions"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["exceptions"]["keywords"],
                    suggested_subquery="exceptions and defences",
                )

        # Rule B: "what is [offence]" implies definition + elements
        if "definition" in detected_facets and "elements" not in detected_facets:
            is_offence_or_concept = (
                bool(detected_entities)
                or any(w in lower_query for w in [
                    "murder", "theft", "rape", "cheating", "assault", "offence", "crime",
                    "robbery", "kidnapping", "defamation", "culpable homicide", "extortion",
                    "fir", "arrest", "bail", "electronic record"
                ])
            )
            if is_offence_or_concept:
                detected_facets["elements"] = QuestionFacet(
                    name="elements",
                    display_name=LEGAL_FACET_DEFINITIONS["elements"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["elements"]["keywords"],
                    suggested_subquery="essential ingredients and elements",
                )

        # Rule C: "arrest" questions with rights also involve arrest procedure
        if "rights" in detected_facets and any(w in lower_query for w in ["arrest", "arrested", "custody"]):
            if "procedure" not in detected_facets:
                detected_facets["procedure"] = QuestionFacet(
                    name="procedure",
                    display_name=LEGAL_FACET_DEFINITIONS["procedure"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["procedure"]["keywords"],
                    suggested_subquery="procedure for arrest and duties of officer",
                )

        # Rule D: "what happens if authority does not respond" implies remedies / consequences
        if any(w in lower_query for w in ["what happens if", "does not respond", "fails to respond", "non-compliance"]):
            if "remedies" not in detected_facets:
                detected_facets["remedies"] = QuestionFacet(
                    name="remedies",
                    display_name=LEGAL_FACET_DEFINITIONS["remedies"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["remedies"]["keywords"],
                    suggested_subquery="remedies, appeals, and consequences of non-response",
                )
            if "consequences" not in detected_facets:
                detected_facets["consequences"] = QuestionFacet(
                    name="consequences",
                    display_name=LEGAL_FACET_DEFINITIONS["consequences"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["consequences"]["keywords"],
                    suggested_subquery="deemed refusal, penalties and default consequences",
                )

        # Rule E: Penalty vs Punishment normalization
        if "penalty" in detected_facets and "punishment" not in detected_facets:
            # If query explicitly says "penalties", keep both or map penalty to punishment
            if any(w in lower_query for w in ["punishment", "imprisonment", "jail"]):
                detected_facets["punishment"] = QuestionFacet(
                    name="punishment",
                    display_name=LEGAL_FACET_DEFINITIONS["punishment"]["display_name"],
                    query_component=cleaned_query,
                    required=True,
                    implied=True,
                    retrieval_keywords=LEGAL_FACET_DEFINITIONS["punishment"]["keywords"],
                    suggested_subquery="punishment prescribed",
                )

        # Fallback if no specific facet detected
        if not detected_facets:
            detected_facets["definition"] = QuestionFacet(
                name="definition",
                display_name="General Statutory Rule",
                query_component=cleaned_query,
                required=True,
                implied=True,
                retrieval_keywords=["statutory rule", "provision", "section"],
                suggested_subquery=cleaned_query,
            )

        facet_list = list(detected_facets.values())
        req_list = [f.name for f in facet_list if f.required]
        opt_list = [f.name for f in facet_list if not f.required]

        return FacetAnalysisResult(
            original_query=query,
            facets=facet_list,
            required_facets=req_list,
            optional_facets=opt_list,
            has_multi_aspects=len(req_list) > 1,
        )


_FACET_ANALYZER_INSTANCE = None


def get_answer_facet_analyzer() -> AnswerFacetAnalyzer:
    """Return singleton instance of AnswerFacetAnalyzer."""
    global _FACET_ANALYZER_INSTANCE
    if _FACET_ANALYZER_INSTANCE is None:
        _FACET_ANALYZER_INSTANCE = AnswerFacetAnalyzer()
    return _FACET_ANALYZER_INSTANCE
