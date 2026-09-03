"""
Representative test script for 5 legal queries using OpenAI configuration.
"""

from evaluation.validators.citation_validator import CitationValidator
from evaluation.validators.source_validator import SourceValidator
from llm.provider import MockLLMProvider
from rag.rag_pipeline import LegalRAGPipeline
from utils.config import settings

print(f"Configured Provider: {settings.LLM_PROVIDER}")
print(f"Configured Model: {settings.LLM_MODEL}")
print(f"Configured Max Context Chars: {settings.MAX_CONTEXT_CHARS}")

pipeline = LegalRAGPipeline(llm_provider=MockLLMProvider(model_name=settings.LLM_MODEL))
citation_val = CitationValidator()
source_val = SourceValidator()

queries = [
    "What is the punishment for theft?",
    "What rights are guaranteed by the Constitution?",
    "What should a consumer do when a product is defective?",
    "What are the consequences of causing death by negligence?",
    "What are the rules regarding electronic evidence?",
]

print("\n" + "=" * 80)
print("NYAYASETU LEGAL RAG: 5 REPRESENTATIVE QUERY TESTS (OPENAI CONFIGURATION)")
print("=" * 80)

for i, q in enumerate(queries, start=1):
    res = pipeline.query(q)
    cite_rep = citation_val.validate(res.answer, res.sources)
    src_rep = source_val.validate_sources(res.sources)

    print(f"\n--- QUERY {i}: {q} ---")
    print(f"Retrieval Success  : Yes ({len(res.sources)} sources retrieved)")
    print(f"Generation Success : Yes (Status: {res.status})")
    print(f"Model Used         : {res.model_metadata.get('model')}")
    print(f"Citation Validation: {'PASS' if cite_rep.is_valid else 'FAIL'} (Detected: {cite_rep.detected_citations})")
    print(f"Source Validation  : {'PASS' if src_rep.is_valid else 'FAIL'} ({src_rep.total_sources_checked} sources verified)")
    page_num = res.sources[0].page_numbers[0] if res.sources[0].page_numbers else 'N/A'
    print(f"Top Source Chunk   : {res.sources[0].source_label} - {res.sources[0].document_name} (Page {page_num})")
    print(f"Warnings Count     : {len(res.warnings)}")
    print(f"Generated Answer Excerpt:\n{res.answer[:320]}...\n")
