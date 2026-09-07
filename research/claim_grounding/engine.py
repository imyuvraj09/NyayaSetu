"""Unified facade engine orchestrating Phase 5 Answer Claim Grounding & Citation Verification.

Connects atomic claim extraction, classification, evidence matching, entailment verification,
citation auditing, grounding scoring, and risk-aware answer qualification.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from research.claim_grounding.answer_validator import AnswerValidator
from research.claim_grounding.citation_verifier import CitationVerifier
from research.claim_grounding.claim_classifier import ClaimClassifier
from research.claim_grounding.claim_extractor import ClaimExtractor
from research.claim_grounding.entailment_checker import EntailmentChecker
from research.claim_grounding.evidence_matcher import EvidenceMatcher
from research.claim_grounding.grounding_scorer import GroundingScorer
from research.claim_grounding.models import (
    AnswerGroundingResult,
    ClaimGroundingDecision,
    ClaimStatus,
    GenerationMetadata,
    RiskLevel,
)


class ClaimGroundingEngine:
    """Orchestrates end-to-end atomic claim grounding, citation auditing, and answer validation."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config = self._load_config(config_path)

        # Initialize modular subcomponents
        self.extractor = ClaimExtractor()
        weights_config = self.config.get("claim_importance_weights", {})
        self.classifier = ClaimClassifier(custom_weights=weights_config)
        self.matcher = EvidenceMatcher(
            min_match_threshold=self.config.get("min_match_threshold", 0.20)
        )
        self.entailment_checker = EntailmentChecker(
            full_support_threshold=self.config.get("full_support_threshold", 0.65),
            partial_support_threshold=self.config.get("partial_support_threshold", 0.35),
        )
        self.citation_verifier = CitationVerifier(
            citation_match_threshold=self.config.get("citation_match_threshold", 0.30)
        )
        self.scorer = GroundingScorer()
        self.validator = AnswerValidator(
            excise_high_risk_unsupported=self.config.get("excise_high_risk_unsupported", False),
            qualify_unsupported_claims=self.config.get("qualify_unsupported_claims", True),
        )

    def verify_and_qualify_answer(
        self,
        answer: str,
        evidence_chunks: List[Any],
        generation_metadata: Optional[GenerationMetadata] = None,
        ablation_mode: Optional[str] = None,
    ) -> AnswerGroundingResult:
        """Run claim-level grounding and citation verification on generated answer.

        Ablation modes:
        - 'citation_presence' (Phase 5A): Check citation presence only
        - 'citation_verification' (Phase 5B): Citation verification only
        - 'claim_evidence' (Phase 5C): Claim-evidence entailment without citation audit
        - 'full' (Phase 5D): Full pipeline
        """
        t_start = time.perf_counter()
        gen_meta = generation_metadata or GenerationMetadata()
        mode = ablation_mode or self.config.get("ablation_mode", "full")

        if not answer or not answer.strip():
            return AnswerGroundingResult(
                original_answer=answer,
                validated_answer=answer,
                claims=[],
                decisions=[],
                grounding_score=1.0,
                high_risk_error_count=0,
                unsupported_claim_count=0,
                contradicted_claim_count=0,
                citation_accuracy=1.0,
                citation_completeness=1.0,
                generation_metadata=gen_meta,
                latency_ms=0.0,
                modifications_made=False,
            )

        # Stage 1: Atomic Claim Extraction
        raw_claims = self.extractor.extract_claims(answer)

        # Stage 2: Claim Classification & Risk Weighting
        classified_claims = self.classifier.classify_claims(raw_claims)

        decisions: List[ClaimGroundingDecision] = []

        for claim in classified_claims:
            # Stage 3: Claim-to-Evidence Matching
            if mode in ["citation_presence"]:
                # Baseline 5A: only check if citations exist
                has_cit = bool(claim.attached_citations)
                status = ClaimStatus.SUPPORTED if has_cit else ClaimStatus.UNSUPPORTED
                score = 1.0 if has_cit else 0.0
                best_match = None
                reasoning = "Citation presence baseline: evaluated solely on presence of attached citation."
                citation_results = []
            elif mode in ["citation_verification"]:
                # 5B: Citation verification only
                matches = self.matcher.match_claim_to_evidence(claim, evidence_chunks)
                best_match = matches[0] if matches else None
                cit_res = self.citation_verifier.verify_citations(claim, evidence_chunks, matches, ClaimStatus.SUPPORTED)
                has_valid = any(c.status.value == "VALID_CITATION" for c in cit_res)
                status = ClaimStatus.SUPPORTED if has_valid else ClaimStatus.UNSUPPORTED
                score = 1.0 if has_valid else 0.0
                reasoning = "Citation verification: evaluated on statutory reference validity."
                citation_results = cit_res
            elif mode in ["claim_evidence"]:
                # 5C: Claim entailment without citation auditing
                matches = self.matcher.match_claim_to_evidence(claim, evidence_chunks)
                status, score, best_match, reasoning = self.entailment_checker.evaluate_support(claim, matches)
                citation_results = []
            else:
                # 5D: Full pipeline
                matches = self.matcher.match_claim_to_evidence(claim, evidence_chunks)
                status, score, best_match, reasoning = self.entailment_checker.evaluate_support(claim, matches)
                cit_res = self.citation_verifier.verify_citations(claim, evidence_chunks, matches, status)
                citation_results = cit_res

            decision = ClaimGroundingDecision(
                claim=claim,
                status=status,
                support_score=score,
                best_evidence_match=best_match,
                citation_results=citation_results,
                reasoning=reasoning,
            )
            decisions.append(decision)

        # Stage 4: Grounding Score and Citation Metrics
        grounding_score, _ = self.scorer.calculate_grounding_score(decisions)
        cit_acc, cit_comp = self.scorer.compute_citation_metrics(decisions)

        # Stage 5: Risk-Aware Answer Validation / Qualification
        if mode in ["full"]:
            validated_answer, mods_made = self.validator.validate_and_qualify(answer, decisions)
        else:
            validated_answer, mods_made = answer, False

        # Diagnostic Counts
        high_risk_errors = sum(
            1 for d in decisions
            if d.claim.risk_level == RiskLevel.HIGH and d.status in [ClaimStatus.UNSUPPORTED, ClaimStatus.CONTRADICTED]
        )
        unsupported_count = sum(1 for d in decisions if d.status == ClaimStatus.UNSUPPORTED)
        contradicted_count = sum(1 for d in decisions if d.status == ClaimStatus.CONTRADICTED)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return AnswerGroundingResult(
            original_answer=answer,
            validated_answer=validated_answer,
            claims=classified_claims,
            decisions=decisions,
            grounding_score=grounding_score,
            high_risk_error_count=high_risk_errors,
            unsupported_claim_count=unsupported_count,
            contradicted_claim_count=contradicted_count,
            citation_accuracy=cit_acc,
            citation_completeness=cit_comp,
            generation_metadata=gen_meta,
            latency_ms=round(elapsed_ms, 3),
            modifications_made=mods_made,
        )

    def _load_config(self, config_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
        """Load YAML configuration or return production defaults."""
        default_config = {
            "enable_claim_extraction": True,
            "enable_claim_classification": True,
            "enable_evidence_matching": True,
            "enable_entailment_checking": True,
            "enable_citation_verification": True,
            "enable_answer_validation": True,
            "min_match_threshold": 0.20,
            "full_support_threshold": 0.65,
            "partial_support_threshold": 0.35,
            "citation_match_threshold": 0.30,
            "excise_high_risk_unsupported": False,
            "qualify_unsupported_claims": True,
            "ablation_mode": "full",
        }
        if config_path:
            p = Path(config_path)
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            default_config.update(data)
                except Exception:
                    pass
        return default_config


_ENGINE_INSTANCE: Optional[ClaimGroundingEngine] = None


def get_claim_grounding_engine(config_path: Optional[Union[str, Path]] = None) -> ClaimGroundingEngine:
    """Singleton getter for the ClaimGroundingEngine."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        if config_path is None:
            # Default to standard config if present
            default_p = Path("configs/claim_grounding_config.yaml")
            config_path = default_p if default_p.exists() else None
        _ENGINE_INSTANCE = ClaimGroundingEngine(config_path=config_path)
    return _ENGINE_INSTANCE
