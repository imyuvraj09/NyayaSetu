"""
Generation and answer quality evaluator for NyayaSetu Assistant.

Assesses generated answers for structural grounding, non-emptiness, citation validity,
prompt leakage absence, source metadata integrity, and disclaimer compliance.
"""

from typing import Any, Dict, Optional

from evaluation.schemas import GenerationEvaluationItem
from evaluation.validators.citation_validator import CitationValidator
from evaluation.validators.source_validator import SourceValidator
from rag.rag_pipeline import LegalRAGPipeline
from utils.logger import get_logger

logger = get_logger(__name__)


class GenerationEvaluator:
    """Evaluates answer generation and safety compliance."""

    def __init__(
        self,
        pipeline: Optional[LegalRAGPipeline] = None,
        citation_validator: Optional[CitationValidator] = None,
        source_validator: Optional[SourceValidator] = None,
    ) -> None:
        self.pipeline = pipeline or LegalRAGPipeline()
        self.citation_validator = citation_validator or CitationValidator()
        self.source_validator = source_validator or SourceValidator()

    def evaluate_query(
        self,
        query_item: Dict[str, Any],
    ) -> GenerationEvaluationItem:
        """Run generation on a query and validate the response structure.

        Args:
            query_item: Dictionary containing 'id' and 'question'.

        Returns:
            GenerationEvaluationItem containing validation status and warnings.
        """
        qid = query_item["id"]
        qtext = query_item["question"]

        response = self.pipeline.query(qtext)

        # 1. Source integrity validation
        source_report = self.source_validator.validate_sources(response.sources)

        # 2. Citation validation
        citation_report = self.citation_validator.validate(response.answer, response.sources)

        all_warnings = list(dict.fromkeys(response.warnings + citation_report.warnings + source_report.warnings))

        return GenerationEvaluationItem(
            query_id=qid,
            query=qtext,
            answer_length=len(response.answer),
            sources_returned_count=len(response.sources),
            citation_validation_passed=citation_report.is_valid,
            valid_citations=citation_report.valid_citations,
            invalid_citations=citation_report.invalid_citations,
            source_integrity_passed=source_report.is_valid,
            warnings=all_warnings,
            status=response.status,
        )
