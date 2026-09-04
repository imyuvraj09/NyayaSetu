"""
Facet Completeness Evaluation Benchmark for NyayaSetu.

Evaluates:
1. Dynamic legal question facet analysis across diverse statutes.
2. Multi-facet retrieval and secondary targeted recovery for missing provisions.
3. End-to-end facet validation and quality verification.
"""

import sys
import os
from pathlib import Path

# Add rag-service root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.answer_facet_analyzer import AnswerFacetAnalyzer
from retrieval.advanced_retriever import AdvancedRetriever
from rag.answer_facet_validator import AnswerFacetValidator


TEST_CASES = [
    {
        "id": "TC-01",
        "name": "BNS Murder Definition + Punishment",
        "query": "What constitutes murder under the Bharatiya Nyaya Sanhita, 2023, and what is the punishment prescribed for it?",
        "expected_facets": ["definition", "punishment"],
        "min_retrieved_facets": ["definition", "punishment"],
    },
    {
        "id": "TC-02",
        "name": "BNS Murder Exceptions",
        "query": "What are the exceptions to murder under the Bharatiya Nyaya Sanhita?",
        "expected_facets": ["exceptions"],
        "min_retrieved_facets": ["exceptions"],
    },
    {
        "id": "TC-03",
        "name": "BNSS Arrest Procedure",
        "query": "What is the procedure for arrest under Bharatiya Nagarik Suraksha Sanhita?",
        "expected_facets": ["procedure"],
        "min_retrieved_facets": ["procedure"],
    },
    {
        "id": "TC-04",
        "name": "BNSS Arrestee Rights",
        "query": "What rights does an arrested person have under Bharatiya Nagarik Suraksha Sanhita?",
        "expected_facets": ["rights"],
        "min_retrieved_facets": ["rights"],
    },
    {
        "id": "TC-05",
        "name": "RTI Time Limit & Remedies",
        "query": "What is the time limit for filing an RTI request and what remedy is available if not answered?",
        "expected_facets": ["time_limit", "remedies"],
        "min_retrieved_facets": ["time_limit"],
    },
    {
        "id": "TC-06",
        "name": "BNSS Grounds of Arrest & Rights",
        "query": "What are the grounds of arrest and what rights does an arrested person have under Bharatiya Nagarik Suraksha Sanhita?",
        "expected_facets": ["grounds", "rights"],
        "min_retrieved_facets": ["grounds", "rights"],
    },
    {
        "id": "TC-07",
        "name": "POCSO Sexual Assault Definition & Punishment",
        "query": "What constitutes penetrative sexual assault under POCSO Act and what is the punishment prescribed for it?",
        "expected_facets": ["definition", "punishment"],
        "min_retrieved_facets": ["definition", "punishment"],
    },
    {
        "id": "TC-08",
        "name": "Consumer Protection Rights & Procedure",
        "query": "What are the consumer rights and dispute redressal procedure under Consumer Protection Act?",
        "expected_facets": ["rights", "procedure"],
        "min_retrieved_facets": ["rights"],
    },
]


def run_facet_evaluation():
    print("=" * 80)
    print("NYAYASETU LEGAL FACET COMPLETENESS BENCHMARK")
    print("=" * 80)

    analyzer = AnswerFacetAnalyzer()
    retriever = AdvancedRetriever()
    validator = AnswerFacetValidator()

    passed_analysis = 0
    passed_retrieval = 0
    total = len(TEST_CASES)

    for tc in TEST_CASES:
        print(f"\n[{tc['id']}] {tc['name']}")
        print(f"Query: {tc['query']}")

        # 1. Question Facet Analysis
        analysis = analyzer.analyze(tc["query"])
        detected_facet_names = [f.name for f in analysis.facets]
        detected_display = [f.display_name for f in analysis.facets]
        print(f"  Detected Facets: {detected_display} (raw: {detected_facet_names})")

        analysis_ok = all(exp in detected_facet_names for exp in tc["expected_facets"])
        if analysis_ok:
            print("  Analysis Status: PASS (all expected facets detected)")
            passed_analysis += 1
        else:
            missing_expected = [exp for exp in tc["expected_facets"] if exp not in detected_facet_names]
            print(f"  Analysis Status: FAIL (missing expected: {missing_expected})")

        # 2. Hybrid Retrieval with Secondary Facet Recovery
        retrieval_res = retriever.retrieve(tc["query"])
        coverage = retrieval_res.facet_coverage
        print(f"  Facet Evidence Coverage: {coverage}")

        # Check sections retrieved
        sections_found = set()
        for chunk in retrieval_res.results[:5]:
            sec = getattr(chunk, "section_number", "")
            title = getattr(chunk, "section_title", "")
            act = getattr(chunk, "act_short_name", "")
            if sec or title:
                sections_found.add(f"{act} Sec {sec}: {title}")
        print(f"  Top Provisions Retrieved: {list(sections_found)[:4]}")

        # Check minimum retrieved facets
        retrieval_ok = True
        for min_facet in tc["min_retrieved_facets"]:
            # Check either direct coverage bool or display name
            found = False
            for f_name, covered in coverage.items():
                if min_facet.lower() in f_name.lower() and covered:
                    found = True
                    break
            if not found:
                retrieval_ok = False
                print(f"  Missing required facet in evidence: {min_facet}")

        if retrieval_ok:
            print("  Retrieval Status: PASS (all required facet provisions retrieved)")
            passed_retrieval += 1
        else:
            print("  Retrieval Status: PARTIAL / MISSING PROVISIONS")

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print(f"Facet Analysis Accuracy: {passed_analysis}/{total} ({passed_analysis/total*100:.1f}%)")
    print(f"Facet Evidence Retrieval: {passed_retrieval}/{total} ({passed_retrieval/total*100:.1f}%)")
    print("=" * 80)

    return passed_analysis == total and passed_retrieval == total


if __name__ == "__main__":
    success = run_facet_evaluation()
    sys.exit(0 if success else 1)
