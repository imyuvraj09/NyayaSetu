"""
Live test for Case-Law RAG integration on FastAPI /api/v1/query.
"""
import json
import urllib.request

def test_live_dual_query():
    url = "http://localhost:8000/api/v1/query"
    payload = {
        "query": "What is consent in sexual offences under Bharatiya Nyaya Sanhita, and what are the Supreme Court principles regarding consent vs misconception of fact in a promise to marry?",
        "enable_reranking": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    print("Sending Dual Query to", url)
    with urllib.request.urlopen(req, timeout=240) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("\n=== RESPONSE SUMMARY ===")
        print("Status:", res.get("status"))
        print("Quality Status:", res.get("quality_status"))
        print("Case Law Status:", res.get("case_law_status"))
        print("Confidence:", res.get("confidence_score"))
        print("Requested Facets:", res.get("requested_facets"))
        
        print("\n=== SOURCES ===")
        for i, s in enumerate(res.get("sources", [])):
            ev_type = s.get("evidence_type", "STATUTE")
            doc = s.get("case_name") or s.get("document_name")
            para = s.get("paragraph_number")
            sec = s.get("metadata", {}).get("section", "")
            print(f"[{i+1}] [{ev_type}] {doc} (Sec: {sec}, Para: {para})")
            
        print("\n=== EVIDENCE GRAPH ===")
        eg = res.get("evidence_graph", {})
        if eg:
            print("Nodes:", len(eg.get("nodes", {})))
            print("Edges:", len(eg.get("edges", [])))
            print("Summary:", eg.get("summary", {}))

        print("\n=== FINAL GENERATED ANSWER ===")
        print(res.get("answer"))

if __name__ == "__main__":
    test_live_dual_query()
