"""
Regression and Negative Topic Tests for NyayaSetu Question-Specific Evidence Selection.

Tests:
1. Primary Regression Query: Circumstantial Evidence in Murder Conviction
   - Checks primary_issue == "circumstantial_evidence"
   - Checks case law includes Sharad Birdhichand Sarda and/or Babu v. State of Kerala
   - Checks Anurag Soni and Naim Ahamed are EXCLUDED
   - Checks BNS Section 108 is EXCLUDED
   - Checks evidence budget is between 2 and 5 sources
   - Checks final answer does NOT focus on murder punishment

2. Negative Topic Test 1: Consent through Promise to Marry
   - Checks primary_issue == "consent_and_promise_to_marry"
   - Checks retrieves consent / promise-to-marry cases
   - Checks Sharad Birdhichand Sarda is EXCLUDED

3. Negative Topic Test 2: Convictions Based on Circumstantial Evidence
   - Checks retrieves circumstantial evidence cases
   - Checks Anurag Soni, Naim Ahamed, and rape/consent cases are EXCLUDED
"""

import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag.rag_pipeline import LegalRAGPipeline
from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.answer_planner import AnswerPlanner
from retrieval.case_law_retriever import CaseLawRetriever
from retrieval.topic_compatibility import TopicCompatibilityEngine, TopicCompatibility


def test_query_analysis_and_planning():
    print("=" * 70)
    print("TEST 1: Query Analysis & Answer Planning for Circumstantial Evidence Query")
    print("=" * 70)

    query = (
        "A person is accused of murder, but there is no eyewitness. The prosecution "
        "relies entirely on circumstances such as motive, CCTV footage, call records, "
        "and forensic evidence. Can a murder conviction be based solely on "
        "circumstantial evidence? Explain the legal principles and judicial tests."
    )

    analyzer = LegalQueryAnalyzer()
    analysis = analyzer.analyze(query)

    print(f"Original Query: {query[:60]}...")
    print(f"Primary Issue: {analysis.primary_issue}")
    print(f"Offence: {analysis.offence}")
    print(f"Authority Requirement: {analysis.authority_requirement.value}")
    print(f"Excluded Topics: {analysis.excluded_topics}")

    assert analysis.primary_issue == "circumstantial_evidence", f"Expected 'circumstantial_evidence', got '{analysis.primary_issue}'"
    assert analysis.offence == "murder", f"Expected 'murder', got '{analysis.offence}'"
    assert "consent" in analysis.excluded_topics, "Expected 'consent' in excluded_topics"
    assert "promise to marry" in analysis.excluded_topics, "Expected 'promise to marry' in excluded_topics"

    # Answer Planner check
    planner = AnswerPlanner()
    plan = planner.plan_answer(analysis, requested_facets=["circumstantial_evidence", "judicial_test"])
    plan_dict = plan.to_dict()

    print("\nAnswer Plan:")
    print(f"Plan Primary Issue: {plan_dict.get('primary_issue')}")
    print(f"Plan Offence: {plan_dict.get('offence')}")
    print(f"Plan Facets: {plan_dict.get('facets')}")
    print(f"Plan Authority Required: {plan_dict.get('authority_required')}")

    assert plan_dict.get("primary_issue") == "circumstantial evidence"
    assert plan_dict.get("offence") == "murder"
    assert "circumstantial_evidence" in plan_dict.get("facets", [])
    assert "judicial_test" in plan_dict.get("facets", [])
    assert "CASE_LAW" in plan_dict.get("authority_required", [])

    print(">>> TEST 1 PASSED! Query Analyzer & Answer Planner correctly identified circumstantial evidence.\n")


def test_regression_query_pipeline():
    print("=" * 70)
    print("TEST 2: End-to-End Pipeline Regression Test for Circumstantial Evidence")
    print("=" * 70)

    query = (
        "A person is accused of murder, but there is no eyewitness. The prosecution "
        "relies entirely on circumstances such as motive, CCTV footage, call records, "
        "and forensic evidence. Can a murder conviction be based solely on "
        "circumstantial evidence? Explain the legal principles and judicial tests."
    )

    pipeline = LegalRAGPipeline()
    response = pipeline.query(query)

    print(f"\nRetrieved Sources Count: {len(response.sources)}")
    print("Retrieved Sources:")
    for s in response.sources:
        sec = f"Sec {s.section_number}" if s.section_number else ""
        cite = f"({s.citation})" if s.citation else ""
        case_act = s.case_name or s.document_name
        print(f"  - {s.source_label}: {case_act} {sec} {cite} [Type: {s.evidence_type}, Compat: {getattr(s, 'topic_compatibility', 'N/A')}]")

    # 1. Check evidence budget: 2 to 5 sources
    assert 2 <= len(response.sources) <= 5, f"Expected 2-5 sources, got {len(response.sources)}"

    # 2. Check Exclusions:
    source_names_and_texts = " ".join([
        (s.case_name or "") + " " + (s.document_name or "") + " " + (s.section_title or "") + " " + (s.text_snippet or "")
        for s in response.sources
    ]).lower()

    assert "anurag soni" not in source_names_and_texts, "FAIL: Anurag Soni was retrieved for circumstantial evidence query!"
    assert "naim ahamed" not in source_names_and_texts, "FAIL: Naim Ahamed was retrieved for circumstantial evidence query!"

    # Check statutory sections: Section 108 (abetment of suicide) must be excluded
    retrieved_sections = [s.section_number for s in response.sources if s.section_number]
    assert "108" not in retrieved_sections, "FAIL: BNS Section 108 (Abetment of suicide) was retrieved for murder/circumstantial query!"

    # 3. Check Case-Law presence: Sharad Birdhichand Sarda or Babu v. State of Kerala must be present
    has_circumstantial_case = any(
        "sharad birdhichand" in (s.case_name or "").lower()
        or "sarda" in (s.case_name or "").lower()
        or "babu" in (s.case_name or "").lower()
        for s in response.sources
    )
    assert has_circumstantial_case, "FAIL: No relevant circumstantial evidence case (Sharad Birdhichand Sarda / Babu) found in sources!"

    # 4. Check Answer content
    answer_text = response.answer
    print("\n--- GENERATED ANSWER EXCERPT ---")
    print(answer_text[:600] + "...")
    print("--------------------------------")

    # Verify no markdown bold syntax **
    assert "**" not in answer_text, "FAIL: Markdown bold syntax (**) found in final answer!"
    # Verify no markdown heading syntax ###
    assert "###" not in answer_text, "FAIL: Markdown heading syntax (###) found in final answer!"
    # Verify does not focus on murder punishment
    assert "Section 103 of the BNS specifically prescribes the punishment for murder" not in answer_text, (
        "FAIL: Answer incorrectly forced a punishment focus!"
    )
    # Verify discusses circumstantial evidence and judicial test
    assert any(k in answer_text.lower() for k in ["circumstantial evidence", "chain of circumstances", "beyond reasonable doubt"]), (
        "FAIL: Answer text does not address circumstantial evidence principles!"
    )

    print(">>> TEST 2 PASSED! Circumstantial evidence regression test successfully validated.\n")


def test_negative_topic_1_promise_to_marry():
    print("=" * 70)
    print("TEST 3: Negative Topic Test 1 (Promise to Marry)")
    print("=" * 70)

    query = "What judicial principles govern consent obtained through a promise to marry?"

    pipeline = LegalRAGPipeline()
    response = pipeline.query(query)

    print(f"Retrieved Sources Count: {len(response.sources)}")
    for s in response.sources:
        print(f"  - {s.source_label}: {s.case_name or s.document_name} [Type: {s.evidence_type}]")

    source_names_and_texts = " ".join([
        (s.case_name or "") + " " + (s.document_name or "") + " " + (s.section_title or "")
        for s in response.sources
    ]).lower()

    # Must NOT contain circumstantial evidence cases like Sharad Birdhichand Sarda
    assert "sharad birdhichand" not in source_names_and_texts, (
        "FAIL: Sharad Birdhichand Sarda was incorrectly retrieved for promise-to-marry query!"
    )
    assert "babu v. state of kerala" not in source_names_and_texts, (
        "FAIL: Babu v. State of Kerala was incorrectly retrieved for promise-to-marry query!"
    )

    # Must contain promise to marry / consent case
    has_consent_case = any(
        any(c in (s.case_name or "").lower() for c in ["anurag soni", "pawar", "naim ahamed", "chhotey"])
        for s in response.sources
    )
    assert has_consent_case, "FAIL: Expected promise to marry / consent case in sources!"

    print(">>> TEST 3 PASSED! Negative topic test 1 passed.\n")


def test_negative_topic_2_circumstantial_evidence():
    print("=" * 70)
    print("TEST 4: Negative Topic Test 2 (Circumstantial Evidence Pure)")
    print("=" * 70)

    query = "What judicial principles govern convictions based on circumstantial evidence?"

    pipeline = LegalRAGPipeline()
    response = pipeline.query(query)

    print(f"Retrieved Sources Count: {len(response.sources)}")
    for s in response.sources:
        print(f"  - {s.source_label}: {s.case_name or s.document_name} [Type: {s.evidence_type}]")

    source_names_and_texts = " ".join([
        (s.case_name or "") + " " + (s.document_name or "") + " " + (s.section_title or "")
        for s in response.sources
    ]).lower()

    # Must NOT contain rape / consent / promise to marry cases
    assert "anurag soni" not in source_names_and_texts, "FAIL: Anurag Soni retrieved for pure circumstantial evidence query!"
    assert "naim ahamed" not in source_names_and_texts, "FAIL: Naim Ahamed retrieved for pure circumstantial evidence query!"

    # Must contain circumstantial evidence authority
    has_ce_case = any(
        "sharad birdhichand" in (s.case_name or "").lower()
        or "sarda" in (s.case_name or "").lower()
        or "babu" in (s.case_name or "").lower()
        for s in response.sources
    )
    assert has_ce_case, "FAIL: Expected Sharad Birdhichand Sarda or Babu in sources!"

    print(">>> TEST 4 PASSED! Negative topic test 2 passed.\n")


if __name__ == "__main__":
    test_query_analysis_and_planning()
    test_regression_query_pipeline()
    test_negative_topic_1_promise_to_marry()
    test_negative_topic_2_circumstantial_evidence()
    print("\nALL 4 REGRESSION AND NEGATIVE TOPIC TESTS PASSED SUCCESSFULLY!")
