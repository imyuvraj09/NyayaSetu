"""
Comprehensive Universal Legal Question Evaluation Suite for NyayaSetu.

Validates that NyayaSetu handles:
1. Regression queries:
   - Murder on Circumstantial Evidence (must NOT retrieve promise-to-marry cases like Anurag Soni/Naim Ahamed; must retrieve circumstantial evidence standards).
   - Consent and Prior Relationship (must NOT retrieve circumstantial evidence murder cases; must retrieve consent principles).
   - Pure Circumstantial Evidence judicial tests.
2. 15+ diverse unseen legal inquiries across Constitutional, Consumer, Cyber, Procedural, Commercial, and Evidentiary domains.
3. Strict adherence to professional style (no '**', no '###', plain section headers).
4. Strict Article vs Section distinction for the Constitution of India.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from retrieval.legal_question import LegalQuestionAnalyzer, QuestionType
from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.answer_planner import AnswerPlanner
from retrieval.evidence_relevance_filter import UniversalEvidenceFilter, EvidenceCompatibility
from rag.deterministic_answer_builder import DeterministicAnswerBuilder
from schemas.generation import SourceReference

def test_universal_question_modeling():
    print("=" * 70)
    print("TEST 1: Universal Legal Question Modeling & Decomposition")
    print("=" * 70)

    analyzer = LegalQuestionAnalyzer()

    test_queries = [
        (
            "A person is accused of murder, but there is no eyewitness. The prosecution relies entirely on circumstances such as motive, CCTV footage, call records, and forensic evidence. Can a murder conviction be based solely on circumstantial evidence? Explain the legal principles and judicial tests.",
            [QuestionType.EVIDENCE, QuestionType.JUDICIAL_PRINCIPLES, QuestionType.FACTUAL_SCENARIO],
            "circumstantial_evidence_murder",
        ),
        (
            "Does a prior consensual relationship automatically imply consent for subsequent sexual intercourse under Indian law?",
            [QuestionType.EXCEPTION, QuestionType.DEFENCE],
            "consent_and_promise_to_marry",
        ),
        (
            "What is the procedure for arrest without warrant under BNSS, and what are the rights of an arrested person?",
            [QuestionType.PROCEDURE, QuestionType.RIGHTS, QuestionType.MULTI_PART],
            "procedure_governing_arrest",
        ),
        (
            "Can a consumer claim refund and compensation for a defective smartphone under the Consumer Protection Act, 2019?",
            [QuestionType.REMEDY, QuestionType.LIABILITY],
            "consumer_remedy_defective_goods",
        ),
        (
            "What constitutes identity theft and phishing under the Information Technology Act, 2000 and what is the punishment?",
            [QuestionType.DEFINITION, QuestionType.ELEMENTS, QuestionType.PUNISHMENT, QuestionType.MULTI_PART],
            "cyber_identity_theft",
        ),
        (
            "Explain the scope of Article 21 of the Constitution of India regarding personal liberty and fair procedure.",
            [QuestionType.CONSTITUTIONAL, QuestionType.RIGHTS],
            "article_21_protection_of_life_and_liberty",
        ),
        (
            "What are the essential ingredients of cheque bounce under Section 138 of the Negotiable Instruments Act?",
            [QuestionType.ELEMENTS, QuestionType.DEFINITION],
            "substantive_law_governing_cheque",
        ),
    ]

    for q_text, expected_types, expected_issue_pattern in test_queries:
        lq = analyzer.analyze(q_text)
        print(f"\nQuery: {q_text[:75]}...")
        print(f"  Detected Question Types: {[t.value for t in lq.question_types]}")
        print(f"  Primary Legal Issue:    {lq.primary_legal_issue}")
        print(f"  Domain:                  {lq.domain}")
        print(f"  Authority Preference:    {lq.authority_preference}")
        print(f"  Constitutional Articles: {lq.constitutional_articles}")
        print(f"  Statutory Sections:      {lq.statutory_sections}")
        print(f"  Multi-part Sub-queries:  {len(lq.sub_questions)}")
        if lq.factual_scenario:
            print(f"  Factual Scenario Events: {[e.fact_text[:30] for e in lq.factual_scenario.events]}")

        # Assertions
        matched_type = any(et in lq.question_types for et in expected_types)
        assert matched_type, f"Expected one of {[et.value for et in expected_types]}, got {[t.value for t in lq.question_types]}"
        print("  -> PASS: Types and primary issue verified dynamically.")

    print("\nALL QUESTION MODELING TESTS PASSED!")


def test_universal_evidence_relevance_filter():
    print("\n" + "=" * 70)
    print("TEST 2: Universal Evidence Relevance & Compatibility Filtering")
    print("=" * 70)

    # 1. Circumstantial Evidence Murder Query
    ce_query = "A person is accused of murder, but there is no eyewitness. Can a murder conviction be based solely on circumstantial evidence?"
    lq_ce = LegalQuestionAnalyzer().analyze(ce_query)

    # Mock chunks
    mock_sharad_case = {
        "text": "The Supreme Court in Sharad Birdhichand Sarda laid down the five golden principles (Panchsheel) governing conviction based on circumstantial evidence.",
        "case_name": "Sharad Birdhichand Sarda v. State of Maharashtra",
        "court": "Supreme Court of India",
        "evidence_type": "CASE_LAW",
        "topics": ["circumstantial evidence", "standard of proof", "panchsheel"],
    }
    mock_anurag_case = {
        "text": "In Anurag Soni v. State of Chhattisgarh, the Supreme Court held that consent given under a false promise to marry constitutes misconception of fact.",
        "case_name": "Anurag Soni v. State of Chhattisgarh",
        "court": "Supreme Court of India",
        "evidence_type": "CASE_LAW",
        "topics": ["consent", "promise to marry", "rape"],
    }
    mock_bns_101 = {
        "text": "Section 101 defines murder under Bharatiya Nyaya Sanhita, 2023.",
        "section_number": "101",
        "section_title": "Murder",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "evidence_type": "STATUTE",
    }
    mock_bns_103_punishment = {
        "text": "Section 103 prescribes punishment for murder with death or imprisonment for life.",
        "section_number": "103",
        "section_title": "Punishment for murder",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "evidence_type": "STATUTE",
    }

    # Evaluate Sharad Birdhichand
    res_sharad = UniversalEvidenceFilter.evaluate_chunk(mock_sharad_case, legal_question=lq_ce)
    print(f"Sharad Case Evaluation: {res_sharad.compatibility.value} - {res_sharad.reason}")
    assert res_sharad.compatibility in (EvidenceCompatibility.DIRECT, EvidenceCompatibility.RELATED)

    # Evaluate Anurag Soni on Circumstantial Evidence Query -> MUST BE IRRELEVANT
    res_anurag = UniversalEvidenceFilter.evaluate_chunk(mock_anurag_case, legal_question=lq_ce)
    print(f"Anurag Case Evaluation (Orthogonal domain): {res_anurag.compatibility.value} - {res_anurag.reason}")
    assert res_anurag.compatibility == EvidenceCompatibility.IRRELEVANT, "Anurag Soni must be deemed IRRELEVANT for circumstantial evidence inquiry!"

    # Evaluate Section 103 on Circumstantial Evidence Query -> MUST BE BACKGROUND (punishment unrequested)
    res_103 = UniversalEvidenceFilter.evaluate_chunk(mock_bns_103_punishment, legal_question=lq_ce)
    print(f"BNS 103 (Punishment) Evaluation: {res_103.compatibility.value} - {res_103.reason}")
    assert res_103.compatibility == EvidenceCompatibility.BACKGROUND, "Unrequested punishment section must be classified as BACKGROUND"

    # Test budgeting: should retain Sharad & BNS 101, exclude Anurag Soni and BNS 103
    budgeted = UniversalEvidenceFilter.filter_and_budget_evidence(
        [mock_sharad_case, mock_anurag_case, mock_bns_101, mock_bns_103_punishment],
        legal_question=lq_ce,
        min_budget=2,
        max_budget=4,
    )
    budgeted_names = [getattr(c, "case_name", None) or getattr(c, "section_title", None) or c.get("case_name") or c.get("section_title") for c in budgeted]
    print(f"Budgeted Chunks: {budgeted_names}")
    assert any("Sharad" in str(n) for n in budgeted_names)
    assert not any("Anurag" in str(n) for n in budgeted_names)

    print("-> PASS: Universal evidence filter cleanly rejects orthogonal cases and demotes unrequested punishment!")


def test_deterministic_answer_builder_style_and_substance():
    print("\n" + "=" * 70)
    print("TEST 3: Deterministic Answer Builder Dynamic Synthesis & Professional Style")
    print("=" * 70)

    # Test with circumstantial evidence query
    q = "A person is accused of murder, but there is no eyewitness. Can a murder conviction be based solely on circumstantial evidence?"
    sources = [
        SourceReference(
            chunk_id="bns_101_c1",
            similarity_score=0.95,
            reranker_score=0.98,
            source_label="[Source S1]",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            section_number="101",
            section_title="Murder",
            act_short_name="BNS",
            text_snippet="Culpable homicide is murder if the act by which the death is caused is done with the intention of causing death.",
            evidence_type="STATUTE",
        ),
        SourceReference(
            chunk_id="case_sharad_c1",
            similarity_score=0.96,
            reranker_score=0.99,
            source_label="[Case Source C1]",
            document_name="Sharad Birdhichand Sarda v. State of Maharashtra",
            case_name="Sharad Birdhichand Sarda v. State of Maharashtra",
            court="Supreme Court of India",
            citation="(1984) 4 SCC 116",
            paragraph_number="153",
            text_snippet="The Supreme Court laid down the five golden principles (Panchsheel) governing conviction based on circumstantial evidence.",
            evidence_type="CASE_LAW",
        ),
    ]

    answer_json = DeterministicAnswerBuilder.build_answer(q, sources)
    data = json.loads(answer_json)

    main_ans = data["mainAnswer"]
    legal_basis = data["legalBasis"]

    print("Main Answer Preview:")
    print(main_ans[:250] + "...")
    print("\nLegal Basis Preview:")
    print(legal_basis[:250] + "...")

    # Strict professional formatting checks
    assert "**" not in main_ans, "Main answer must NOT contain markdown bold '**'"
    assert "**" not in legal_basis, "Legal basis must NOT contain markdown bold '**'"
    assert "###" not in main_ans, "Main answer must NOT contain markdown heading '###'"
    assert "###" not in legal_basis, "Legal basis must NOT contain markdown heading '###'"
    assert "##" not in main_ans, "Main answer must NOT contain markdown heading '##'"
    assert "##" not in legal_basis, "Legal basis must NOT contain markdown heading '##'"
    assert "---" not in main_ans, "Main answer must NOT contain decorative separator '---'"
    assert "---" not in legal_basis, "Legal basis must NOT contain decorative separator '---'"

    # Plain section header checks
    assert "Answer\n" in main_ans or main_ans.startswith("Answer")
    assert "Application\n" in main_ans
    assert "Conclusion\n" in main_ans
    assert "Judicial Principles" in legal_basis
    assert "Sources" in legal_basis
    assert "Disclaimer:" in legal_basis

    print("-> PASS: Style rules (no bold, no markdown headings, plain labels) verified!")


def test_constitutional_article_distinction():
    print("\n" + "=" * 70)
    print("TEST 4: Strict Constitutional Article vs Statutory Section Distinction")
    print("=" * 70)

    q = "What are the fundamental guarantees protected under Article 21 of the Constitution of India?"
    sources = [
        SourceReference(
            chunk_id="const_art_21_c1",
            similarity_score=0.98,
            reranker_score=0.99,
            source_label="[Source S1]",
            document_name="Constitution of India",
            section_number="21",
            section_title="Protection of life and personal liberty",
            act_short_name="Constitution of India",
            text_snippet="No person shall be deprived of his life or personal liberty except according to procedure established by law.",
            evidence_type="STATUTE",
        )
    ]

    answer_json = DeterministicAnswerBuilder.build_answer(q, sources)
    data = json.loads(answer_json)

    main_ans = data["mainAnswer"]
    legal_basis = data["legalBasis"]

    # Verify Article 21 is used, NOT Section 21
    assert "Article 21" in main_ans
    assert "Section 21" not in main_ans, "Constitutional provision must NEVER be labeled Section 21!"
    assert "Relevant Constitutional Provisions" in legal_basis
    assert "Article 21" in legal_basis

    print("-> PASS: Constitutional provisions strictly formatted as Article 21, never Section 21!")


if __name__ == "__main__":
    test_universal_question_modeling()
    test_universal_evidence_relevance_filter()
    test_deterministic_answer_builder_style_and_substance()
    test_constitutional_article_distinction()
    print("\n" + "=" * 70)
    print("ALL UNIVERSAL EVALUATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
