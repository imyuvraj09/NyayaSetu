"""Test all 7 newly added Indian statutes against NyayaSetu RAG Service."""
import json
import time
import requests

TEST_QUERIES = [
    {
        "id": 1,
        "statute": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "query": "What is the constitution and role of the Internal Complaints Committee (ICC)?",
        "expected_doc": "sexual_harassment_workplace_act_2013.pdf",
    },
    {
        "id": 2,
        "statute": "The Protection of Children from Sexual Offences Act, 2012 (POCSO)",
        "query": "What are the mandatory reporting obligations under POCSO?",
        "expected_doc": "pocso_act_2012.pdf",
    },
    {
        "id": 3,
        "statute": "The Right to Information Act, 2005 (RTI)",
        "query": "What is the time limit for providing information under the RTI Act?",
        "expected_doc": "right_to_information_act_2005.pdf",
    },
    {
        "id": 4,
        "statute": "The Right of Children to Free and Compulsory Education Act, 2009 (RTE)",
        "query": "What is the reservation percentage for disadvantaged groups in private schools under the RTE Act?",
        "expected_doc": "right_to_education_act_2009.pdf",
    },
    {
        "id": 5,
        "statute": "The Goods and Services Tax Act, 2017 (GST)",
        "query": "What constitutes a supply under the GST Act?",
        "expected_doc": "gst_act_2017.pdf",
    },
    {
        "id": 6,
        "statute": "The Companies Act, 2013",
        "query": "What are the statutory requirements for Corporate Social Responsibility (CSR)?",
        "expected_doc": "companies_act_2013.pdf",
    },
    {
        "id": 7,
        "statute": "The Insolvency and Bankruptcy Code, 2016 (IBC)",
        "query": "What is the time limit for completing the Corporate Insolvency Resolution Process (CIRP)?",
        "expected_doc": "insolvency_bankruptcy_code_2016.pdf",
    },
]

def main():
    print("=" * 80)
    print("NYAYASETU — 7 INDIAN STATUTES RETRIEVAL & GROUNDING VERIFICATION")
    print("=" * 80)

    results = []

    for t in TEST_QUERIES:
        print(f"\n[{t['id']}/7] Testing: {t['statute']}")
        print(f"Query: '{t['query']}'")
        payload = {
            "query": t["query"],
            "session_id": f"test-session-{t['id']}",
            "top_k": 5,
        }
        
        start_time = time.time()
        try:
            resp = requests.post("http://localhost:8000/api/v1/query", json=payload, timeout=90)
            elapsed = time.time() - start_time
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                
                # Check citations
                retrieved_files = [s.get("source_filename") for s in sources]
                has_expected = any(t["expected_doc"] in str(f) for f in retrieved_files)
                
                print(f"Status: SUCCESS ({elapsed:.2f}s)")
                print(f"Retrieved Sources ({len(sources)}):")
                for idx, s in enumerate(sources, 1):
                    doc_name = s.get("document_name", "Unknown")
                    fn = s.get("source_filename", "Unknown")
                    pages = s.get("page_numbers", [])
                    print(f"  [{idx}] {doc_name} | File: {fn} | Page(s): {pages}")
                
                print(f"\nExpected File Present: {has_expected}")
                print(f"\nAnswer Preview (first 300 chars):\n{answer[:300]}...\n")
                
                results.append({
                    "id": t["id"],
                    "statute": t["statute"],
                    "query": t["query"],
                    "success": True,
                    "elapsed": elapsed,
                    "has_expected": has_expected,
                    "answer_length": len(answer),
                    "sources": sources,
                    "answer": answer
                })
            else:
                print(f"Status: ERROR HTTP {resp.status_code}: {resp.text}")
                results.append({
                    "id": t["id"],
                    "statute": t["statute"],
                    "query": t["query"],
                    "success": False,
                    "error": resp.text
                })
        except Exception as err:
            print(f"Status: EXCEPTION: {err}")
            results.append({
                "id": t["id"],
                "statute": t["statute"],
                "query": t["query"],
                "success": False,
                "error": str(err)
            })

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY:")
    print("=" * 80)
    all_passed = True
    for r in results:
        status_str = "PASS" if (r.get("success") and r.get("has_expected")) else "FAIL"
        if status_str == "FAIL":
            all_passed = False
        print(f"Query {r['id']}: [{status_str}] {r['statute']} (Time: {r.get('elapsed', 0):.2f}s)")
    
    print("=" * 80)
    print(f"Overall Result: {'ALL 7 TESTS PASSED PERFECTLY!' if all_passed else 'SOME TESTS FAILED'}")

    with open("data/processed/verification_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
