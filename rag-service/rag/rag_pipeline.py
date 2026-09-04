"""
End-to-end Legal RAG Pipeline for NyayaSetu Assistant.

Orchestrates:
1. User Query validation
2. Phase 6 Advanced Two-Stage Retrieval (Dense Search -> Filter -> Cross-Encoder Rerank)
3. Structured Context Building ([SOURCE 1] ... [SOURCE K]) with 20000-char limits
4. Grounded Prompt Engineering with mandatory 4-section format
5. LLM Inference via Provider Abstraction (OpenAI Primary)
6. Deterministic Citation and Safety Validation
7. Structured Serialization into RAGResponse
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from llm.base import BaseLLMProvider, LLMError
from llm.provider import get_llm_provider
from prompts.prompts import SYSTEM_INSTRUCTION, build_rag_prompt, build_recovery_prompt
from rag.answer_facet_validator import AnswerFacetValidator
from rag.answer_validator import LegalAnswerValidator
from rag.context_builder import LegalContextBuilder
from rag.deterministic_answer_builder import DeterministicAnswerBuilder
from retrieval.advanced_retriever import AdvancedRetriever
from retrieval.answer_planner import AnswerPlanner
from retrieval.case_law_retriever import CaseLawRetriever
from retrieval.evidence_graph import LegalEvidenceGraph
from retrieval.facet_evidence_models import CaseLawStatus
from retrieval.judicial_principle_extractor import JudicialPrincipleExtractor
from retrieval.topic_compatibility import TopicCompatibilityEngine
from schemas.generation import RAGResponse, SourceReference
from utils.logger import get_logger

logger = get_logger(__name__)


class LegalRAGPipeline:
    """End-to-end legal question answering orchestrator."""

    def __init__(
        self,
        retriever: Optional[AdvancedRetriever] = None,
        context_builder: Optional[LegalContextBuilder] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        validator: Optional[LegalAnswerValidator] = None,
        facet_validator: Optional[AnswerFacetValidator] = None,
        case_retriever: Optional[CaseLawRetriever] = None,
        planner: Optional[AnswerPlanner] = None,
        principle_extractor: Optional[JudicialPrincipleExtractor] = None,
    ) -> None:
        self.retriever = retriever or AdvancedRetriever()
        self.context_builder = context_builder or LegalContextBuilder()
        self.llm_provider = llm_provider or get_llm_provider()
        self.validator = validator or LegalAnswerValidator()
        self.facet_validator = facet_validator or AnswerFacetValidator()
        self.case_retriever = case_retriever or CaseLawRetriever()
        self.planner = planner or AnswerPlanner()
        self.principle_extractor = principle_extractor or JudicialPrincipleExtractor()

    @staticmethod
    def _build_sources_fallback_block(sources: List[SourceReference]) -> str:
        """Format retrieved statutory sources with their available metadata for fallback presentation."""
        if not sources:
            return "No specific statutory provisions could be retrieved."

        lines = []
        for s in sources:
            page_text = f"Page {', '.join(map(str, s.page_numbers))}" if s.page_numbers else "Section Record"
            score_text = f" · Relevance Score: {s.reranker_score:.2f}" if s.reranker_score is not None else ""
            lines.append(f"- **{s.source_label}**: {s.document_name} ({page_text}{score_text})")
            if s.text_snippet and s.text_snippet.strip():
                clean_snippet = s.text_snippet.strip().replace("\r", " ").replace("\n", " ")
                if len(clean_snippet) > 260:
                    clean_snippet = clean_snippet[:260].rstrip() + "..."
                lines.append(f"  > \"{clean_snippet}\"")
        return "\n".join(lines)

    def _build_fallback_answer(self, sources: List[SourceReference]) -> str:
        """Construct a user-facing fallback message preserving all retrieved legal sources."""
        sources_block = self._build_sources_fallback_block(sources)
        return (
            "## Answer\n\n"
            "The AI response generation service is temporarily unavailable or has reached its current request limit. "
            "However, relevant legal sources have been successfully retrieved from the NyayaSetu legal knowledge base.\n\n"
            "Please review the statutory sources and citations below, or try your question again after a short time.\n\n"
            "## Legal Sources\n\n"
            f"{sources_block}\n\n"
            "## Note\n\n"
            "The retrieval system remains operational, but natural-language answer generation is temporarily unavailable. "
            "These statutory provisions and excerpts are provided solely for informational reference and do not constitute formal legal advice."
        )

    def query(
        self,
        query_text: str,
        initial_k: Optional[int] = None,
        final_k: Optional[int] = None,
        max_per_document: Optional[int] = None,
    ) -> RAGResponse:
        """Process a legal inquiry and return a grounded, cited response.

        Args:
            query_text: Natural language legal question from user.
            initial_k: Candidate retrieval count override.
            final_k: Final reranked source count override.
            max_per_document: Document diversity limit override.

        Returns:
            RAGResponse object with synthesized answer, citations, and provenance.
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query cannot be empty or whitespace only.")

        logger.info("Executing Legal RAG Pipeline for query: '%s'", query_text.strip())

        # Step 1: Execute Phase 6 Advanced Retrieval
        retrieval_result = self.retriever.retrieve(
            query=query_text,
            initial_k=initial_k,
            final_k=final_k,
            max_per_document=max_per_document,
        )

        statutory_chunks = list(retrieval_result.results)
        q_analysis = retrieval_result.query_analysis or {}
        raw_auth_req = q_analysis.get("authority_requirement", "STATUTE") if isinstance(q_analysis, dict) else getattr(q_analysis, "authority_requirement", "STATUTE")
        auth_req_val = raw_auth_req.value if hasattr(raw_auth_req, "value") else str(raw_auth_req)

        facet_analysis = getattr(retrieval_result, "facet_analysis", None)
        facet_coverage = getattr(retrieval_result, "facet_coverage", None) or {}
        if isinstance(facet_analysis, dict):
            raw_facets = facet_analysis.get("facets", [])
            requested_facets = [
                f.get("display_name", f.get("name", ""))
                for f in raw_facets
                if f.get("required", True)
            ] if raw_facets else facet_analysis.get("required_facets", [])
        elif hasattr(facet_analysis, "facets"):
            requested_facets = [f.display_name for f in facet_analysis.facets if f.required]
        else:
            requested_facets = []

        # Step 1B: Case-Law Retrieval (Phase 8, 9, 10, 22)
        judicial_facet_names = {"judicial_principles", "precedent", "case_law", "court_interpretation", "judicial_test", "ratio", "holding", "distinguishing_principle"}
        raw_f_names = []
        if hasattr(facet_analysis, "facets"):
            raw_f_names = [f.name for f in facet_analysis.facets if f.required]
        elif isinstance(facet_analysis, dict):
            raw_f_names = [f.get("name", "") for f in facet_analysis.get("facets", []) if f.get("required", True)]

        requires_case_law = (auth_req_val in ("CASE_LAW", "BOTH")) or bool(set(raw_f_names) & judicial_facet_names)

        case_chunks: List[RerankedChunk] = []
        case_law_status = CaseLawStatus.NOT_REQUESTED.value
        case_warnings: List[str] = []

        if requires_case_law:
            target_secs = q_analysis.get("section_candidates", []) if isinstance(q_analysis, dict) else getattr(q_analysis, "section_candidates", [])
            target_topics = q_analysis.get("entities", []) if isinstance(q_analysis, dict) else getattr(q_analysis, "entities", [])
            p_issue = q_analysis.get("primary_issue") if isinstance(q_analysis, dict) else getattr(q_analysis, "primary_issue", None)
            ex_topics = q_analysis.get("excluded_topics") if isinstance(q_analysis, dict) else getattr(q_analysis, "excluded_topics", None)
            try:
                active_qa = retrieval_result.query_analysis if hasattr(retrieval_result, "query_analysis") else q_analysis
                case_chunks = self.case_retriever.retrieve(
                    query=query_text,
                    target_sections=target_secs,
                    target_topics=target_topics,
                    primary_issue=p_issue,
                    excluded_topics=ex_topics,
                    top_k=3,
                    query_analysis=active_qa,
                )
                if case_chunks:
                    case_law_status = CaseLawStatus.FOUND.value
                else:
                    case_law_status = CaseLawStatus.NOT_FOUND.value
                    case_warnings.append("The current indexed corpus does not contain verified judicial decisions sufficient to substantiate judicial principles on this issue.")
            except Exception as cle:
                logger.warning("Case-law retrieval failed: %s", cle)
                case_law_status = CaseLawStatus.CORPUS_UNAVAILABLE.value
                case_warnings.append("The current indexed corpus does not contain verified judicial decisions sufficient to substantiate judicial principles on this issue.")

        # Combine & Enforce Evidence Topic Compatibility and Budget (Rule 7 & 9: 2–5 sources)
        active_q_analysis = retrieval_result.query_analysis if hasattr(retrieval_result, "query_analysis") else q_analysis
        ranked_chunks = TopicCompatibilityEngine().filter_and_budget(
            statutory_chunks=statutory_chunks,
            case_chunks=case_chunks,
            query_analysis=active_q_analysis,
            min_sources=2,
            max_sources=5,
        )

        # In-Memory Evidence Graph (Phase 12)
        evidence_graph = LegalEvidenceGraph().build_from_retrieval(
            query=query_text,
            requested_facets=requested_facets,
            statutory_chunks=statutory_chunks,
            case_law_chunks=case_chunks,
        )
        graph_summary = evidence_graph.get_summary()

        retrieval_meta = {
            "initial_candidates_discovered": retrieval_result.initial_candidates_count,
            "candidates_retained_after_filtering": retrieval_result.filtered_candidates_count,
            "final_reranked_count": len(ranked_chunks),
            "statutory_chunks_count": len(statutory_chunks),
            "case_law_chunks_count": len(case_chunks),
            "case_law_status": case_law_status,
            "evidence_graph": graph_summary,
            "document_distribution": retrieval_result.document_distribution,
            "query_analysis": retrieval_result.query_analysis,
            "facet_coverage": facet_coverage,
            "debug_telemetry": retrieval_result.debug_telemetry,
        }

        # Step 2: Check for empty retrieval results
        if not ranked_chunks:
            logger.warning("No relevant statutory or judicial passages retrieved.")
            return RAGResponse(
                query=query_text,
                answer=(
                    "## Answer\n\n"
                    "No relevant Indian statutory provisions or judicial precedents could be found in the current "
                    "database to address your question.\n\n"
                    "## Legal Basis\n\n"
                    "The current legal corpus does not contain provisions or judgments addressing the specified inquiry.\n\n"
                    "## Sources\n\n"
                    "None\n\n"
                    "## Important Note\n\n"
                    "This system only searches the indexed legal database. Please verify specific Indian enactments."
                ),
                sources=[],
                retrieval_metadata=retrieval_meta,
                model_metadata={"provider": self.llm_provider.provider_name, "model": self.llm_provider.model_name},
                warnings=["Zero candidate legal sources found."],
                status="no_sources_found",
                requested_facets=requested_facets,
                facet_coverage=facet_coverage,
                facet_validation={},
                case_law_status=case_law_status,
                evidence_graph=graph_summary,
                generation_status="SUCCESS",
                retrieval_status="NO_SOURCES_FOUND",
                validation_status="NOT_RUN",
            )

        # Step 3: Build Grounded Context
        context_result = self.context_builder.build_context(ranked_chunks)
        sources: List[SourceReference] = context_result.sources

        is_deterministic_fallback = False
        generation_error_category = None
        generation_status = "SUCCESS"

        # Step 4: Check LLM Provider Configuration
        if not self.llm_provider.is_configured():
            logger.info(
                "LLM provider '%s' is not configured. Engaging deterministic answer builder.",
                self.llm_provider.provider_name,
            )
            raw_answer = DeterministicAnswerBuilder.build_answer(
                query=query_text,
                sources=sources,
                query_analysis=retrieval_result.query_analysis if hasattr(retrieval_result, "query_analysis") else None,
                facet_analysis=facet_analysis,
            )
            is_deterministic_fallback = True
            generation_status = "RETRIEVAL_ONLY"
            generation_error_category = "UNCONFIGURED"
            model_meta = {
                "provider": self.llm_provider.provider_name,
                "model": self.llm_provider.model_name,
                "configured": False,
                "fallback": True,
            }
        else:
            # Step 5: Construct Prompt
            prompt = build_rag_prompt(
                query=retrieval_result.normalized_query,
                formatted_context=context_result.formatted_context,
                max_source_index=len(sources),
                requested_facets=requested_facets,
            )

            # Step 6: Generate Completion via LLM Provider
            try:
                llm_response = self.llm_provider.generate(
                    prompt=prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                )
                raw_answer = llm_response.content
                model_meta = {
                    "provider": self.llm_provider.provider_name,
                    "model": llm_response.model,
                    "prompt_tokens": llm_response.prompt_tokens,
                    "completion_tokens": llm_response.completion_tokens,
                    "configured": True,
                }
            except LLMError as err:
                logger.error(
                    "LLM generation failed [category=%s, status=%s]: %s",
                    err.category,
                    err.status_code,
                    err.message,
                )
                generation_error_category = err.category
                is_deterministic_fallback = True
                generation_status = "RETRIEVAL_ONLY"

                logger.info(
                    "Switching to deterministic evidence-grounded fallback answer builder (reusing %d retrieved sources)...",
                    len(sources),
                )
                raw_answer = DeterministicAnswerBuilder.build_answer(
                    query=query_text,
                    sources=sources,
                    query_analysis=retrieval_result.query_analysis if hasattr(retrieval_result, "query_analysis") else None,
                    facet_analysis=facet_analysis,
                )
                model_meta = {
                    "provider": self.llm_provider.provider_name,
                    "model": getattr(self.llm_provider, "model_name", "unknown"),
                    "error_category": err.category,
                    "status_code": err.status_code,
                    "configured": True,
                    "fallback": True,
                }
            except Exception as err:
                logger.error("Unexpected error during LLM generation: %s", err)
                generation_error_category = "UNKNOWN_ERROR"
                is_deterministic_fallback = True
                generation_status = "RETRIEVAL_ONLY"

                logger.info("Switching to deterministic evidence-grounded fallback answer builder on unexpected error...")
                raw_answer = DeterministicAnswerBuilder.build_answer(
                    query=query_text,
                    sources=sources,
                    query_analysis=retrieval_result.query_analysis if hasattr(retrieval_result, "query_analysis") else None,
                    facet_analysis=facet_analysis,
                )
                model_meta = {
                    "provider": self.llm_provider.provider_name,
                    "model": getattr(self.llm_provider, "model_name", "unknown"),
                    "error_category": "UNKNOWN_ERROR",
                    "status_code": 500,
                    "configured": True,
                    "fallback": True,
                }

        # Step 7: Deterministic Citation and Safety Validation
        val_result = self.validator.validate(
            answer=raw_answer,
            available_source_count=len(sources),
        )

        # Step 8: Deep Claim-to-Evidence and Facet Completeness Validation
        facet_val_result = None
        target_act_name = (
            retrieval_result.query_analysis.get("act")
            if isinstance(retrieval_result.query_analysis, dict)
            else getattr(retrieval_result.query_analysis, "act", None)
        )

        has_facets = bool(
            getattr(facet_analysis, "facets", None)
            or (isinstance(facet_analysis, dict) and facet_analysis.get("facets"))
        )
        if facet_analysis and has_facets:
            facet_val_result = self.facet_validator.validate_answer(
                answer_text=raw_answer,
                facet_analysis=facet_analysis,
                facet_coverage=facet_coverage,
                sources=sources,
                target_act=target_act_name,
                query_analysis=active_q_analysis,
            )
            logger.info(
                "Facet & Claim Validation: complete=%s, status=%s, missing=%s, supported_claims=%d/%d",
                facet_val_result.complete,
                facet_val_result.quality_status.value,
                facet_val_result.missing_facets,
                facet_val_result.claim_metrics.get("supported_claims", 0),
                facet_val_result.claim_metrics.get("total_claims", 0),
            )

            # Single-pass recovery re-prompt ONLY for normal LLM flow (do NOT call LLM when in fallback mode)
            needs_recovery = (
                not facet_val_result.complete
                or facet_val_result.missing_facets
                or facet_val_result.claim_metrics.get("false_negative_claims", 0) > 0
                or facet_val_result.claim_metrics.get("unsupported_claims", 0) > 0
            )

            MAX_FACET_RECOVERY_ATTEMPTS = 1
            if needs_recovery and not is_deterministic_fallback and self.llm_provider.is_configured():
                defective_items = list(facet_val_result.missing_facets)
                if facet_val_result.claim_metrics.get("false_negative_claims", 0) > 0:
                    for cr in facet_val_result.claim_results:
                        if cr.get("is_negative_claim") and not cr.get("negative_claim_valid"):
                            defective_items.append(f"{cr.get('facet', 'statute')} (False 'unavailable' claim rejected)")

                logger.info(
                    "Executing single-pass facet recovery re-prompt for defective/missing items: %s",
                    defective_items,
                )
                try:
                    recovery_prompt = build_recovery_prompt(
                        query=retrieval_result.normalized_query,
                        formatted_context=context_result.formatted_context,
                        missing_facets=defective_items,
                        previous_answer=raw_answer,
                        max_source_index=len(sources),
                    )
                    recovery_llm_response = self.llm_provider.generate(
                        prompt=recovery_prompt,
                        system_instruction=SYSTEM_INSTRUCTION,
                    )
                    recovered_answer = recovery_llm_response.content

                    re_val = self.facet_validator.validate_answer(
                        answer_text=recovered_answer,
                        facet_analysis=facet_analysis,
                        facet_coverage=facet_coverage,
                        sources=sources,
                        target_act=target_act_name,
                        query_analysis=active_q_analysis,
                    )
                    logger.info(
                        "Post-recovery validation check: complete=%s, status=%s, missing=%s, supported_claims=%d/%d",
                        re_val.complete,
                        re_val.quality_status.value,
                        re_val.missing_facets,
                        re_val.claim_metrics.get("supported_claims", 0),
                        re_val.claim_metrics.get("total_claims", 0),
                    )
                    if (
                        re_val.complete
                        or re_val.claim_metrics.get("supported_claims", 0) >= facet_val_result.claim_metrics.get("supported_claims", 0)
                        or len(re_val.missing_facets) < len(facet_val_result.missing_facets)
                    ):
                        raw_answer = recovered_answer
                        facet_val_result = re_val
                        model_meta["facet_recovery_applied"] = True
                        if hasattr(recovery_llm_response, "completion_tokens") and recovery_llm_response.completion_tokens:
                            model_meta["completion_tokens"] = (
                                model_meta.get("completion_tokens", 0) + recovery_llm_response.completion_tokens
                            )
                except Exception as rec_err:
                    logger.warning("Facet recovery generation failed: %s", rec_err)

        warnings_combined = list(val_result.warnings) + case_warnings
        if is_deterministic_fallback:
            if generation_error_category in ("RATE_LIMIT", "QUOTA_EXCEEDED"):
                warnings_combined.append(
                    "AI synthesis is temporarily unavailable; answer limited to retrieved legal evidence."
                )
            else:
                warnings_combined.append(
                    "AI synthesis temporarily unavailable; answer limited to retrieved legal evidence."
                )
        elif facet_val_result and not facet_val_result.complete:
            warnings_combined.append(
                f"Quality notice: [{facet_val_result.quality_status.value}] Missing or ungrounded facets: {', '.join(facet_val_result.missing_facets)}"
            )

        if is_deterministic_fallback:
            val_status = "PASSED" if (val_result.is_valid and facet_val_result and facet_val_result.complete) else "PARTIALLY_COMPLETE"
        else:
            val_status = "PASSED" if (val_result.is_valid and (not facet_val_result or facet_val_result.complete or facet_val_result.quality_status.value in ("COMPLETE", "PARTIALLY_COMPLETE"))) else "FAILED"

        logger.info(
            "Answer processing completed (len: %d chars, valid: %s, quality: %s, gen_status: %s, val_status: %s, warnings: %d)",
            len(raw_answer),
            val_result.is_valid,
            facet_val_result.quality_status.value if facet_val_result else ("PARTIALLY_COMPLETE" if is_deterministic_fallback else "COMPLETE"),
            generation_status,
            val_status,
            len(warnings_combined),
        )

        return RAGResponse(
            query=query_text,
            answer=raw_answer,
            sources=sources,
            retrieval_metadata=retrieval_meta,
            model_metadata=model_meta,
            warnings=warnings_combined,
            status="retrieval_only" if is_deterministic_fallback else "success",
            requested_facets=requested_facets,
            facet_coverage=facet_coverage,
            facet_validation=facet_val_result.to_dict() if facet_val_result else {},
            claim_validation=facet_val_result.claim_metrics if facet_val_result else {},
            quality_status=facet_val_result.quality_status.value if facet_val_result else ("PARTIALLY_COMPLETE" if is_deterministic_fallback else "COMPLETE"),
            case_law_status=case_law_status,
            evidence_graph=evidence_graph.to_dict(),
            generation_status=generation_status,
            retrieval_status="SUCCESS",
            validation_status=val_status,
        )

