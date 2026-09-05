import sys
sys.path.insert(0, '.')
from retrieval.advanced_retriever import AdvancedRetriever
from rag.context_builder import LegalContextBuilder
from retrieval.provision_relationship_validator import get_provision_relationship_validator

r = AdvancedRetriever()
res = r.retrieve('How are electronic records admitted under Bharatiya Sakshya Adhiniyam?')
cb = LegalContextBuilder()
context_result = cb.build_context(res.results)

for i, s in enumerate(context_result.sources):
    print(f"Source {i}: label={s.source_label}, sec={s.section_number}, len(text_snippet)={len(s.text_snippet)}")
    print(f"Has certificate: {'certificate' in s.text_snippet.lower()}")

val = get_provision_relationship_validator()
mock_answer = "Under Indian law, electronic records are admitted under Section 63 of Bharatiya Sakshya Adhiniyam. Under Section 62, contents may be proved under Section 63 if conditions are satisfied."
sanitized = val.correct_and_sanitize_relationships(mock_answer, context_result.sources, res.query_analysis)
print("\nSanitized Answer:\n", sanitized)
