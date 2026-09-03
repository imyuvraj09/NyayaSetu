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
from prompts.prompts import SYSTEM_INSTRUCTION, build_rag_prompt
from rag.answer_validator import LegalAnswerValidator
from rag.context_builder import LegalContextBuilder
from retrieval.advanced_retriever import AdvancedRetriever
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
    ) -> None:
        self.retriever = retriever or AdvancedRetriever()
        self.context_builder = context_builder or LegalContextBuilder()
        self.llm_provider = llm_provider or get_llm_provider()
        self.validator = validator or LegalAnswerValidator()

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

        ranked_chunks = retrieval_result.results
        retrieval_meta = {
            "initial_candidates_discovered": retrieval_result.initial_candidates_count,
            "candidates_retained_after_filtering": retrieval_result.filtered_candidates_count,
            "final_reranked_count": len(ranked_chunks),
            "document_distribution": retrieval_result.document_distribution,
        }

        # Step 2: Check for empty retrieval results
        if not ranked_chunks:
            logger.warning("No relevant statutory passages retrieved.")
            return RAGResponse(
                query=query_text,
                answer=(
                    "## Answer\n\n"
                    "No relevant Indian statutory provisions or legal sections could be found in the current "
                    "database to address your question.\n\n"
                    "## Legal Basis\n\n"
                    "The current statutory corpus does not contain provisions addressing the specified inquiry.\n\n"
                    "## Sources\n\n"
                    "None\n\n"
                    "## Important Note\n\n"
                    "This system only searches the indexed statutory database. Please verify specific Indian enactments."
                ),
                sources=[],
                retrieval_metadata=retrieval_meta,
                model_metadata={"provider": self.llm_provider.provider_name, "model": self.llm_provider.model_name},
                warnings=["Zero candidate legal sources found."],
                status="no_sources_found",
            )

        # Step 3: Build Grounded Context
        context_result = self.context_builder.build_context(ranked_chunks)
        sources: List[SourceReference] = context_result.sources

        # Step 4: Check LLM Provider Configuration
        if not self.llm_provider.is_configured():
            if self.llm_provider.provider_name in ("gemini", "google"):
                provider_name_display = "Google Gemini"
                key_name = "GEMINI_API_KEY"
            elif self.llm_provider.provider_name == "openai":
                provider_name_display = "OpenAI"
                key_name = "OPENAI_API_KEY"
            else:
                provider_name_display = self.llm_provider.provider_name.title()
                key_name = f"{self.llm_provider.provider_name.upper()}_API_KEY"

            logger.info(
                "LLM provider '%s' is not configured. Returning retrieved sources without LLM synthesis.",
                self.llm_provider.provider_name,
            )
            fallback_text = (
                f"## Answer\n\n"
                f"LLM generation is currently not configured ({provider_name_display} API key missing). "
                f"However, the system successfully retrieved and reranked {len(sources)} relevant statutory provisions "
                f"from the Indian legal database.\n\n"
                f"## Legal Basis\n\n"
                f"Please review the attached source references below for official statutory text and citations.\n\n"
                f"## Sources\n\n"
                + "\n".join(f"{s.source_label}: {s.document_name} (Page {s.page_numbers[0] if s.page_numbers else 'N/A'})" for s in sources)
                + f"\n\n## Important Note\n\n"
                f"Configure {key_name} in your environment or .env file to enable AI natural language synthesis. "
                f"These statutory provisions and excerpts are provided solely for informational reference and do not constitute formal legal advice."
            )
            return RAGResponse(
                query=query_text,
                answer=fallback_text,
                sources=sources,
                retrieval_metadata=retrieval_meta,
                model_metadata={
                    "provider": self.llm_provider.provider_name,
                    "model": self.llm_provider.model_name,
                    "configured": False,
                },
                warnings=[
                    f"LLM provider '{self.llm_provider.provider_name}' is not configured. "
                    f"Configure {key_name} in .env to enable natural language synthesis."
                ],
                status="unconfigured_llm",
            )

        # Step 5: Construct Prompt
        prompt = build_rag_prompt(
            query=retrieval_result.normalized_query,
            formatted_context=context_result.formatted_context,
            max_source_index=len(sources),
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
            fallback_answer = self._build_fallback_answer(sources)
            return RAGResponse(
                query=query_text,
                answer=fallback_answer,
                sources=sources,
                retrieval_metadata=retrieval_meta,
                model_metadata={
                    "provider": self.llm_provider.provider_name,
                    "model": getattr(self.llm_provider, "model_name", "unknown"),
                    "error_category": err.category,
                    "status_code": err.status_code,
                    "configured": True,
                },
                warnings=[f"LLM {err.category}: natural language generation temporarily unavailable."],
                status="rate_limited" if err.category in ("RATE_LIMIT_EXCEEDED", "QUOTA_EXCEEDED") else "fallback",
            )
        except Exception as err:
            logger.error("Unexpected error during LLM generation: %s", err)
            fallback_answer = self._build_fallback_answer(sources)
            return RAGResponse(
                query=query_text,
                answer=fallback_answer,
                sources=sources,
                retrieval_metadata=retrieval_meta,
                model_metadata={
                    "provider": self.llm_provider.provider_name,
                    "model": getattr(self.llm_provider, "model_name", "unknown"),
                    "error_category": "LLM_ERROR",
                    "status_code": 500,
                    "configured": True,
                },
                warnings=[f"LLM generation error: {err}"],
                status="error",
            )

        # Step 7: Deterministic Answer Validation
        val_result = self.validator.validate(
            answer=raw_answer,
            available_source_count=len(sources),
        )

        logger.info(
            "Answer generated successfully (len: %d chars, valid: %s, warnings: %d)",
            len(raw_answer),
            val_result.is_valid,
            len(val_result.warnings),
        )

        return RAGResponse(
            query=query_text,
            answer=raw_answer,
            sources=sources,
            retrieval_metadata=retrieval_meta,
            model_metadata=model_meta,
            warnings=val_result.warnings,
            status="success",
        )
