import sys
sys.path.insert(0, '.')
from retrieval.advanced_retriever import AdvancedRetriever

r = AdvancedRetriever()
res = r.retrieve('How are electronic records admitted under Bharatiya Sakshya Adhiniyam?')
print('Attributes:', [a for a in dir(res) if not a.startswith('_')])
print('Results count:', len(res.results))
for i, c in enumerate(res.results):
    text = getattr(c, 'text', '')
    cid = getattr(c, 'chunk_id', '')
    sec = getattr(c, 'section_numbers', None) or (c.metadata.get('section_numbers') if hasattr(c, 'metadata') else None)
    score = getattr(c, 'final_score', None) or getattr(c, 'score', None)
    print(f"Result {i}: id={cid} sec={sec} score={score}")
    print(f"Text: {text[:160]}...\n")

