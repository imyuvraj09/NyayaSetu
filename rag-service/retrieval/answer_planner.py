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
    primary_issue: str = ""
    offence: Optional[str] = None
    facets: List[str] = field(default_factory=list)
    authority_required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        display_issue = self.primary_issue.replace("_", " ") if self.primary_issue else ""
        return {
            "query": self.query,
            "primary_issue": display_issue,
            "offence": self.offence,
            "facets": self.facets,
            "authority_required": self.authority_required,
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
        primary_issue = getattr(query_analysis, "primary_issue", "") or ""
        offence = getattr(query_analysis, "offence", None)

        sections: List[AnswerSectionPlan] = []
        planned_facets: List[str] = []
        authority_required: List[str] = []

        if primary_issue == "circumstantial_evidence":
            # Specialized structure for circumstantial evidence questions
            planned_facets = [
                "circumstantial_evidence",
                "judicial_test",
                "standard_of_proof",
                "application",
            ]
            authority_required = ["CASE_LAW"]

            sections.append(
                AnswerSectionPlan(
                    facet="answer",
                    display_title="Answer",
                    required=True,
                    evidence_types=["CASE_LAW", "STATUTE"],
                    description="Direct answer stating whether murder conviction can be based solely on circumstantial evidence.",
                )
            )
            sections.append(
                AnswerSectionPlan(
                    facet="legal_principles",
                    display_title="Relevant Legal Principles",
                    required=True,
                    evidence_types=["STATUTE", "CASE_LAW"],
                    description="Substantive criminal provisions defining murder and foundational principles of evidence.",
                )
            )
            sections.append(
                AnswerSectionPlan(
                    facet="judicial_principles",
                    display_title="Judicial Principles",
                    required=True,
                    evidence_types=["CASE_LAW"],
                    description="Judicial tests and precedents including the five golden principles (Panchsheel) governing circumstantial evidence.",
                )
            )
            sections.append(
                AnswerSectionPlan(
                    facet="application",
                    display_title="Application",
                    required=True,
                    evidence_types=["CASE_LAW"],
                    description="Evaluation of specific factual circumstances (motive, CCTV, call records, forensic evidence) against judicial tests.",
                )
            )
            sections.append(
                AnswerSectionPlan(
                    facet="conclusion",
                    display_title="Conclusion",
                    required=True,
                    evidence_types=["CASE_LAW"],
                    description="Final summary of the evidentiary threshold required to sustain conviction.",
                )
            )

            return AnswerPlan(
                query=query_analysis.original_query,
                authority_requirement=auth_req,
                sections=sections,
                requires_statute=False,
                requires_case_law=True,
                primary_issue=primary_issue,
                offence=offence,
                facets=planned_facets,
                authority_required=authority_required,
            )

        # Standard General Planning
        # 1. Direct Legal Rule / Answer
        sections.append(
            AnswerSectionPlan(
                facet="legal_rule",
                display_title="Answer",
                required=True,
                evidence_types=["STATUTE", "CASE_LAW"] if auth_req == AuthorityRequirement.BOTH else [auth_req.value],
                description="Direct, authoritative summary answering the core legal question.",
            )
        )
        planned_facets.append("legal_rule")

        # 2. Statutory Provisions (included if STATUTE or BOTH, or if punishment asked)
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
            planned_facets.append("statutory_provisions")

        # 3. Judicial Principles (included if CASE_LAW or BOTH or if judicial facets requested)
        judicial_facets = {"judicial_principles", "precedent", "case_law", "court_interpretation", "judicial_test", "ratio", "holding"}
        has_judicial_req = (auth_req in (AuthorityRequirement.CASE_LAW, AuthorityRequirement.BOTH)) or bool(req_facets_set & judicial_facets)

        if has_judicial_req:
            sections.append(
                AnswerSectionPlan(
                    facet="judicial_principles",
                    display_title="Judicial Principles",
                    required=True,
                    evidence_types=["CASE_LAW"],
                    description="Verified judicial precedents, holdings, and legal tests established by Indian courts.",
                )
            )
            planned_facets.append("judicial_principles")

        # 4. Legal Application / Practical Context
        sections.append(
            AnswerSectionPlan(
                facet="application",
                display_title="Application",
                required=True,
                evidence_types=["STATUTE", "CASE_LAW"] if auth_req == AuthorityRequirement.BOTH else [auth_req.value],
                description="Synthesizing rules and principles to state clearly how the law applies.",
            )
        )
        planned_facets.append("application")

        if auth_req == AuthorityRequirement.CASE_LAW:
            authority_required = ["CASE_LAW"]
        elif auth_req == AuthorityRequirement.STATUTE:
            authority_required = ["STATUTE"]
        else:
            authority_required = ["STATUTE", "CASE_LAW"]

        plan = AnswerPlan(
            query=query_analysis.original_query,
            authority_requirement=auth_req,
            sections=sections,
            requires_statute=auth_req in (AuthorityRequirement.STATUTE, AuthorityRequirement.BOTH),
            requires_case_law=has_judicial_req,
            primary_issue=primary_issue,
            offence=offence,
            facets=planned_facets,
            authority_required=authority_required,
        )

        logger.info(
            "Constructed AnswerPlan: primary_issue=%s, offence=%s, authority=%s, sections=%d",
            plan.primary_issue,
            plan.offence,
            plan.authority_required,
            len(plan.sections),
        )
        return plan
