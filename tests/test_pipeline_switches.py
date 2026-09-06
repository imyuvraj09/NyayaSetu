import os
import sys
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAG_SERVICE_DIR = os.path.join(REPO_ROOT, "rag-service")
for p in [REPO_ROOT, RAG_SERVICE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from rag.rag_pipeline import LegalRAGPipeline
from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk, RetrievedChunk
from research.schemas import RoutingDecision, RoutingMode


class TestPipelineSwitches(unittest.TestCase):
    """Verify research switches do not degrade production pipeline."""

    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_context_builder = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_validator = MagicMock()
        self.mock_facet_validator = MagicMock()
        self.mock_case_retriever = MagicMock()

        # Build dummy reranked chunk
        dummy_chunk = RerankedChunk(
            rank=1,
            chunk_id="bns_c001",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            document_type="Criminal Law",
            source_filename="bns_2023.pdf",
            page_numbers=[1],
            text="Section 303: Whoever commits theft...",
            similarity_score=0.90,
            reranker_score=0.95,
            metadata={"section_number": "303", "act_short_name": "BNS"},
            section_number="303",
            act_short_name="BNS",
        )
        retrieval_res = AdvancedRetrievalResult(
            original_query="What is theft?",
            normalized_query="theft",
            initial_k=20,
            final_k=5,
            initial_candidates_count=1,
            filtered_candidates_count=1,
            final_results_count=1,
            results=[dummy_chunk],
            document_distribution={"Bharatiya Nyaya Sanhita, 2023": 1},
        )
        self.mock_retriever.retrieve.return_value = retrieval_res
        self.mock_case_retriever.retrieve_case_law.return_value = []
        self.mock_validator.validate_answer.return_value = MagicMock(is_valid=True, warnings=[])
        self.mock_facet_validator.validate_facets.return_value = MagicMock(
            complete=True,
            missing_facets=[],
            quality_status=MagicMock(value="COMPLETE"),
            claim_metrics={},
            to_dict=lambda: {},
        )
        self.mock_context_builder.build_context.return_value = MagicMock(
            formatted_context="[SOURCE 1] Excerpt",
            sources=[],
        )
        self.mock_llm.generate.return_value = MagicMock(
            content="## Answer\nTheft is punishable under Section 303.",
            token_count=50,
        )

        self.pipeline = LegalRAGPipeline(
            retriever=self.mock_retriever,
            context_builder=self.mock_context_builder,
            llm_provider=self.mock_llm,
            validator=self.mock_validator,
            facet_validator=self.mock_facet_validator,
            case_retriever=self.mock_case_retriever,
        )

    def test_default_use_fact_routing_is_false(self):
        """Verify default call has use_fact_routing=False and does not attach fact_first_routing."""
        response = self.pipeline.query("What is theft under BNS?")
        self.assertEqual(response.status, "success")
        self.assertNotIn("fact_first_routing", response.retrieval_metadata)

    def test_use_fact_routing_true_attaches_metadata(self):
        """Verify use_fact_routing=True executes router and attaches metadata."""
        response = self.pipeline.query(
            "What is theft under Section 303 of BNS?",
            use_fact_routing=True,
        )
        self.assertEqual(response.status, "success")
        self.assertIn("fact_first_routing", response.retrieval_metadata)
        r_meta = response.retrieval_metadata["fact_first_routing"]
        self.assertIn("selected_regimes", r_meta)
        self.assertIn("routing_mode", r_meta)
        self.assertIn("confidence", r_meta)


if __name__ == "__main__":
    unittest.main()
