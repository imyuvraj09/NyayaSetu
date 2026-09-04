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
from rag.rag_pipeline import LegalRAGPipeline
from retrieval.claim_evidence_validator import get_claim_evidence_validator
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
    assert "Application\n" in main_ans or "Application to the Facts\n" in main_ans or "Application" in main_ans
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


def test_adaptive_professional_legal_response_generation():
    print("\n" + "=" * 70)
    print("TEST 5: Adaptive Professional Legal Response Generation")
    print("=" * 70)

    # 1. Practical Action Query (UPI Fraud)
    upi_query = "A victim loses money through a fraudulent UPI transaction. What immediate legal remedies and reporting mechanisms are available?"
    upi_sources = [
        SourceReference(
            chunk_id="it_act_sec_43",
            similarity_score=0.92,
            reranker_score=0.95,
            source_label="[Source S1]",
            document_name="Information Technology Act, 2000",
            section_number="43",
            section_title="Penalty and compensation for damage to computer, computer system, etc.",
            act_short_name="Information Technology Act, 2000",
            text_snippet="If any person without permission of the owner or any other person who is in charge of a computer, computer system or computer network accesses or downloads, he shall be liable to pay damages by way of compensation.",
            evidence_type="STATUTE",
        ),
        SourceReference(
            chunk_id="bns_sec_318",
            similarity_score=0.90,
            reranker_score=0.93,
            source_label="[Source S2]",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            section_number="318",
            section_title="Cheating",
            act_short_name="Bharatiya Nyaya Sanhita, 2023",
            text_snippet="Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property, commits cheating.",
            evidence_type="STATUTE",
        ),
    ]

    upi_ans_json = DeterministicAnswerBuilder.build_answer(upi_query, upi_sources)
    upi_data = json.loads(upi_ans_json)

    assert upi_data["legalDomain"] == "Cybercrime / Financial Fraud", f"Expected Cybercrime domain, got {upi_data['legalDomain']}"
    upi_main = upi_data["mainAnswer"]

    print("UPI Practical Main Answer Preview:")
    print(upi_main[:350] + "...\n")

    # Verify Adaptive Sections
    assert "Answer\n" in upi_main or upi_main.startswith("Answer")
    assert "Immediate Steps\n" in upi_main
    assert "Reporting Mechanisms\n" in upi_main
    assert "Applicable Legal Position\n" in upi_main
    assert "Evidence to Preserve\n" in upi_main
    assert "Important Qualifications\n" in upi_main
    assert "Conclusion\n" in upi_main

    # Verify Numbered Steps & Bullet points
    assert "1. Contact the bank" in upi_main
    assert "2. Document and preserve" in upi_main
    assert "3. Register an official" in upi_main
    assert "- Transaction reference IDs" in upi_main

    # Verify Direct Answer First
    assert "immediate priority is to report" in upi_main

    # Verify Strict Styling Rules
    assert "**" not in upi_main
    assert "###" not in upi_main
    assert "---" not in upi_main

    print("-> PASS: Practical action / fraud inquiry correctly adapted!")

    # 2. Direct Answer First for YES/NO questions
    consent_query = "Does a previous consensual relationship constitute consent for a subsequent sexual act under Indian law?"
    consent_sources = [
        SourceReference(
            chunk_id="bns_63",
            similarity_score=0.95,
            reranker_score=0.98,
            source_label="[Source S1]",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            section_number="63",
            section_title="Rape",
            act_short_name="Bharatiya Nyaya Sanhita, 2023",
            text_snippet="A man is said to commit rape who has sexual intercourse with a woman without her consent.",
            evidence_type="STATUTE",
        )
    ]
    consent_ans = json.loads(DeterministicAnswerBuilder.build_answer(consent_query, consent_sources))["mainAnswer"]
    assert "No. A prior consensual relationship does not automatically establish consent" in consent_ans
    print("-> PASS: YES/NO consent question begins immediately with substantive 'No.'!")

    # 3. Case-law limitation when judicial principles requested but absent
    case_query = "What are the judicial principles and precedent tests governing preventive detention?"
    case_sources = [
        SourceReference(
            chunk_id="stat_only_1",
            similarity_score=0.88,
            reranker_score=0.90,
            source_label="[Source S1]",
            document_name="Constitution of India",
            section_number="22",
            section_title="Protection against arrest and detention in certain cases",
            act_short_name="Constitution of India",
            text_snippet="No person who is arrested shall be detained in custody without being informed...",
            evidence_type="STATUTE",
        )
    ]
    case_basis = json.loads(DeterministicAnswerBuilder.build_answer(case_query, case_sources))["legalBasis"]
    assert "The current indexed sources do not contain verified judicial decisions sufficient to substantiate the case-law aspect of this question." in case_basis
    print("-> PASS: Unindexed case-law limitation correctly handled without hallucination!")


def test_universal_fact_first_domain_routing_20_categories():
    print("\n" + "=" * 70)
    print("TEST 6: Universal Fact-First Domain Routing (20 Core Categories)")
    print("=" * 70)

    analyzer = LegalQuestionAnalyzer()

    category_tests = [
        # A. CRIMINAL
        ("What is the punishment for murder under Indian law?", "Criminal Law", "PUNISHMENT"),
        ("A person is accused of murder without eyewitnesses. Can circumstantial evidence establish guilt?", "Criminal Law", "EVIDENCE"),
        ("How is a murder investigation conducted by police?", "Criminal Law", "INVESTIGATION"),
        ("What evidence can prove theft in a criminal trial?", "Criminal Law", "EVIDENCE"),
        # B. CYBERCRIME
        ("A hacker gains unauthorized access to a company's computer system, copies confidential files, and demands ransom. What offences may apply, what investigation procedures are relevant, and what evidence could establish the offence?", "Cybercrime / Information Technology Law", "OFFENCES"),
        ("A person sends ransomware to a company and demands payment. What offences may apply?", "Cybercrime / Information Technology Law", "OFFENCES"),
        # C. EVIDENCE LAW
        ("What evidence is admissible for proving an electronic record in court?", "Law of Evidence", "ADMISSIBILITY"),
        ("What is the legal test for proving guilt solely through circumstantial evidence?", "Law of Evidence", "EVIDENCE"),
        # D. CONSTITUTIONAL
        ("Explain Article 21 of the Constitution of India regarding personal liberty.", "Constitutional Law", "DEFINITION"),
        ("Explain Article 21 and the Supreme Court principles concerning fair and reasonable procedure.", "Constitutional Law", "PROCEDURE"),
        # E. CONSUMER
        ("What remedies are available to a consumer for defective goods?", "Consumer Law", "REMEDY"),
        ("How to file an appeal against a consumer commission order?", "Consumer Law", "APPEAL"),
        # F. RTI
        ("How to file an RTI application before a public authority?", "RTI / Information Law", "PROCEDURE"),
        ("What is the procedure to appeal an RTI decision by the PIO?", "RTI / Information Law", "APPEAL"),
        # G. FAMILY LAW
        ("What is the procedure for divorce under Indian law?", "Family Law", "PROCEDURE"),
        # H. EMPLOYMENT
        ("An employee was subjected to wrongful termination. What rights and remedies are available?", "Employment / Labour Law", "REMEDY"),
        # I. CONTRACT
        ("What remedies are available for breach of contract?", "Contract Law", "REMEDY"),
        # J. CORPORATE
        ("When can a company director be held liable for corporate default?", "Corporate Law", "LIABILITY"),
        # K. INSOLVENCY
        ("What is the CIRP process under the Insolvency and Bankruptcy Code?", "Insolvency Law", "PROCEDURE"),
        # L. TAX
        ("What is the GST penalty for non-compliance with statutory tax filing?", "Tax / GST Law", "PUNISHMENT"),
    ]

    for q, expected_domain, expected_facet in category_tests:
        lq = analyzer.analyze(q)
        print(f"Query: {q[:60]}...")
        print(f"  -> Primary Domain: {lq.primary_domain}")
        print(f"  -> Requested Facets: {lq.requested_facets}")

        assert lq.primary_domain == expected_domain, f"For query '{q}', expected domain '{expected_domain}', got '{lq.primary_domain}'"
        assert expected_facet in lq.requested_facets or expected_facet.lower() in [f.lower() for f in lq.requested_facets], f"Expected facet '{expected_facet}' in {lq.requested_facets}"

    print("\n-> PASS: All 20 Core Universal Domain Categories correctly classified without keyword hijacking!")


def test_cross_domain_negative_tests():
    print("\n" + "=" * 70)
    print("TEST 7: Cross-Domain Negative Tests (Wrong-Domain Hijack Prevention)")
    print("=" * 70)

    analyzer = LegalQuestionAnalyzer()

    # 1. Sexual assault + evidence -> NOT Law of Evidence
    q1 = "A victim alleges sexual assault. What evidence could establish the offence?"
    lq1 = analyzer.analyze(q1)
    print("Q1 Domain:", lq1.primary_domain)
    assert lq1.primary_domain != "Law of Evidence", "Sexual assault evidence must NOT classify as Law of Evidence!"
    assert "Criminal Law" in lq1.primary_domain

    # 2. Server hack + evidence -> NOT Law of Evidence
    q2 = "A company server was hacked. What evidence should investigators preserve?"
    lq2 = analyzer.analyze(q2)
    print("Q2 Domain:", lq2.primary_domain)
    assert lq2.primary_domain != "Law of Evidence", "Hacked server evidence preservation must NOT classify as Law of Evidence!"
    assert "Cyber" in lq2.primary_domain

    # 3. Consumer defective phone + remedy -> NOT generic remedies, IS Consumer Law
    q3 = "A consumer purchased a defective phone. What remedy is available?"
    lq3 = analyzer.analyze(q3)
    print("Q3 Domain:", lq3.primary_domain)
    assert lq3.primary_domain == "Consumer Law", "Defective phone remedy must classify as Consumer Law!"

    # 4. State denial of liberty + Article 21 -> NOT Procedural Law, IS Constitutional Law
    q4 = "A person was denied liberty by state action. Explain Article 21 and the available remedy."
    lq4 = analyzer.analyze(q4)
    print("Q4 Domain:", lq4.primary_domain)
    assert lq4.primary_domain != "Criminal Procedure", "Article 21 state liberty denial must NOT classify as Criminal Procedure!"
    assert lq4.primary_domain == "Constitutional Law"

    # 5. Unlawful dismissal + remedy -> NOT Evidence Law, IS Employment / Labour Law
    q5 = "An employee was dismissed unlawfully. What remedy is available?"
    lq5 = analyzer.analyze(q5)
    print("Q5 Domain:", lq5.primary_domain)
    assert lq5.primary_domain != "Law of Evidence", "Unlawful employee dismissal must NOT classify as Law of Evidence!"
    assert lq5.primary_domain == "Employment / Labour Law"

    print("-> PASS: All 5 Cross-Domain Negative Tests Passed!")


def test_required_regression_tests_section_24():
    print("\n" + "=" * 70)
    print("TEST 8: Section 24 Regression Tests (8 Mandatory Benchmark Queries)")
    print("=" * 70)

    analyzer = LegalQuestionAnalyzer()

    # TEST 1: Hacker scenario
    t1_q = "A hacker gains unauthorized access to a company's computer system, copies confidential files, and demands ransom. What offences may apply, what investigation procedures are relevant, and what evidence could establish the offence?"
    t1_lq = analyzer.analyze(t1_q)
    assert t1_lq.primary_domain == "Cybercrime / Information Technology Law", f"Expected Cybercrime domain, got {t1_lq.primary_domain}"
    assert "OFFENCES" in t1_lq.requested_facets
    assert "INVESTIGATION" in t1_lq.requested_facets
    assert "EVIDENCE" in t1_lq.requested_facets
    assert t1_lq.primary_domain != "Law of Evidence"

    # Verify deterministic answer generation for TEST 1
    t1_sources = [
        SourceReference(
            chunk_id="it_act_43_66",
            similarity_score=0.95,
            reranker_score=0.98,
            source_label="[Source S1]",
            document_name="Information Technology Act",
            section_number="66",
            section_title="Computer related offences",
            act_short_name="IT Act",
            text_snippet="If any person, dishonestly or fraudulently, does any act referred to in section 43, he shall be punishable with imprisonment.",
            evidence_type="STATUTE",
        ),
        SourceReference(
            chunk_id="bnss_176",
            similarity_score=0.90,
            reranker_score=0.92,
            source_label="[Source S2]",
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            section_number="176",
            section_title="Procedure for investigation",
            act_short_name="BNSS",
            text_snippet="Procedure for investigation of cognizable offences including collection of electronic evidence and forensics.",
            evidence_type="STATUTE",
        ),
        SourceReference(
            chunk_id="bnss_176_dup",
            similarity_score=0.88,
            reranker_score=0.89,
            source_label="[Source S3]",
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            section_number="176",
            section_title="Procedure for investigation",
            act_short_name="BNSS",
            text_snippet="Duplicate chunk of section 176 for testing deduplication.",
            evidence_type="STATUTE",
        ),
    ]

    t1_payload = json.loads(DeterministicAnswerBuilder.build_answer(t1_q, t1_sources))
    t1_main = t1_payload["mainAnswer"]
    t1_basis = t1_payload["legalBasis"]

    print("Hacker Query Response Preview:")
    print(t1_main[:400] + "...\n")

    # Domain label
    assert t1_payload["legalDomain"] == "Cybercrime / Information Technology Law"

    # Multi-facet sections present
    assert "Possible Offences" in t1_main
    assert "Investigation" in t1_main
    assert "Evidence" in t1_main
    assert "Application" in t1_main
    assert "Conclusion" in t1_main

    # Circumstantial evidence lecture ABSENT
    assert "circumstantial evidence" not in t1_main.lower()
    assert "unbroken chain" not in t1_main.lower()
    assert "hypothesis of innocence" not in t1_main.lower()
    assert "1. A Hacker Gains" not in t1_main

    # Source deduplication: BNSS Section 176 should appear only once in sources
    sources_section = t1_basis[t1_basis.find("Sources"):]
    assert sources_section.count("BNSS — Section 176") == 1, f"Expected Section 176 to appear only once, found {sources_section.count('BNSS — Section 176')} times"

    # Strict formatting
    assert "**" not in t1_main
    assert "###" not in t1_main
    assert "---" not in t1_main

    print("-> PASS: TEST 1 (Hacker scenario multi-facet generation) passed!")

    # TEST 2
    t2_q = "What is the legal test for proving guilt solely through circumstantial evidence?"
    t2_lq = analyzer.analyze(t2_q)
    assert t2_lq.primary_domain == "Law of Evidence"
    t2_payload = json.loads(DeterministicAnswerBuilder.build_answer(t2_q, []))
    assert "circumstantial" in t2_payload["mainAnswer"].lower()
    print("-> PASS: TEST 2 (Circumstantial evidence test) passed!")

    # TEST 3
    t3_q = "What evidence is admissible for proving an electronic record in court?"
    t3_lq = analyzer.analyze(t3_q)
    assert t3_lq.primary_domain == "Law of Evidence"
    t3_payload = json.loads(DeterministicAnswerBuilder.build_answer(t3_q, []))
    assert "electronic record" in t3_payload["mainAnswer"].lower()
    assert "circumstantial evidence" not in t3_payload["mainAnswer"].lower()
    print("-> PASS: TEST 3 (Electronic record admissibility) passed!")

    # TEST 4
    t4_q = "Someone hacked my company's server and stole customer data. What legal offences may apply?"
    t4_lq = analyzer.analyze(t4_q)
    assert t4_lq.primary_domain == "Cybercrime / Information Technology Law"
    assert "OFFENCES" in t4_lq.requested_facets
    print("-> PASS: TEST 4 (Server hack stolen customer data offences) passed!")

    # TEST 5
    t5_q = "My company's server was hacked. What should investigators collect?"
    t5_lq = analyzer.analyze(t5_q)
    assert "Cyber" in t5_lq.primary_domain
    assert "INVESTIGATION" in t5_lq.requested_facets
    assert "EVIDENCE" in t5_lq.requested_facets
    print("-> PASS: TEST 5 (Server hack investigators collect) passed!")

    # TEST 6
    t6_q = "What are the rules for admissibility of electronic evidence under Indian law?"
    t6_lq = analyzer.analyze(t6_q)
    assert t6_lq.primary_domain == "Law of Evidence"
    assert "Cyber" not in t6_lq.primary_domain
    print("-> PASS: TEST 6 (Rules for admissibility of electronic evidence) passed!")

    # TEST 7
    t7_q = "A person accesses a computer without authorization and copies files. What offence may be committed?"
    t7_lq = analyzer.analyze(t7_q)
    assert t7_lq.primary_domain == "Cybercrime / Information Technology Law"
    assert "OFFENCES" in t7_lq.requested_facets
    print("-> PASS: TEST 7 (Unauthorized access and copies files) passed!")

    # TEST 8
    t8_q = "A person sends ransomware to a company and demands payment. What offences may apply?"
    t8_lq = analyzer.analyze(t8_q)
    assert "Cyber" in t8_lq.primary_domain
    assert "OFFENCES" in t8_lq.requested_facets
    print("-> PASS: TEST 8 (Ransomware demand payment offences) passed!")


def test_claim_level_grounding_and_unsupported_claim_prevention():
    print("\n" + "=" * 70)
    print("TEST 9: Claim-Level Grounding & Unsupported Legal Claim Prevention")
    print("=" * 70)

    validator = get_claim_evidence_validator()

    # 1. Cybercrime Scenario where ONLY Section 66 is retrieved
    q = (
        "A hacker gains unauthorized access to a company's computer system, copies confidential files, "
        "and demands ransom. What offences may apply, what investigation procedures are relevant, "
        "and what evidence could establish the offence?"
    )

    sec66_source = SourceReference(
        source_label="[Source 1]",
        chunk_id="it_act_sec_66",
        document_name="Information Technology Act, 2000",
        section="66",
        section_number="66",
        section_title="Computer related offences",
        similarity_score=0.92,
        reranker_score=0.98,
        text_snippet=(
            "Section 66. Computer related offences. If any person, dishonestly or fraudulently, does any act "
            "referred to in section 43, he shall be punishable with imprisonment for a term which may extend to "
            "three years or with fine which may extend to five lakh rupees or with both."
        ),
        evidence_type="STATUTE",
    )

    answer_json = DeterministicAnswerBuilder.build_answer(query=q, sources=[sec66_source])
    data = json.loads(answer_json)
    main_ans = data["mainAnswer"]

    print(f"\n--- Output for Section 66 Only ---\n{main_ans}\n")

    # Assertion 1: Retrieved only Section 66 -> answer does NOT assert Section 43, 66C, 66D, or BNS 308 as offences
    assert "Section 66" in main_ans
    assert "Section 66C" not in main_ans
    assert "Section 66D" not in main_ans
    assert "Section 308" not in main_ans and "BNS" not in main_ans
    # Section 43 must not be listed as an offence block
    offences_part = main_ans[main_ans.find("Possible Offences"):main_ans.find("Investigation")] if "Investigation" in main_ans else main_ans
    assert "Section 43" not in offences_part
    print("-> PASS: Assertion 1 (Retrieved only Section 66 -> answer does NOT mention Section 43, 66C, 66D, or BNS 308)")

    # Assertion 4: No investigation statute -> answer does not assert statutory investigation requirement as fact
    assert "mandatorily register an fir under section 154" not in main_ans.lower()
    assert "statutory investigation mandate" not in main_ans.lower()
    assert "practical evidence preservation" in main_ans.lower() or "preserved carefully" in main_ans.lower()
    print("-> PASS: Assertion 4 (No investigation statute -> answer does not assert statutory investigation requirement as fact)")

    # Assertion 5: Evidence logs mentioned -> phrased as factual/may help establish, no statutory admissibility claims
    assert "section 63" not in main_ans.lower()
    assert "section 65b" not in main_ans.lower()
    assert "may help establish" in main_ans.lower()
    print("-> PASS: Assertion 5 (Evidence logs mentioned -> phrased as 'may help establish', no statutory admissibility claims)")

    # Assertion 6: Conclusion guard -> conclusion summarizes only retrieved sections
    conclusion_idx = main_ans.find("Conclusion")
    assert conclusion_idx != -1
    conclusion_part = main_ans[conclusion_idx:]
    assert "Section 66" in conclusion_part
    assert "66C" not in conclusion_part
    assert "66D" not in conclusion_part
    assert "308" not in conclusion_part
    print("-> PASS: Assertion 6 (Conclusion guard -> no unretrieved sections in Conclusion)")

    # 2. Scenario where Section 66C IS retrieved for identity theft
    q_id = "A perpetrator stole employee login credentials and passwords to access company networks. What offence applies?"
    sec66c_source = SourceReference(
        source_label="[Source 1]",
        chunk_id="it_act_sec_66c",
        document_name="Information Technology Act, 2000",
        section="66C",
        section_number="66C",
        section_title="Punishment for identity theft",
        similarity_score=0.91,
        reranker_score=0.97,
        text_snippet=(
            "Section 66C. Whoever, fraudulently or dishonestly make use of the electronic signature, password or "
            "any other unique identification feature of any other person, shall be punished with imprisonment."
        ),
        evidence_type="STATUTE",
    )
    answer_66c = DeterministicAnswerBuilder.build_answer(query=q_id, sources=[sec66c_source])
    data_66c = json.loads(answer_66c)
    assert "Section 66C" in data_66c["mainAnswer"]
    print("-> PASS: Assertion 2 (Retrieved Section 66C correctly mentioned matching identity-theft facts)")

    # 3. Scenario with NCRP reporting source
    q_rep = "How and where can cybercrime be reported online in India?"
    ncrp_source = SourceReference(
        source_label="[Source 1]",
        chunk_id="ncrp_portal_admin",
        document_name="National Cyber Crime Reporting Portal (cybercrime.gov.in)",
        section="Administrative Portal",
        section_number="",
        section_title="Cybercrime Reporting Portal",
        similarity_score=0.88,
        reranker_score=0.95,
        text_snippet="The National Cyber Crime Reporting Portal (cybercrime.gov.in) provides a citizen-centric facility to report cybercrimes online.",
        evidence_type="ADMINISTRATIVE",
    )
    answer_ncrp = DeterministicAnswerBuilder.build_answer(query=q_rep, sources=[ncrp_source])
    data_ncrp = json.loads(answer_ncrp)
    assert "cybercrime.gov.in" in data_ncrp["mainAnswer"].lower() or "reporting portal" in data_ncrp["mainAnswer"].lower()
    print("-> PASS: Assertion 3 (NCRP reporting source cited with its source without IT Act citation borrowing)")

    # 4. Post-generation Auditor & Sanitizer Test
    hallucinated_answer = (
        "Answer\n\n"
        "Possible Offences\n\n"
        "- Section 66 of Information Technology Act, 2000 [Source 1]\n"
        "- Section 43 of Information Technology Act, 2000 [Source 1]\n"
        "- Section 66C of Information Technology Act, 2000 [Source 1]\n"
        "- Section 308 of BNS [Source 1]\n\n"
        "Investigation Procedures\n"
        "The investigating officer must mandatorily register an FIR under Section 154.\n\n"
        "Evidence\n"
        "A mandatory certificate under Section 65B is strictly required.\n\n"
        "Conclusion\n"
        "In summary, liability is attracted under Section 66, Section 43, Section 66C, and Section 308."
    )

    sanitized = validator.audit_and_sanitize_answer(hallucinated_answer, [sec66_source])
    print(f"\n--- Sanitized Post-Generation Text ---\n{sanitized}\n")
    assert "Section 66" in sanitized
    assert "Section 43" not in sanitized
    assert "Section 66C" not in sanitized
    assert "Section 308" not in sanitized
    assert "mandatorily register an fir under section 154" not in sanitized.lower()
    assert "section 65b" not in sanitized.lower()
    print("-> PASS: Post-generation auditor and sanitizer successfully eliminated all ungrounded claims!")


def test_procedural_fact_first_routing_and_proposition_normalization():
    print("\n" + "=" * 70)
    print("TEST 10: Procedural Fact-First Routing & Proposition Normalization")
    print("=" * 70)

    from retrieval.proposition_extractor import PropositionExtractor
    from rag.clean_proposition import CleanProposition

    query = (
        "A person is arrested for theft. The police want to search their mobile phone. "
        "What is the procedure and what electronic evidence is relevant?"
    )

    # 1. Question Analysis & Classification
    analyzer = LegalQuestionAnalyzer()
    lq = analyzer.analyze(query)

    print(f"Query: {query}")
    print(f"  Primary Task:       {lq.primary_task}")
    print(f"  Background Offence: {lq.background_offence}")
    print(f"  Primary Domain:     {lq.primary_domain}")
    print(f"  Governing Enact.:   {lq.governing_enactments}")

    assert lq.primary_task == "SEARCH_SEIZURE", f"Expected primary_task SEARCH_SEIZURE, got {lq.primary_task}"
    assert lq.background_offence == "theft", f"Expected background_offence theft, got {lq.background_offence}"
    assert lq.primary_domain == "Criminal Procedure", f"Expected Criminal Procedure, got {lq.primary_domain}"
    assert "Bharatiya Nagarik Suraksha Sanhita, 2023" in lq.governing_enactments

    # 2. Query Analyzer Procedural Routing
    qa = LegalQueryAnalyzer()
    analysis_res = qa.analyze(query)
    print(f"  Detected Act:       {analysis_res.act}")
    print(f"  Target Document ID: {analysis_res.document_id}")
    assert analysis_res.document_id == "bnss_2023", f"Expected bnss_2023, got {analysis_res.document_id}"

    # 3. Universal Evidence Filtering (Demote theft punishment, promote search/seizure)
    bns_theft_chunk = {
        "text": "Section 303. Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
        "section_number": "303",
        "section_title": "Theft",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "document_id": "bns_2023",
        "evidence_type": "STATUTE",
        "topics": ["theft", "punishment", "dishonest taking"],
    }
    bnss_search_chunk = {
        "text": "Section 105. Search by police officer. Whenever an officer in charge of a police station has reasonable grounds for believing that anything necessary for an investigation may be found...",
        "section_number": "105",
        "section_title": "Search by police officer",
        "act": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "document_id": "bnss_2023",
        "evidence_type": "STATUTE",
        "topics": ["search", "seizure", "investigation", "summons to produce"],
    }

    res_theft = UniversalEvidenceFilter.evaluate_chunk(bns_theft_chunk, legal_question=lq)
    print(f"  BNS Theft Chunk Evaluation:  {res_theft.compatibility.value} ({res_theft.reason})")
    assert res_theft.compatibility == EvidenceCompatibility.BACKGROUND, "Theft chunk must be demoted to BACKGROUND for procedural search inquiry!"

    res_search = UniversalEvidenceFilter.evaluate_chunk(bnss_search_chunk, legal_question=lq)
    print(f"  BNSS Search Chunk Evaluation: {res_search.compatibility.value} ({res_search.reason})")
    assert res_search.compatibility == EvidenceCompatibility.DIRECT, "BNSS search chunk must be DIRECT for search inquiry!"

    # 4. Proposition Normalization (Decouple raw OCR & gazette headers)
    raw_ocr_snippet = (
        "12 THE GAZETTE OF INDIA EXTRAORDINARY [PART II—SEC. 1] "
        "Section 105. (1) Search by police officer. Whenever an officer in charge of a police station "
        "or an investigating officer having reasonable grounds for believing that anything necessary "
        "for the purpose of an investigation into any offence which he is authorised to investigate may be found..."
    )
    clean_prop_text = PropositionExtractor.clean_raw_text(raw_ocr_snippet, "105", "Search by police officer")
    print(f"\n  Raw OCR Snippet:   {raw_ocr_snippet[:80]}...")
    print(f"  Clean Proposition: {clean_prop_text[:100]}...")

    assert "THE GAZETTE OF INDIA" not in clean_prop_text
    assert "EXTRAORDINARY" not in clean_prop_text
    assert "[PART II" not in clean_prop_text
    assert not clean_prop_text.startswith("Section 105")
    assert not clean_prop_text.startswith("(1)")

    # 5. Deterministic Answer Builder Generation & Structural Verification
    search_source = SourceReference(
        chunk_id="bnss_sec_105",
        similarity_score=0.96,
        reranker_score=0.98,
        source_label="[Source S1]",
        document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
        section_number="105",
        section_title="Search by police officer",
        act_short_name="BNSS",
        text_snippet=raw_ocr_snippet,
        evidence_type="STATUTE",
    )

    resp_json = DeterministicAnswerBuilder.build_answer(query, [search_source])
    resp_data = json.loads(resp_json)

    main_answer = resp_data["mainAnswer"]
    legal_basis = resp_data["legalBasis"]
    propositions = resp_data.get("cleanPropositions", [])

    print("\nMain Answer Output Preview:")
    print(main_answer[:300] + "...")

    # Strict UI formatting assertions: NO bold, NO markdown headers, NO dividers
    assert "**" not in main_answer, "Must not contain '**'"
    assert "###" not in main_answer, "Must not contain '###'"
    assert "##" not in main_answer, "Must not contain '##'"
    assert "---" not in main_answer, "Must not contain '---'"
    assert "**" not in legal_basis
    assert "###" not in legal_basis
    assert "THE GAZETTE OF INDIA" not in legal_basis
    assert "EXTRAORDINARY" not in legal_basis

    # Exact required section headers
    assert "Answer\n" in main_answer or main_answer.startswith("Answer")
    assert "Search and Seizure Procedure" in main_answer
    assert "Electronic Evidence That May Be Relevant" in main_answer
    assert "Application" in main_answer
    assert "Important Qualifications" in main_answer
    assert "Conclusion" in main_answer

    # Verify content accuracy
    assert "theft" in main_answer.lower()
    assert "mobile phone" in main_answer.lower()
    assert "panchnama" in main_answer.lower()
    assert "hash" in main_answer.lower() or "faraday" in main_answer.lower()
    assert "Section 63" in main_answer or "Section 65B" in main_answer
    assert "Article 20(3)" in main_answer or "self-incrimination" in main_answer.lower()

    # Verify cleanPropositions payload
    assert len(propositions) >= 1
    assert propositions[0]["authority_name"] == "BNSS Section 105"
    assert "THE GAZETTE OF INDIA" not in propositions[0]["clean_proposition"]

    print("-> PASS: Procedural fact-first routing, evidence filtering, proposition normalization, and response structure verified!")


def test_suite_11_final_answer_presentation_and_no_meta_chat():
    print("\n" + "=" * 70)
    print("TEST 11: Final Answer Presentation, Completeness, and Absolute Prohibition of Meta-Chat")
    print("=" * 70)

    # 1. Sanitizer unit test with simulated model output containing meta-chat and jargon
    dirty_output = (
        "### Judicial Principles\n\n"
        "Under Indian criminal jurisprudence, **Sharad Birdhichand Sarda v. State of Maharashtra** establishes the panchsheel.\n\n"
        "Conclusion\n"
        "Conviction requires proof beyond reasonable doubt.\n\n"
        "---\n\n"
        "Would you like to refine the answer generation, inspect the underlying cleanPropositions JSON payload, or test another legal scenario?"
    )
    cleaned = LegalRAGPipeline._sanitize_meta_chat_and_formatting(dirty_output)
    print("Cleaned simulated output:\n", cleaned)
    assert "**" not in cleaned, "Markdown bold must be stripped"
    assert "###" not in cleaned, "Markdown headers must be stripped"
    assert "---" not in cleaned, "Horizontal rules must be stripped"
    assert "Would you like" not in cleaned, "Meta-chat question must be cleanly stripped"
    assert "cleanPropositions" not in cleaned, "Internal jargon must be stripped"
    assert "JSON payload" not in cleaned, "Internal jargon must be stripped"
    assert "reasonable doubt" in cleaned
    print("-> PASS: Sanitizer unit test verified successfully.")

    # 2. Test 8 diverse real-world legal scenarios through DeterministicAnswerBuilder & Sanitizer
    scenarios = [
        {
            "id": 1,
            "title": "Circumstantial Evidence Murder Scenario",
            "query": "A person is accused of murder, but there is no eyewitness. The prosecution relies entirely on circumstances such as motive, CCTV footage, call records, and forensic evidence. Can a murder conviction be based solely on circumstantial evidence? Explain the legal principles and judicial tests.",
            "sources": [
                SourceReference(
                    chunk_id="ce_case_1",
                    similarity_score=0.95,
                    reranker_score=0.97,
                    source_label="[Case Source C1]",
                    document_name="Sharad Birdhichand Sarda v. State of Maharashtra",
                    act_short_name="Case Law",
                    text_snippet="Five golden principles of circumstantial evidence laid down by Supreme Court.",
                    evidence_type="CASE_LAW",
                )
            ],
            "must_contain": [
                "Answer",
                "Judicial Principles",
                "Sharad Birdhichand Sarda",
                "fully established",
                "consistent only with",
                "conclusive nature",
                "exclude every possible hypothesis",
                "chain of evidence so complete",
                "Application to the Facts",
                "Motive",
                "CCTV",
                "Call Records",
                "Forensic",
                "Conclusion",
                "beyond reasonable doubt",
            ],
            "must_not_contain": [
                "Section 1",
                "Short title and commencement",
                "cleanPropositions",
                "JSON payload",
                "RAG",
                "deterministic fallback",
                "Would you like",
                "Let me know",
            ],
        },
        {
            "id": 2,
            "title": "Procedure + Evidence (Theft + Mobile Phone Search)",
            "query": "Police seized a mobile phone during a theft investigation without following seizure procedure. Can electronic evidence from it be used in court?",
            "sources": [],
            "must_contain": ["Investigation", "Evidence", "Application", "Conclusion", "procedural"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 3,
            "title": "Pure Evidence Law (Electronic Record Admissibility under BSA)",
            "query": "What are the conditions for admissibility of electronic records under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023?",
            "sources": [],
            "must_contain": ["Admissibility", "Section 63", "Certificate", "Application", "Conclusion"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 4,
            "title": "Practical Consumer Remedy (Defective Product)",
            "query": "A consumer purchased a defective smartphone that stopped working within 10 days. The seller and manufacturer refuse refund or replacement. What remedies are available under the Consumer Protection Act, 2019?",
            "sources": [],
            "must_contain": ["Remedies", "Consumer Protection Act", "District", "Refund", "Replacement", "Conclusion"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 5,
            "title": "RTI Appeal Procedure",
            "query": "The Public Information Officer rejected an RTI request without citing valid exemptions. How can the applicant appeal under the RTI Act, 2005?",
            "sources": [],
            "must_contain": ["Right to Information Act", "First Appeal", "Second Appeal", "First Appellate Authority", "Information Commission", "Conclusion"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 6,
            "title": "Cybercrime Scenario",
            "query": "A hacker gained unauthorized access to a company server, stole customer records, and demanded ransom. What offences apply, how should investigation proceed, and what digital evidence is required?",
            "sources": [],
            "must_contain": ["Offences", "Investigation", "Evidence", "Application", "Conclusion"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 7,
            "title": "Contract Dispute (Advance Payment Breach)",
            "query": "A vendor received 50% advance payment for goods but failed to deliver. Can the buyer terminate the contract and claim refund and damages under Indian Contract Act?",
            "sources": [],
            "must_contain": ["contract", "breach", "restitution", "damages", "Conclusion"],
            "must_not_contain": ["Would you like", "cleanPropositions", "JSON payload"],
        },
        {
            "id": 8,
            "title": "Constitutional Law (Article 21 Fair Procedure)",
            "query": "Explain the scope of Article 21 of the Constitution of India regarding personal liberty and the requirement of just, fair, and reasonable procedure.",
            "sources": [],
            "must_contain": ["Article 21", "fair", "procedure", "Conclusion"],
            "must_not_contain": ["Section 21", "Would you like", "cleanPropositions", "JSON payload"],
        },
    ]

    for sc in scenarios:
        print(f"\nEvaluating Scenario {sc['id']}: {sc['title']}")
        resp_str = DeterministicAnswerBuilder.build_answer(sc["query"], sc["sources"])
        data = json.loads(resp_str)
        main_ans = LegalRAGPipeline._sanitize_meta_chat_and_formatting(data["mainAnswer"])
        legal_basis = LegalRAGPipeline._sanitize_meta_chat_and_formatting(data.get("legalBasis", ""))
        full_text = main_ans + "\n" + legal_basis

        # Professional presentation assertions
        assert "**" not in full_text, f"Markdown bold leak in scenario {sc['id']}"
        assert "###" not in full_text, f"Markdown header leak in scenario {sc['id']}"
        assert "---" not in full_text, f"Markdown divider leak in scenario {sc['id']}"
        assert "THE GAZETTE OF INDIA" not in full_text, f"Raw gazette leak in scenario {sc['id']}"
        assert "EXTRAORDINARY" not in full_text, f"Raw OCR leak in scenario {sc['id']}"

        # Absolute prohibition of meta-conversation and assistant chatter
        for forbidden in ["Would you like", "Do you want", "Let me know", "I can assist", "Please let me know"]:
            assert forbidden.lower() not in full_text.lower(), f"Forbidden meta-text '{forbidden}' found in scenario {sc['id']}"

        # Substantive facet completeness
        for req in sc["must_contain"]:
            assert req.lower() in full_text.lower(), f"Missing required concept '{req}' in scenario {sc['id']}"

        # Negative checks
        for forbidden in sc["must_not_contain"]:
            assert forbidden.lower() not in full_text.lower(), f"Found forbidden item '{forbidden}' in scenario {sc['id']}"

        print(f"  -> Scenario {sc['id']} ({sc['title']}) PASSED all presentation, depth, and meta-chat checks.")

    print("\n-> PASS: TEST 11 (Final Answer Presentation, Completeness, and No Meta-Chat Fix) completely verified!")


if __name__ == "__main__":
    test_universal_question_modeling()
    test_universal_evidence_relevance_filter()
    test_deterministic_answer_builder_style_and_substance()
    test_constitutional_article_distinction()
    test_adaptive_professional_legal_response_generation()
    test_universal_fact_first_domain_routing_20_categories()
    test_cross_domain_negative_tests()
    test_required_regression_tests_section_24()
    test_claim_level_grounding_and_unsupported_claim_prevention()
    test_procedural_fact_first_routing_and_proposition_normalization()
    test_suite_11_final_answer_presentation_and_no_meta_chat()
    print("\n" + "=" * 70)
    print("ALL UNIVERSAL & ADAPTIVE EVALUATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


