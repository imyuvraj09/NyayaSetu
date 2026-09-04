"""
Answer Planner for NyayaSetu Legal Assistant.

Translates user question intent, authority requirements, and requested facets
into a structured AnswerPlan specifying:
- Required sections and facets
- Required evidence types (STATUTE, CASE_LAW, or BOTH) per section
- Evidence sufficiency criteria
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from retrieval.query_analyzer import AuthorityRequirement, LegalQueryAnalysis
from schemas.case_law import EvidenceType
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnswerSectionPlan:
    """Specification for an individual section of the synthesized answer."""
    facet: str
    display_title: str
    required: bool
    evidence_types: List[str]  # ["STATUTE"], ["CASE_LAW"], or ["STATUTE", "CASE_LAW"]
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet": self.facet,
            "display_title": self.display_title,
            "required": self.required,
            "evidence_types": self.evidence_types,
            "description": self.description,
        }


@dataclass
class AnswerPlan:
    """Comprehensive plan governing retrieval and generation for a legal question."""
    query: str
    authority_requirement: AuthorityRequirement
    sections: List[AnswerSectionPlan]
    requires_statute: bool
    requires_case_law: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "authority_requirement": self.authority_requirement.value,
            "sections": [s.to_dict() for s in self.sections],
            "requires_statute": self.requires_statute,
            "requires_case_law": self.requires_case_law,
        }


class AnswerPlanner:
    """Plans structured answers based on query analysis and requested facets."""

    def plan_answer(
        self,
        query_analysis: LegalQueryAnalysis,
        requested_facets: List[str],
    ) -> AnswerPlan:
        """Create a structured answer plan for the user's inquiry."""
        auth_req = query_analysis.authority_requirement
        req_facets_set = set(requested_facets)

        sections: List[AnswerSectionPlan] = []

        # 1. Direct Legal Rule / Answer
        sections.append(
            AnswerSectionPlan(
                facet="legal_rule",
                display_title="Direct Legal Answer",
                required=True,
                evidence_types=["STATUTE", "CASE_LAW"] if auth_req == AuthorityRequirement.BOTH else [auth_req.value],
                description="Direct, authoritative summary answering the core legal question.",
            )
        )

        # 2. Statutory Provisions (included if STATUTE or BOTH)
        if auth_req in (AuthorityRequirement.STATUTE, AuthorityRequirement.BOTH):
            sections.append(
                AnswerSectionPlan(
                    facet="statutory_provisions",
                    display_title="Relevant Legal Provisions",
                    required=True,
                    evidence_types=["STATUTE"],
                    description="Statutory definitions, essential ingredients, sections, and prescribed penalties.",
                )
            )

        # 3. Judicial Principles (included if CASE_LAW or BOTH or if judicial facets requested)
        judicial_facets = {"judicial_principles", "precedent", "case_law", "court_interpretation", "judicial_test", "ratio", "holding"}
        has_judicial_req = (auth_req in (AuthorityRequirement.CASE_LAW, AuthorityRequirement.BOTH)) or bool(req_facets_set & judicial_facets)

        if has_judicial_req:
            sections.append(
                AnswerSectionPlan(
                    facet="judicial_principles",
                    display_title="Judicial Principles & Precedents",
                    required=True,
                    evidence_types=["CASE_LAW"],
                    description="Verified judicial precedents, holdings, and legal tests established by Indian courts.",
                )
            )

        # 4. Legal Application / Practical Context
        sections.append(
            AnswerSectionPlan(
                facet="application",
                display_title="Legal Application & Distinction",
                required=True,
                evidence_types=["STATUTE", "CASE_LAW"] if auth_req == AuthorityRequirement.BOTH else [auth_req.value],
                description="Synthesizing rules and principles to state clearly how the law applies.",
            )
        )

        plan = AnswerPlan(
            query=query_analysis.original_query,
            authority_requirement=auth_req,
            sections=sections,
            requires_statute=auth_req in (AuthorityRequirement.STATUTE, AuthorityRequirement.BOTH),
            requires_case_law=has_judicial_req,
        )

        logger.info(
            "Constructed AnswerPlan: authority=%s, requires_statute=%s, requires_case_law=%s, sections=%d",
            plan.authority_requirement.value,
            plan.requires_statute,
            plan.requires_case_law,
            len(plan.sections),
        )
        return plan
