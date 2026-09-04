"""
Test script for live /api/v1/query endpoint.
"""
import json
import urllib.request

def main():
    url = "http://localhost:8000/api/v1/query"
    payload = {
        "query": "What constitutes murder under the Bharatiya Nyaya Sanhita, 2023, and what is the punishment prescribed for it?",
        "enable_reranking": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    print("Sending query to", url)
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("\n=== RESPONSE SUMMARY ===")
        print("Status:", res.get("status"))
        print("Quality Status:", res.get("quality_status"))
        print("Claim Validation:", res.get("claim_validation"))
        print("Requested Facets:", res.get("requested_facets"))
        print("Facet Coverage:", res.get("facet_coverage"))
        print("Facet Validation:", res.get("facet_validation"))
        print("Provisions:", res.get("retrieved_provisions"))
        print("Confidence:", res.get("confidence_score"))
        print("Multi-Part:", res.get("is_multi_part"))
        print("\n=== SOURCES ===")
        for i, s in enumerate(res.get("sources", [])):
            print(f"[{i+1}] {s.get('document_name')} | Sec: {s.get('metadata', {}).get('section', '')} | Pages: {s.get('page_numbers')}")
        print("\n=== ANSWER ===")
        print(res.get("answer"))

if __name__ == "__main__":
    main()
