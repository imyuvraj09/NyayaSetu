import sys
import json
sys.path.insert(0, '.')
from rag.rag_pipeline import LegalRAGPipeline

q = "A woman alleges sexual harassment at her workplace by a senior employee whose name is RAJU. What legal protections, complaint mechanisms, and evidence are relevant?"

p = LegalRAGPipeline()
res = p.query(q)

print("Status:", res.status)
print("Query:", res.query)
print("Sources count:", len(res.sources))
for s in res.sources:
    print(f"  Source: doc={s.document_name}, sec={getattr(s, 'section_number', '')}, title={getattr(s, 'section_title', '')}")

try:
    ans_data = json.loads(res.answer)
    print("\nLegal Domain:", ans_data.get("legalDomain"))
    print("\nMain Answer:\n", ans_data.get("mainAnswer")[:400])
    print("\nLegal Basis:\n", ans_data.get("legalBasis")[:400])
except Exception:
    print("\nAnswer raw:\n", res.answer[:500])
