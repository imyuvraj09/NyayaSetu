"""
Answer Facet Validator for NyayaSetu Legal Assistant.

Inspects generated legal responses (main answer and legal basis) against requested facets
and performs deep claim-to-evidence validation.

Verifies that every required facet is:
1. Grounded using retrieved statutory provisions,
2. Backed by valid claims with semantic text support,
3. Citing the exact supporting source, AND
4. NOT dismissed as 'unavailable' when official statutory evidence was retrieved.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from retrieval.answer_facet_analyzer import (
    LEGAL_FACET_DEFINITIONS,
    FacetAnalysisResult,
    QuestionFacet,
)
from retrieval.claim_evidence_validator import (
    ClaimEvidenceValidator,
    get_claim_evidence_validator,
)
from retrieval.facet_evidence_models import (
    ClaimValidationResult,
    EvidenceStatus,
    FacetEvidence,
    FacetStatus,
    FinalQualityStatus,
)
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FacetValidationDetail:
    """Detailed validation state for a single legal facet."""
    facet_name: str
    display_name: str
    required: bool
    status: FacetStatus = FacetStatus.NOT_REQUESTED
    evidence_found: bool = False
    answer_covered: bool = False
    claims_supported: bool = False
    citations_valid: bool = True
    addressed: bool = False
    evidence_supported: bool = False
    source_sections: List[str] = field(default_factory=list)
    matching_snippets: List[str] = field(default_factory=list)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    acknowledges_limitation: bool = False
    false_negative_detected: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_name": self.facet_name,
            "display_name": self.display_name,
            "required": self.required,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "evidence_found": self.evidence_found,
            "answer_covered": self.answer_covered,
            "claims_supported": self.claims_supported,
            "citations_valid": self.citations_valid,
            "addressed": self.addressed,
            "evidence_supported": self.evidence_supported,
            "source_sections": self.source_sections,
            "matching_snippets": self.matching_snippets[:3],
            "claims": self.claims[:3],
            "acknowledges_limitation": self.acknowledges_limitation,
            "false_negative_detected": self.false_negative_detected,
            "reason": self.reason,
        }


@dataclass
class AnswerFacetValidationResult:
    """Comprehensive post-generation answer facet completeness report."""
    complete: bool
    quality_status: FinalQualityStatus
    coverage: Dict[str, bool]
    facet_statuses: Dict[str, str]
    missing_facets: List[str]
    facet_details: Dict[str, FacetValidationDetail]
    claim_metrics: Dict[str, Any]
    claim_results: List[Dict[str, Any]]
    diagnostic_summary: str

    @property
    def coverage_summary(self) -> Dict[str, bool]:
        return self.coverage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "complete": self.complete,
            "quality_status": self.quality_status.value if isinstance(self.quality_status, Enum) else str(self.quality_status),
            "coverage": self.coverage,
            "coverage_summary": self.coverage,
            "facet_statuses": self.facet_statuses,
            "missing_facets": self.missing_facets,
            "facet_details": {k: v.to_dict() for k, v in self.facet_details.items()},
            "claim_metrics": self.claim_metrics,
            "claim_results": self.claim_results[:10],
            "diagnostic_summary": self.diagnostic_summary,
        }


class AnswerFacetValidator:
    """Validates that a generated legal answer satisfies all requested facets with grounded evidence."""

    def __init__(self, claim_validator: Optional[ClaimEvidenceValidator] = None) -> None:
        self.claim_validator = claim_validator or get_claim_evidence_validator()

    def validate_answer(
        self,
        answer_text: str,
        facet_analysis: Any,
        facet_coverage: Optional[Dict[str, Any]] = None,
        retrieval_facet_coverage: Optional[Dict[str, Any]] = None,
        sources: Optional[List[Any]] = None,
        target_act: Optional[str] = None,
        query_analysis: Optional[Any] = None,
    ) -> AnswerFacetValidationResult:
        """Inspect generated answer text against requested facets and validate substantive legal claims.

        Args:
            answer_text: Full synthesized answer (or JSON string / mainAnswer + legalBasis).
            facet_analysis: The FacetAnalysisResult or dict from the query analyzer.
            facet_coverage: Map from retrieval stage indicating evidence backing.
            retrieval_facet_coverage: Alias for facet_coverage.
            sources: Optional list of SourceReference objects passed in prompt context.
            target_act: Optional primary statute name.
            query_analysis: Optional query analysis containing primary_issue and excluded_topics.

        Returns:
            AnswerFacetValidationResult detailing multi-level status, claim support, and diagnostics.
        """
        retrieval_coverage = facet_coverage if facet_coverage is not None else (retrieval_facet_coverage or {})
        sources_list = sources or []

        # 1. Extract and validate substantive claims from answer text
        extracted_claims = self.claim_validator.extract_claims(answer_text)
        claim_validation_results, claim_metrics = self.claim_validator.validate_claims(
            claims=extracted_claims,
            sources=sources_list,
            facet_coverage=retrieval_coverage,
            target_act=target_act,
            query_analysis=query_analysis,
        )

        claims_by_facet: Dict[str, List[ClaimValidationResult]] = {}
        for cr in claim_validation_results:
            claims_by_facet.setdefault(cr.facet, []).append(cr)

        # 2. Reconstruct facets list from facet_analysis
        facets_list: List[QuestionFacet] = []
        if isinstance(facet_analysis, dict):
            raw_facets = facet_analysis.get("facets", [])
            for rf in raw_facets:
                facets_list.append(
                    QuestionFacet(
                        name=rf.get("name", ""),
                        display_name=rf.get("display_name", rf.get("name", "")),
                        required=rf.get("required", True),
                        retrieval_keywords=rf.get("retrieval_keywords", []),
                    )
                )
        elif hasattr(facet_analysis, "facets"):
            facets_list = facet_analysis.facets

        coverage_map: Dict[str, bool] = {}
        facet_status_map: Dict[str, str] = {}
        missing_facets: List[str] = []
        details_map: Dict[str, FacetValidationDetail] = {}

        has_false_negative = False
        has_unsupported_claim = False

        # 3. Evaluate each facet individually
        for facet in facets_list:
            f_name = facet.name
            display_name = LEGAL_FACET_DEFINITIONS.get(f_name, {}).get("display_name", f_name.title())

            if not facet.required:
                facet_status_map[f_name] = FacetStatus.NOT_REQUESTED.value
                coverage_map[f_name] = True
                continue

            cov_info = retrieval_coverage.get(f_name, {})
            ev_status = cov_info.get("evidence_status", "")
            ev_supported = cov_info.get("supported", False) or (ev_status == EvidenceStatus.FOUND.value)
            src_sections = cov_info.get("source_sections", [])

            # Check claims associated with this facet
            facet_claims = claims_by_facet.get(f_name, [])
            # Also check if general claims support this facet
            if not facet_claims and f_name in ("definition", "elements"):
                facet_claims = [c for c in claim_validation_results if c.facet in ("general", "definition", "elements")]

            # Check for false negative claim on this facet
            facet_false_negative = any(c.is_negative_claim and not c.negative_claim_valid for c in facet_claims)
            if facet_false_negative:
                has_false_negative = True

            # Check affirmative claim support and citation validity
            affirmative_claims = [c for c in facet_claims if not c.is_negative_claim]
            facet_claims_supported = (
                len(affirmative_claims) > 0 and all(c.supported for c in affirmative_claims)
            )
            facet_citations_valid = (
                all(c.citation_valid for c in affirmative_claims) if affirmative_claims else True
            )

            # Check if answer discusses this facet
            is_discussed = len(affirmative_claims) > 0

            # Determine Multi-Level Facet Status
            if not ev_supported:
                # Evidence was NOT found in corpus
                legit_neg = any(c.is_negative_claim and c.negative_claim_valid for c in facet_claims)
                if legit_neg:
                    f_status = FacetStatus.REQUESTED_BUT_NOT_FOUND
                    is_valid = True
                    reason = "Genuinely unavailable in corpus; properly acknowledged."
                else:
                    f_status = FacetStatus.REQUESTED_BUT_NOT_FOUND
                    is_valid = True
                    reason = "No statutory evidence found in corpus."
            else:
                # Evidence WAS found in corpus
                if facet_false_negative:
                    # Answer falsely claimed evidence was missing!
                    f_status = FacetStatus.ANSWERED_UNSUPPORTED
                    is_valid = False
                    reason = f"False negative claim: Answer claimed '{f_name}' is not in sources, but evidence exists."
                elif not is_discussed:
                    # Evidence existed but LLM didn't answer it
                    f_status = FacetStatus.EVIDENCE_FOUND_NOT_ANSWERED
                    is_valid = False
                    reason = f"Evidence was provided in sources, but answer omitted '{f_name}'."
                elif not facet_claims_supported:
                    # Answer discussed it but claims are unverified or unsupported
                    f_status = FacetStatus.ANSWERED_UNSUPPORTED
                    is_valid = False
                    has_unsupported_claim = True
                    reason = f"Claims made for '{f_name}' are unsupported by retrieved source text."
                elif not facet_citations_valid:
                    # Answer discussed and supported, but cited wrong section
                    f_status = FacetStatus.ANSWERED_SUPPORTED
                    is_valid = False
                    reason = f"Citation mismatch for '{f_name}'."
                else:
                    # Fully answered, supported, and properly cited
                    f_status = FacetStatus.ANSWERED_SUPPORTED_AND_CITED
                    is_valid = True
                    reason = "Substantive claims verified and accurately cited."

            coverage_map[f_name] = is_valid
            facet_status_map[f_name] = f_status.value
            if not is_valid:
                missing_facets.append(f_name)

            details_map[f_name] = FacetValidationDetail(
                facet_name=f_name,
                display_name=display_name,
                required=facet.required,
                status=f_status,
                evidence_found=ev_supported,
                answer_covered=is_discussed,
                claims_supported=facet_claims_supported,
                citations_valid=facet_citations_valid,
                addressed=is_valid,
                evidence_supported=ev_supported,
                source_sections=src_sections,
                matching_snippets=[c.claim for c in affirmative_claims[:2]],
                claims=[c.to_dict() for c in facet_claims],
                acknowledges_limitation=(not ev_supported),
                false_negative_detected=facet_false_negative,
                reason=reason,
            )

        # 4. Final Quality Status Determination
        is_complete = len(missing_facets) == 0 and not has_false_negative

        req_facets = [f for f in facets_list if f.required]
        unfound_facets = [f.name for f in req_facets if details_map.get(f.name) and details_map[f.name].status == FacetStatus.REQUESTED_BUT_NOT_FOUND]

        if has_false_negative or has_unsupported_claim:
            quality_status = FinalQualityStatus.UNSUPPORTED_CLAIM
        elif len(unfound_facets) == len(req_facets) and len(req_facets) > 0:
            # All required facets were genuinely not found in corpus
            quality_status = FinalQualityStatus.INSUFFICIENT_EVIDENCE
        elif len(unfound_facets) > 0:
            quality_status = FinalQualityStatus.PARTIALLY_COMPLETE
        elif is_complete:
            quality_status = FinalQualityStatus.COMPLETE
        else:
            quality_status = FinalQualityStatus.PARTIALLY_COMPLETE

        req_names = [f.name for f in facets_list if f.required]
        summary_lines = [
            f"Facet & Claim Validation {'PASSED' if is_complete else 'FAILED'}:",
            f"Quality Status: {quality_status.value}",
            f"Required: {req_names}",
            f"Statuses: {facet_status_map}",
            f"Missing/Defective: {missing_facets}",
        ]
        diagnostic_str = " | ".join(summary_lines)

        logger.info(
            "Answer validation complete: status=%s, complete=%s, missing=%s, claims_supported=%d/%d",
            quality_status.value,
            is_complete,
            missing_facets,
            claim_metrics.get("supported_claims", 0),
            claim_metrics.get("total_claims", 0),
        )

        return AnswerFacetValidationResult(
            complete=is_complete,
            quality_status=quality_status,
            coverage=coverage_map,
            facet_statuses=facet_status_map,
            missing_facets=missing_facets,
            facet_details=details_map,
            claim_metrics=claim_metrics,
            claim_results=[cr.to_dict() for cr in claim_validation_results],
            diagnostic_summary=diagnostic_str,
        )


_FACET_VALIDATOR_INSTANCE = None


def get_answer_facet_validator() -> AnswerFacetValidator:
    """Return singleton instance of AnswerFacetValidator."""
    global _FACET_VALIDATOR_INSTANCE
    if _FACET_VALIDATOR_INSTANCE is None:
        _FACET_VALIDATOR_INSTANCE = AnswerFacetValidator()
    return _FACET_VALIDATOR_INSTANCE
