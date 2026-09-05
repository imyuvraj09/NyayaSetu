import sys
sys.path.insert(0, '.')
from retrieval.advanced_retriever import AdvancedRetriever
from rag.context_builder import LegalContextBuilder

r = AdvancedRetriever()
res = r.retrieve('How are electronic records admitted under Bharatiya Sakshya Adhiniyam?')
cb = LegalContextBuilder()
context_result = cb.build_context(res.results)
qa = res.query_analysis
print('Type of query_analysis:', type(qa))
print('query_analysis keys/attrs:', dir(qa) if not isinstance(qa, dict) else qa.keys())
lq = getattr(qa, 'legal_question', None) if hasattr(qa, 'legal_question') else (qa.get('legal_question') if isinstance(qa, dict) else None)
print('legal_question:', lq)
