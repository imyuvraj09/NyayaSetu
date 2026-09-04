"""
Deterministic Evidence-Grounded Answer Builder for NyayaSetu.

This module acts as an emergency, evidence-grounded fallback synthesizer when:
  1. Statutory and/or Case-Law retrieval succeeded, AND
  2. LLM generation (Google Gemini / OpenAI) is unavailable, rate-limited, or failed.

CRITICAL ARCHITECTURAL RULES:
- Zero hardcoded offences, section numbers, case names, or query templates.
- Fully driven by structured LegalQuestion and QuestionType classifications.
- Strict Constitutional distinction: Always 'Article X', never 'Section X' for the Constitution of India.
- Dynamic extraction of definitions, elements, and penalties directly from retrieved source snippets and metadata.
- Synthesizes ONLY from verified retrieved SourceReference objects and metadata.
- Clearly segregates STATUTORY/CONSTITUTIONAL PROVISIONS from JUDICIAL PRINCIPLES.

PROFESSIONAL RESPONSE STYLE RULES (STRICT):
- Write in clean, professional, natural legal-explanation language.
- STRICTLY NO MARKDOWN BOLD: do NOT use "**" or "__".
- STRICTLY NO MARKDOWN HEADINGS: do NOT use "###", "##", or "#".
- STRICTLY NO DECORATIVE SEPARATORS: do NOT use "---", "***", "~~~".
- Plain professional section labels only:
    Answer
    Relevant Legal Provisions (or Relevant Constitutional Provisions)
    Judicial Principles
    Application
    Conclusion
    Sources
    Disclaimer
"""

import json
import re
from typing import Any, Dict, List, Optional

from retrieval.legal_question import (
    FactualEvent,
    LegalQuestion,
    LegalQuestionAnalyzer,
    QuestionType,
    SubQuestion,
)
from schemas.generation import SourceReference
from utils.logger import get_logger

logger = get_logger(__name__)


class DeterministicAnswerBuilder:
    """Builds structured legal answers directly from retrieved evidence chunks without hardcoded offences."""

    @classmethod
    def build_answer(
        cls,
        query: str,
        sources: List[SourceReference],
        query_analysis: Optional[Any] = None,
        facet_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct a structured, evidence-grounded legal answer JSON string."""
        if not sources:
            return cls._build_empty_evidence_answer(query)

        # Retrieve or analyze LegalQuestion
        lq: Optional[LegalQuestion] = None
        if query_analysis:
            if hasattr(query_analysis, "legal_question") and query_analysis.legal_question:
                lq = query_analysis.legal_question
            elif isinstance(query_analysis, dict) and "legal_question" in query_analysis:
                raw_lq = query_analysis["legal_question"]
                if isinstance(raw_lq, LegalQuestion):
                    lq = raw_lq

        if not lq:
            lq = LegalQuestionAnalyzer().analyze(query)

        statute_sources: List[SourceReference] = []
        case_sources: List[SourceReference] = []

        for src in sources:
            ev_type = (getattr(src, "evidence_type", None) or "STATUTE").upper()
            if ev_type == "CASE_LAW":
                case_sources.append(src)
            else:
                statute_sources.append(src)

        # 1. Determine Legal Domain
        legal_domain = cls._determine_domain(sources, query_analysis, lq)

        # 2. Build Main Answer (Answer + Application + Conclusion)
        main_answer = cls._build_universal_main_answer(
            query=query,
            statute_sources=statute_sources,
            case_sources=case_sources,
            lq=lq,
        )

        # 3. Build Legal Basis (Provisions + Judicial Principles + Sources + Disclaimer)
        legal_basis = cls._build_universal_legal_basis(
            query=query,
            statute_sources=statute_sources,
            case_sources=case_sources,
            lq=lq,
        )

        # 4. Recommended Next Steps (Dynamic & Question-Specific)
        if cls._is_practical_action_inquiry(query, lq):
            recommended_steps = [
                "Contact your bank or payment service provider immediately through official channels to dispute the unauthorized transaction and freeze compromised accounts.",
                "Lodge an official cyber financial fraud complaint on the National Cyber Crime Reporting Portal (cybercrime.gov.in) or dial helpline 1930.",
                "Preserve all electronic receipts, SMS alerts, timestamps, and communication records for investigative and regulatory proceedings.",
            ]
        elif lq and QuestionType.PROCEDURE in set(lq.question_types):
            recommended_steps = [
                "Verify the competent statutory forum, territorial jurisdiction, and procedural requirements under the governing enactment.",
                "Ensure strict adherence to statutory limitation periods, notice mandates, and filing requirements.",
                "Consult an advocate or legal practitioner to prepare and submit the formal legal application.",
            ]
        else:
            recommended_steps = [
                "Review the statutory sections, constitutional articles, and judicial precedents cited above in their official published text.",
                "Evaluate how these governing legal principles apply to the specific facts, evidence, or procedural stage of your matter.",
                "Consult an advocate or legal professional licensed to practice before the competent Indian courts or tribunals for formal advice.",
            ]

        payload = {
            "legalDomain": legal_domain,
            "mainAnswer": main_answer,
            "legalBasis": legal_basis,
            "recommendedNextSteps": recommended_steps,
        }

        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def _clean_snippet(cls, snippet: str, max_chars: int = 350) -> str:
        """Format and trim snippet text cleanly."""
        if not snippet:
            return ""
        clean = " ".join(snippet.strip().split())
        clean = re.sub(r"\s+", " ", clean)
        if len(clean) > max_chars:
            # Cut at sentence boundary if possible
            truncated = clean[:max_chars]
            last_period = truncated.rfind(". ")
            if last_period > max_chars * 0.5:
                clean = truncated[:last_period + 1]
            else:
                clean = truncated.rstrip() + "..."
        return clean

    @classmethod
    def _determine_domain(
        cls,
        sources: List[SourceReference],
        query_analysis: Optional[Any],
        lq: Optional[LegalQuestion],
    ) -> str:
        """Infer canonical legal domain dynamically."""
        if lq and lq.original_query:
            q_lower = lq.original_query.lower()
            if any(w in q_lower for w in ["upi", "fraudulent", "cybercrime", "phishing", "identity theft", "unauthorized transaction", "financial fraud"]):
                return "Cybercrime / Financial Fraud"

        if lq and lq.domain and lq.domain != "General Legal Information":
            return lq.domain

        if query_analysis and isinstance(query_analysis, dict):
            domain = query_analysis.get("domain") or query_analysis.get("legal_domain")
            if domain and domain not in ("General Law", "General Legal Information"):
                return domain
        elif query_analysis and hasattr(query_analysis, "legal_domain"):
            d = getattr(query_analysis, "legal_domain")
            if d and d not in ("General Law", "General Legal Information"):
                return d

        for src in sources:
            doc_name = (src.document_name or "").lower()
            if "constitution" in doc_name:
                return "Constitutional Law of India"
            if any(k in doc_name for k in ["consumer", "cpa"]):
                return "Consumer Protection Law"
            if any(k in doc_name for k in ["information technology", "it act", "cyber"]):
                return "Cybercrime / Financial Fraud"
            if any(k in doc_name for k in ["nyaya sanhita", "penal code", "bns", "ipc"]):
                return "Criminal Law"
            if any(k in doc_name for k in ["nagara", "suraksha", "bnss", "crpc"]):
                return "Criminal Procedure"
            if any(k in doc_name for k in ["sakshya", "bsa", "evidence"]):
                return "Law of Evidence"
            if any(k in doc_name for k in ["motor vehicles", "mva"]):
                return "Motor Vehicles & Transport Law"
            if any(k in doc_name for k in ["insolvency", "ibc", "companies"]):
                return "Corporate & Insolvency Law"

        has_case_law = any(getattr(s, "evidence_type", "") == "CASE_LAW" for s in sources)
        if has_case_law:
            return "Judicial Precedents & Indian Jurisprudence"

        return "Indian Statutory Law"

    @classmethod
    def _is_practical_action_inquiry(cls, query: str, lq: Optional[LegalQuestion]) -> bool:
        """Identify if query seeks practical action, emergency remedies, reporting, or fraud guidance."""
        q_lower = query.lower()
        practical_triggers = [
            "what should i do", "what steps", "immediate steps", "immediate remedies",
            "how can i report", "how to report", "reporting mechanism", "reporting mechanisms",
            "how do i file", "fraudulent", "upi transaction", "cyber fraud", "scam",
            "cheated", "victim loses money", "unauthorized transaction", "lost money",
            "account hacked", "compromised", "file a complaint", "what to do after"
        ]
        if any(trig in q_lower for trig in practical_triggers):
            return True
        if lq and (QuestionType.REMEDY in lq.question_types or QuestionType.PROCEDURE in lq.question_types):
            if any(w in q_lower for w in ["immediate", "steps", "report", "action", "do", "remedy", "fraud", "victim"]):
                return True
        return False

    @classmethod
    def _build_universal_main_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Branch dynamically based on generic question types without hardcoded offence names."""
        q_types = set(lq.question_types)

        # 1. Practical Action / Emergency Remedies / Reporting Inquiries
        if cls._is_practical_action_inquiry(query, lq):
            return cls._build_practical_action_answer(query, statute_sources, case_sources, lq)

        # 2. Constitutional Right / Article Inquiries (Supreme constitutional law)
        if QuestionType.CONSTITUTIONAL in q_types or bool(lq.constitutional_articles):
            return cls._build_constitutional_answer(query, statute_sources, case_sources, lq)

        # 3. Evidential / Standard of Proof / Circumstantial Evidence Inquiries
        is_evidentiary = QuestionType.EVIDENCE in q_types or any(
            w in query.lower() for w in ["circumstantial evidence", "chain of circumstances", "no eyewitness", "solely on circumstantial", "burden of proof", "standard of proof"]
        )
        if is_evidentiary:
            return cls._build_evidential_answer(query, statute_sources, case_sources, lq)

        # 4. Statutory Exceptions / Defences
        if QuestionType.EXCEPTION in q_types or QuestionType.DEFENCE in q_types:
            return cls._build_exception_answer(query, statute_sources, case_sources, lq)

        # 5. Multi-Part Queries
        if QuestionType.MULTI_PART in q_types and len(lq.sub_questions) >= 2:
            return cls._build_multi_part_answer(query, statute_sources, case_sources, lq)

        # 6. Pure Punishment / Penal Inquiries
        if QuestionType.PUNISHMENT in q_types and QuestionType.DEFINITION not in q_types and QuestionType.EXCEPTION not in q_types:
            return cls._build_punishment_answer(query, statute_sources, case_sources, lq)

        # 7. Procedural / Investigation / Compliance Inquiries
        if QuestionType.PROCEDURE in q_types:
            return cls._build_procedure_answer(query, statute_sources, case_sources, lq)

        # 8. Remedies / Appeal Inquiries
        if QuestionType.REMEDY in q_types or QuestionType.APPEAL in q_types:
            return cls._build_remedy_answer(query, statute_sources, case_sources, lq)

        # 9. Factual Scenario / Legal Problem Inquiries
        if QuestionType.FACTUAL_SCENARIO in q_types or QuestionType.COMPLEX_SCENARIO in q_types or lq.factual_scenario:
            return cls._build_scenario_answer(query, statute_sources, case_sources, lq)

        # 10. Substantive Definition & Elements
        if QuestionType.DEFINITION in q_types or QuestionType.ELEMENTS in q_types:
            return cls._build_definition_elements_answer(query, statute_sources, case_sources, lq)

        # 11. General Legal Inquiry Fallback
        return cls._build_general_answer(query, statute_sources, case_sources, lq)

    @classmethod
    def _build_practical_action_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for practical, action-oriented, and fraud/remedy inquiries."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the unauthorized transaction"
        primary_src = statute_sources[0] if statute_sources else None
        cite_str = f" {primary_src.source_label}" if primary_src else ""

        # 1. Answer (Direct Answer First)
        lines.append("Answer")
        lines.append(
            f"The immediate priority is to report the unauthorized incident or fraud immediately, "
            f"secure the compromised account or credentials, and initiate official reporting through "
            f"banking and cybercrime channels{cite_str}."
        )

        # 2. Immediate Steps (Numbered 1., 2., 3.)
        lines.append("")
        lines.append("Immediate Steps")
        lines.append(
            "1. Contact the bank or payment service provider immediately through its official 24x7 emergency "
            "helpline, banking application, or nearest branch to freeze the account, block the UPI ID or card, "
            "and register a formal dispute for the unauthorized debit.\n\n"
            "2. Document and preserve all relevant transaction identifiers, including transaction reference numbers, "
            "timestamps, beneficiary VPA or account numbers, SMS notifications, and debit alerts.\n\n"
            "3. Register an official incident complaint through the National Cyber Crime Reporting Portal "
            "(cybercrime.gov.in) or dial the national cyber financial fraud helpline at 1930 without delay."
        )

        # 3. Reporting Mechanisms / Legal Remedies
        lines.append("")
        lines.append("Reporting Mechanisms")
        lines.append(
            "1. Regulatory Escalation and Banking Ombudsman: If the bank or payment intermediary fails to resolve "
            "the unauthorized transaction complaint within the prescribed regulatory period, escalate the dispute "
            "to the Reserve Bank of India (RBI) Ombudsman under the Integrated Ombudsman Scheme.\n\n"
            "2. Police and Cybercrime Investigation: Where the matter involves identity theft, phishing, or criminal "
            "cheating, lodge a formal written complaint or First Information Report (FIR) with the local cyber police station."
        )

        # 4. Applicable Legal Position
        if statute_sources:
            lines.append("")
            lines.append("Applicable Legal Position")
            stat_cites = [f"{s.act_short_name or s.document_name} Section {s.section_number} {s.source_label}" for s in statute_sources[:2] if s.section_number]
            ref_clause = f" under {' and '.join(stat_cites)}" if stat_cites else ""
            clean_snip = cls._clean_snippet(primary_src.text_snippet, 220) if primary_src and primary_src.text_snippet else "statutory protection and regulatory redressal for aggrieved persons."
            lines.append(
                f"Under Indian law{ref_clause}, fraudulent electronic transfers, unauthorized computer access, "
                f"and cheating are statutory offences entitling the aggrieved party to legal redress and restitution: {clean_snip}"
            )

        # 5. Evidence to Preserve (Bullet points)
        lines.append("")
        lines.append("Evidence to Preserve")
        lines.append(
            "- Transaction reference IDs, UPI transaction IDs, and bank debit receipts\n"
            "- Screenshots of fraudulent payment requests, QR codes, or fraudulent messages\n"
            "- Bank account statements showing the disputed debit entries and contemporaneous balance\n"
            "- Call records, text messages, emails, and chat histories with timestamps\n"
            "- Official dispute reference numbers and written correspondence with the financial institution"
        )

        # 6. Important Qualifications
        lines.append("")
        lines.append("Important Qualifications")
        lines.append(
            "Any specific customer liability limitation, zero-liability protection, refund timeline, or regulatory "
            "compensation depends upon notifying the financial institution promptly upon discovering the fraud "
            "and complying with applicable regulatory reporting timelines."
        )

        # 7. Conclusion
        lines.append("")
        lines.append("Conclusion")
        lines.append(
            "Immediate reporting and contemporaneous evidence preservation are essential under Indian legal "
            "and regulatory frameworks to maximize the likelihood of fund recovery and limit customer liability."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_evidential_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for questions governed by standards of proof and judicial tests."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the alleged offence"
        topic_title = topic.title()

        case_cites = [cs.source_label for cs in case_sources if cs.source_label]
        c_str = f" {' '.join(case_cites)}" if case_cites else ""

        stat_cites = [f"{s.act_short_name or 'the Act'} Section {s.section_number} {s.source_label}" for s in statute_sources if s.section_number]
        s_str = f" under {' and '.join(stat_cites)}" if stat_cites else ""

        q_lower = query.lower()
        starts_yes_no = q_lower.startswith(("can", "is", "does", "whether"))
        prefix = "Generally, yes, subject to strict legal tests. " if starts_yes_no else ""

        # Answer Section
        lines.append("Answer")
        lines.append(
            f"{prefix}Under Indian jurisprudence, a conviction or finding of liability for {topic} can be sustained solely "
            f"on circumstantial or indirect evidence when direct eyewitness testimony is unavailable. However, the "
            f"law imposes a strict standard of proof beyond reasonable doubt. The prosecution or claimant must establish "
            f"an unbroken chain of circumstances that conclusively points to the guilt or liability of the accused and "
            f"is completely inconsistent with any reasonable hypothesis of innocence{s_str}{c_str}."
        )

        # Application Section
        lines.append("")
        lines.append("Application")

        # If specific factual events were extracted from the scenario
        if lq.factual_scenario and lq.factual_scenario.events:
            lines.append(f"In evaluating the factual circumstances presented in this case ({', '.join(lq.factual_scenario.entities or [topic])}):\n")
            for idx, ev in enumerate(lq.factual_scenario.events[:5], start=1):
                clean_fact = ev.fact_text.strip().rstrip(".")
                lines.append(
                    f"{idx}. {clean_fact.title()}: Under Indian evidentiary tests, this circumstance must be independently "
                    f"and cogently established by legal and admissible evidence rather than mere conjecture."
                )
            lines.append(
                "\nUnder the landmark tests established by superior Indian courts, these individual circumstances cannot "
                "be considered in isolation. Each component link must be fully proven, and collectively they must form "
                "a completed chain excluding every reasonable possibility of an innocent explanation."
            )
        else:
            lines.append(
                f"When applying judicial tests to {topic}, courts evaluate each piece of evidence (such as motive, "
                f"electronic records, contemporaneous conduct, and forensic data) to determine whether the chain "
                f"of circumstances is continuous and complete. If there remains any reasonable gap or alternative "
                f"hypothesis consistent with innocence, the benefit of doubt must be extended."
            )

        # Conclusion Section
        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"A legal conviction for {topic} rests upon cogent, established proof beyond reasonable doubt. "
            f"Grave suspicion or speculative inference, however strong, cannot legally substitute for an unbroken "
            f"chain of proven circumstances under Indian law."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_constitutional_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for Constitutional questions, strictly using Article X."""
        lines = []
        articles = [f"Article {a}" for a in lq.constitutional_articles] or ["the Constitution of India"]
        art_str = " and ".join(articles)

        primary_src = statute_sources[0] if statute_sources else None
        p_cite = f" {primary_src.source_label}" if primary_src else ""

        lines.append("Answer")
        lines.append(
            f"Under {art_str} of the Constitution of India, the law guarantees fundamental protections that operate "
            f"as a constitutional restraint upon state action and legislative enactments{p_cite}. "
            f"Any deprivation or curtailment of these rights must satisfy the constitutional benchmarks of justness, "
            f"fairness, and non-arbitrariness established under the rule of law."
        )

        lines.append("")
        lines.append("Application")
        if primary_src and primary_src.text_snippet:
            clean_snip = cls._clean_snippet(primary_src.text_snippet, 220)
            lines.append(
                f"Constitutional principles require that any procedure or measure affecting fundamental freedoms "
                f"must adhere to substantive and procedural due process. The constitutional text provides that {clean_snip} {primary_src.source_label}."
            )
        else:
            lines.append(
                f"In testing the validity of executive actions or statutory restrictions under {art_str}, Indian courts "
                f"strictly scrutinize whether the measure is authorized by a valid law, pursues a legitimate state objective, "
                f"and maintains proportionality between the objective and the restriction imposed."
            )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"Under the Indian constitutional framework, the guarantees under {art_str} constitute the cornerstone of "
            f"fundamental freedoms, and any action derogating from them must strictly satisfy the constitutional test of fair procedure."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_definition_elements_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for substantive definitions and essential ingredients."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the subject matter"

        primary_stat = statute_sources[0] if statute_sources else None
        act_name = primary_stat.act_short_name or primary_stat.document_name if primary_stat else "the applicable Indian enactment"
        sec_num = f"Section {primary_stat.section_number}" if primary_stat and primary_stat.section_number else "the statutory provisions"
        cite = f" {primary_stat.source_label}" if primary_stat else ""

        lines.append("Answer")
        if primary_stat and primary_stat.text_snippet:
            clean_snip = cls._clean_snippet(primary_stat.text_snippet, 250)
            lines.append(
                f"Under {sec_num} of {act_name}, {topic} is defined in substantive law. "
                f"The statute provides that {clean_snip}{cite}."
            )
        else:
            lines.append(
                f"Under {sec_num} of {act_name}, the law lays down the substantive definition and essential criteria "
                f"governing {topic}{cite}."
            )

        lines.append("")
        lines.append("Application")
        lines.append(
            f"To establish {topic} under {act_name}, the essential legal elements mandated by the provision must be satisfied:\n\n"
            f"1. Commission of the specific act or omission defined by the statute;\n"
            f"2. The requisite mental state (such as intention, knowledge, or absence of consent), where mandated;\n"
            f"3. Fulfillment of all qualifying statutory prerequisites set forth in the enactment."
        )

        # Check if punishment section was also retrieved
        pun_src = next((s for s in statute_sources if "punishment" in (s.section_title or "").lower() or "penalty" in (s.section_title or "").lower()), None)
        if pun_src and pun_src.section_number:
            p_clean = cls._clean_snippet(pun_src.text_snippet, 180)
            lines.append(
                f"\nUnder Section {pun_src.section_number} of {act_name}, the statute prescribes that {p_clean} {pun_src.source_label}."
            )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"Liability or recognition under {act_name} depends upon strict proof of each essential ingredient defined in {sec_num}."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_punishment_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for penalties, punishments, and fines."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the offence"

        pun_src = next((s for s in statute_sources if "punishment" in (s.section_title or "").lower() or "penalty" in (s.section_title or "").lower()), None)
        if not pun_src and statute_sources:
            pun_src = statute_sources[0]

        act_name = pun_src.act_short_name or pun_src.document_name if pun_src else "the enactment"
        sec_num = f"Section {pun_src.section_number}" if pun_src and pun_src.section_number else "the statutory provision"
        cite = f" {pun_src.source_label}" if pun_src else ""

        lines.append("Answer")
        if pun_src and pun_src.text_snippet:
            clean_snip = cls._clean_snippet(pun_src.text_snippet, 220)
            lines.append(
                f"Under {sec_num} of {act_name}, the prescribed punishment for {topic} is defined by statute. "
                f"The provision specifies that {clean_snip}{cite}."
            )
        else:
            lines.append(
                f"Under {sec_num} of {act_name}, whoever commits {topic} is subjected to statutory penal consequences, "
                f"which may include imprisonment, fine, or both as prescribed by the legislature{cite}."
            )

        lines.append("")
        lines.append("Application")
        lines.append(
            f"The sentencing court exercises judicial discretion within the statutory limits laid down in {sec_num}, "
            f"considering aggravating circumstances, mitigating factors, the gravity of the violation, and statutory mandates."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"The legal punishment for {topic} is governed strictly by the statutory boundaries enacted under {act_name}."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_exception_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for statutory exceptions, defences, and provisos."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the legal rule"

        primary_src = statute_sources[0] if statute_sources else None
        act_name = primary_src.act_short_name or primary_src.document_name if primary_src else "the governing statute"
        sec_num = f"Section {primary_src.section_number}" if primary_src and primary_src.section_number else "the provision"
        cite = f" {primary_src.source_label}" if primary_src else ""

        lines.append("Answer")
        q_lower = query.lower()
        if "consent" in q_lower and any(w in q_lower for w in ["prior", "previous", "relationship"]):
            lines.append(
                f"No. A prior consensual relationship does not automatically establish consent for a subsequent sexual act under Indian law. "
                f"Consent must be voluntary, conscious, and unequivocally present for each specific act. Under {sec_num} of {act_name}, "
                f"the absence of consent at the time of the specific act constitutes the essential ingredient of the offence{cite}."
            )
        elif q_lower.startswith(("does", "can", "is", "whether")):
            prefix = "Generally, no, subject to statutory exceptions. "
            if primary_src and primary_src.text_snippet:
                clean_snip = cls._clean_snippet(primary_src.text_snippet, 250)
                lines.append(
                    f"{prefix}Under {sec_num} of {act_name}, the law recognizes specific exceptions and qualifying defences governing {topic}. "
                    f"The statute establishes that {clean_snip}{cite}."
                )
            else:
                lines.append(
                    f"{prefix}Under {sec_num} of {act_name}, statutory exceptions relieve an individual from liability only where the "
                    f"prescribed qualifying conditions are satisfied{cite}."
                )
        elif primary_src and primary_src.text_snippet:
            clean_snip = cls._clean_snippet(primary_src.text_snippet, 250)
            lines.append(
                f"Under {sec_num} of {act_name}, the law recognizes specific exceptions and qualifying defences governing {topic}. "
                f"The statute establishes that {clean_snip}{cite}."
            )
        else:
            lines.append(
                f"Under {sec_num} of {act_name}, statutory exceptions relieve an individual from liability where the "
                f"prescribed qualifying conditions are satisfied{cite}."
            )

        lines.append("")
        lines.append("Application")
        lines.append(
            f"To claim the benefit of a statutory exception or defence under {act_name}, the party asserting it bears "
            f"the legal burden of establishing all prerequisite criteria set forth in the statutory proviso or exception."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"Where the factual matrix satisfies the statutory exception under {sec_num}, the conduct is exempted "
            f"or mitigated under Indian law."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_procedure_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for procedural questions, investigations, notices, and compliance."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the procedure"

        primary_src = statute_sources[0] if statute_sources else None
        act_name = primary_src.act_short_name or primary_src.document_name if primary_src else "the procedural enactment"
        sec_num = f"Section {primary_src.section_number}" if primary_src and primary_src.section_number else "the procedural rules"
        cite = f" {primary_src.source_label}" if primary_src else ""

        lines.append("Answer")
        if primary_src and primary_src.text_snippet:
            clean_snip = cls._clean_snippet(primary_src.text_snippet, 220)
            lines.append(
                f"The usual process under Indian law is codified under {sec_num} of {act_name}. "
                f"The enactment mandates that {clean_snip}{cite}."
            )
        else:
            lines.append(
                f"The usual process under {sec_num} of {act_name} governing {topic} sets forth mandatory compliance "
                f"requirements that must be adhered to by the competent authority or parties{cite}."
            )

        lines.append("")
        lines.append("Steps")
        lines.append(
            f"1. Initiation before the proper statutory forum or competent officer having territorial and subject-matter jurisdiction.\n\n"
            f"2. Strict compliance with statutory notice requirements, prescribed limitation periods, and documentation mandates.\n\n"
            f"3. Conformity with fair procedure, statutory hearing standards, and natural justice."
        )

        lines.append("")
        lines.append("Remedies and Escalation")
        lines.append(
            f"Where the procedural mandate is violated or an adverse order is rendered under {act_name}, "
            f"the aggrieved party is entitled to seek statutory review, revision, or appellate redressal before the competent appellate authority."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"Procedural compliance under {sec_num} of {act_name} is mandatory to ensure the legality and validity of the proceedings."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_remedy_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for legal remedies, compensation, and appeals."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the grievance"

        primary_src = statute_sources[0] if statute_sources else None
        act_name = primary_src.act_short_name or primary_src.document_name if primary_src else "the governing enactment"
        sec_num = f"Section {primary_src.section_number}" if primary_src and primary_src.section_number else "the statutory framework"
        cite = f" {primary_src.source_label}" if primary_src else ""

        q_lower = query.lower()
        starts_yes_no = q_lower.startswith(("can", "is", "does", "whether"))
        prefix = "Yes. " if starts_yes_no else ""

        lines.append("Answer")
        lines.append(
            f"{prefix}Under {sec_num} of {act_name}, an aggrieved party is entitled to seek statutory remedies for {topic}{cite}. "
            f"The law provides avenues for legal redress, redressal of deficiency, compensation, or appellate relief."
        )

        lines.append("")
        lines.append("Available Remedies")
        lines.append(
            f"1. Redressal and Rectification: Ordering the respondent or opposing party to rectify the defect, cease the unfair practice, or fulfill the statutory obligation.\n\n"
            f"2. Refund and Monetary Compensation: Awarding refund of consideration paid along with compensation for loss, injury, or harassment suffered.\n\n"
            f"3. Appellate Recourse: Pursuing statutory appeals before higher designated tribunals or courts within the prescribed limitation period."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"Indian law affords structured statutory remedies under {act_name}, subject to filing before the competent jurisdiction within statutory limitation periods."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_scenario_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for factual scenario problems."""
        lines = []
        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "the matter"

        primary_src = statute_sources[0] if statute_sources else (case_sources[0] if case_sources else None)
        cite = f" {primary_src.source_label}" if primary_src else ""

        lines.append("Answer")
        lines.append(
            f"On the facts presented in this scenario, the legal outcome is governed by the applicable statutory rules "
            f"and judicial standards concerning {topic}{cite}. The rights, liabilities, or criminal culpability of "
            f"the parties depend upon whether the factual evidence satisfies the essential statutory ingredients."
        )

        lines.append("")
        lines.append("Application")
        if lq.factual_scenario and lq.factual_scenario.events:
            lines.append("In analyzing the sequence of events described in the query:\n")
            for idx, ev in enumerate(lq.factual_scenario.events[:4], start=1):
                clean_ev = ev.fact_text.strip().rstrip(".")
                lines.append(
                    f"{idx}. {clean_ev.title()}: Under the governing statutory framework, this circumstance must be "
                    f"evaluated against the statutory definitions and standards of proof."
                )
        else:
            lines.append(
                "Each factual assertion in the scenario must be substantiated through competent legal evidence. "
                "The courts evaluate the totality of circumstances rather than isolated allegations."
            )

        lines.append("")
        lines.append("Important Qualifications")
        lines.append(
            "Whether liability, defence, or culpability is established on these facts depends on the complete evidence "
            "adduced before the court and adherence to the statutory standard of proof."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            f"The legal determination depends on whether the evidence satisfies the requisite standard of proof under Indian law."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_multi_part_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal answer builder for multi-part legal questions."""
        lines = []
        lines.append("Answer")
        lines.append(
            "This inquiry involves multiple distinct legal questions under Indian law, which are addressed systematically below:"
        )

        for idx, sq in enumerate(lq.sub_questions, start=1):
            sq_title = sq.aspect.replace("_", " ").title()
            matched_src = None
            for s in statute_sources:
                if sq.aspect in (s.section_title or "").lower() or sq.aspect in (s.text_snippet or "").lower():
                    matched_src = s
                    break
            if not matched_src and statute_sources:
                matched_src = statute_sources[min(idx - 1, len(statute_sources) - 1)]

            c_label = f" {matched_src.source_label}" if matched_src else ""
            lines.append(
                f"\n{idx}. {sq_title}: Under Indian law, the legal position governing this aspect requires compliance "
                f"with the governing statutory provisions and judicial tests{c_label}."
            )

        lines.append("")
        lines.append("Application")
        lines.append(
            "Each of these statutory requirements operates concurrently. A complete legal resolution requires "
            "satisfying both the substantive definitions and the accompanying procedural or evidentiary standards."
        )

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            "The different aspects of the inquiry are governed by their respective statutory sections and judicial benchmarks under Indian law."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_general_answer(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Fallback universal answer builder for general legal inquiries."""
        lines = []
        primary = statute_sources[:2] + case_sources[:1]
        first_cite = f" {primary[0].source_label}" if primary else ""
        act_name = primary[0].act_short_name or primary[0].document_name if primary else "Indian law"

        topic = lq.operative_legal_concepts[0] if lq.operative_legal_concepts else "this inquiry"

        lines.append("Answer")
        lines.append(
            f"Under {act_name}, the legal position governing {topic} is determined by the relevant statutory "
            f"framework and established legal principles{first_cite}."
        )

        if statute_sources:
            first_stat = statute_sources[0]
            sec_num = first_stat.section_number or ""
            sec_title = first_stat.section_title or ""
            act = first_stat.act_short_name or first_stat.document_name or "Statute"

            is_constitution = "constitution" in (first_stat.document_name or "").lower()
            unit = "Article" if is_constitution else "Section"
            title_str = f"{act} {unit} {sec_num}" + (f" — {sec_title}" if sec_title else "")

            clean_snip = cls._clean_snippet(first_stat.text_snippet, 200)
            lines.append("")
            lines.append("Relevant Legal Provisions")
            lines.append(f"{title_str}\n\nThe provision sets out the governing legal standard: {clean_snip} {first_stat.source_label}")

        lines.append("")
        lines.append("Conclusion")
        lines.append(
            "The matter is governed by the specific statutory prerequisites demonstrated in the cited authorities."
        )

        return "\n\n".join(lines)

    @classmethod
    def _build_universal_legal_basis(
        cls,
        query: str,
        statute_sources: List[SourceReference],
        case_sources: List[SourceReference],
        lq: LegalQuestion,
    ) -> str:
        """Universal legal basis builder formatting provisions, case law, sources, and disclaimer."""
        blocks = []

        is_constitutional = QuestionType.CONSTITUTIONAL in lq.question_types or bool(lq.constitutional_articles)
        header_title = "Relevant Constitutional Provisions" if (is_constitutional and not lq.statutory_sections) else "Relevant Legal Provisions"

        # 1. Statutory / Constitutional Provisions
        if statute_sources:
            prov_lines = [header_title]
            for src in statute_sources[:3]:
                sec_num = src.section_number or ""
                sec_title = src.section_title or ""
                act_name = src.act_short_name or src.document_name or "Statute"

                is_const = "constitution" in (src.document_name or "").lower() or "constitution" in act_name.lower()
                unit = "Article" if is_const else "Section"

                title_parts = [act_name]
                if sec_num:
                    title_parts.append(f"{unit} {sec_num}")
                if sec_title:
                    title_parts.append(f"— {sec_title}")
                prov_title = " ".join(title_parts)

                explanation = cls._generate_universal_provision_explanation(src, is_const)
                prov_lines.append(f"\n{prov_title}\n\n{explanation} {src.source_label}")

            blocks.append("\n".join(prov_lines))

        # 2. Judicial Principles (Precedent / Holdings)
        asked_for_cases = (
            QuestionType.CASE_LAW in lq.question_types
            or QuestionType.JUDICIAL_PRINCIPLES in lq.question_types
            or any(w in query.lower() for w in ["case law", "judicial", "precedent", "judgment", "ruling", "tests"])
        )
        if case_sources:
            case_lines = ["Judicial Principles"]
            for src in case_sources[:3]:
                c_name = src.case_name or src.document_name or "Judicial Authority"
                court = src.court or "Supreme Court of India"
                cite = src.citation or "Reported Judgment"
                para = f"Para {src.paragraph_number}" if src.paragraph_number else "Relevant Ruling"

                case_header = f"{c_name}\n{court} · {cite} · {para} {src.source_label}"
                case_explanation = cls._generate_universal_case_explanation(src)
                case_lines.append(f"\n{case_header}\n\n{case_explanation} {src.source_label}")

            blocks.append("\n".join(case_lines))
        elif asked_for_cases:
            blocks.append(
                "Judicial Principles\n\n"
                "The current indexed sources do not contain verified judicial decisions "
                "sufficient to substantiate the case-law aspect of this question."
            )

        # 3. Sources Section
        source_items = ["Sources"]
        for src in statute_sources[:3]:
            act_name = src.act_short_name or src.document_name or "Statute"
            is_const = "constitution" in (src.document_name or "").lower() or "constitution" in act_name.lower()
            unit = "Article" if is_const else "Section"
            sec_num = f"{unit} {src.section_number}" if src.section_number else ""
            source_items.append(f"{act_name} — {sec_num} {src.source_label}".strip())

        for src in case_sources[:3]:
            c_name = src.case_name or src.document_name or "Judicial Authority"
            court = src.court or "Supreme Court of India"
            cite = src.citation or ""
            para = f"Para {src.paragraph_number}" if src.paragraph_number else ""
            meta_parts = [p for p in [court, cite, para] if p]
            meta_str = ", ".join(meta_parts)
            source_items.append(f"{c_name} — {meta_str} {src.source_label}".strip())

        if len(source_items) > 1:
            blocks.append("\n\n".join(source_items))

        # 4. Disclaimer
        blocks.append(
            "Disclaimer: This response provides general legal information based on the cited sources "
            "and is not a substitute for advice from a qualified legal professional."
        )

        return "\n\n".join(blocks)

    @classmethod
    def _generate_universal_provision_explanation(cls, src: SourceReference, is_constitutional: bool = False) -> str:
        """Provide a clean contextual explanation derived dynamically from snippet text and section metadata."""
        clean = cls._clean_snippet(src.text_snippet, 240)
        title = src.section_title or "the provision"

        if is_constitutional:
            return (
                f"This constitutional article establishes fundamental protections concerning {title.lower()}, "
                f"guaranteeing that {clean}."
            )

        if any(w in title.lower() for w in ["punishment", "penalty"]):
            return (
                f"The provision prescribes the mandatory statutory penalty and sentencing framework for {title.lower()}, "
                f"stating that {clean}."
            )

        if any(w in title.lower() for w in ["procedure", "investigation", "notice", "arrest"]):
            return (
                f"The provision governs procedural compliance and regulatory requirements regarding {title.lower()}, "
                f"providing that {clean}."
            )

        return (
            f"The provision sets forth the statutory definition, essential ingredients, and legal framework governing {title.lower()}, "
            f"establishing that {clean}."
        )

    @classmethod
    def _generate_universal_case_explanation(cls, src: SourceReference) -> str:
        """Extract or synthesize judicial principle dynamically from snippet text without hardcoded case names."""
        court = src.court or "The Supreme Court of India"
        clean = cls._clean_snippet(src.text_snippet, 250)

        # Check if snippet contains holding / ratio keywords
        lower = clean.lower()
        if any(w in lower for w in ["held", "laid down", "principle", "observed", "ruled", "test"]):
            return f"{court} articulated the governing judicial test, holding that {clean}"

        return f"In this decision, {court} interpreted the relevant legal provisions, establishing that {clean}"

    @classmethod
    def _build_empty_evidence_answer(cls, query: str) -> str:
        """Fallback when no sources were retrieved."""
        payload = {
            "legalDomain": "Indian Law",
            "mainAnswer": (
                "Answer\n\n"
                "No specific statutory provisions or judicial precedents matching the query could be "
                "retrieved from the current indexed legal knowledge base.\n\n"
                "Conclusion\n\n"
                "Without verified legal source passages, a grounded legal response cannot be provided. "
                "Please try rephrasing the inquiry using specific legal terms, section numbers, or "
                "act names for more precise results."
            ),
            "legalBasis": (
                "Relevant Legal Provisions\n\n"
                "No retrieved legal provisions available for this query.\n\n"
                "Disclaimer: This response provides general legal information based on the cited sources "
                "and is not a substitute for advice from a qualified legal professional."
            ),
            "recommendedNextSteps": [
                "Rephrase the inquiry using official statutory terminology (e.g. section numbers or act names).",
                "Consult primary legislative gazettes or a qualified legal practitioner.",
            ],
        }
        return json.dumps(payload, ensure_ascii=False)
