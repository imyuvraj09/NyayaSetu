"""
Legal Concept Mapper for NyayaSetu Assistant.

Provides maintainable statutory concept mappings, keyword expansions,
and candidate statutory provisions to improve retrieval recall without
hardcoding answers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ConceptMapping:
    """Represents a legal concept with statutory synonyms, expansions, and candidate sections."""
    canonical_concept: str
    related_terms: List[str] = field(default_factory=list)
    statutory_phrases: List[str] = field(default_factory=list)
    section_candidates: Dict[str, List[str]] = field(default_factory=dict)
    # section_candidates maps document_id -> list of section numbers


LEGAL_CONCEPT_REGISTRY: List[ConceptMapping] = [
    ConceptMapping(
        canonical_concept="murder",
        related_terms=[
            "murder", "culpable homicide", "circumstances constituting murder",
            "punishment for murder", "death or imprisonment for life",
            "intention of causing death", "bodily injury sufficient in the ordinary course of nature",
            "imminently dangerous act", "grave and sudden provocation", "exceptions to murder"
        ],
        statutory_phrases=[
            "culpable homicide is murder", "whoever commits murder", "shall be punished with death or imprisonment for life",
            "punishment for murder", "culpable homicide not amounting to murder"
        ],
        section_candidates={
            "bns_2023": ["100", "101", "102", "103", "104", "105"],
        },
    ),
    ConceptMapping(
        canonical_concept="culpable homicide",
        related_terms=[
            "culpable homicide", "causing death", "intention of causing death",
            "knowledge that act is likely to cause death", "culpable homicide not amounting to murder"
        ],
        statutory_phrases=[
            "whoever causes death by doing an act", "culpable homicide not amounting to murder",
            "punishment for culpable homicide"
        ],
        section_candidates={
            "bns_2023": ["100", "101", "105"],
        },
    ),
    ConceptMapping(
        canonical_concept="punishment for murder",
        related_terms=[
            "punishment for murder", "death", "imprisonment for life", "fine",
            "capital punishment", "life sentence"
        ],
        statutory_phrases=[
            "whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine",
            "punishment for murder"
        ],
        section_candidates={
            "bns_2023": ["103", "104"],
        },
    ),
    ConceptMapping(
        canonical_concept="electronic records",
        related_terms=[
            "electronic record", "electronic records", "admissibility of electronic records",
            "digital record", "certificate", "hash value", "computer output", "admissibility"
        ],
        statutory_phrases=[
            "admissibility of electronic records", "information contained in an electronic record",
            "certificate signed by a person in charge"
        ],
        section_candidates={
            "bsa_2023": ["61", "62", "63"],
            "it_act": ["65B", "43", "66"],
        },
    ),
    ConceptMapping(
        canonical_concept="fir",
        related_terms=[
            "fir", "first information report", "information in cognizable cases",
            "reporting of crime", "zero fir", "e-fir"
        ],
        statutory_phrases=[
            "information in cognizable cases", "every information relating to the commission of a cognizable offence",
            "shall be reduced to writing by or under the direction of the officer in charge of a police station"
        ],
        section_candidates={
            "bnss_2023": ["173", "174", "175", "176"],
        },
    ),
    ConceptMapping(
        canonical_concept="investigation",
        related_terms=[
            "investigate", "investigated", "investigation", "how is a murder case investigated",
            "how is a case investigated", "police investigation", "inquest", "search",
            "seizure", "examination of witnesses", "case investigated"
        ],
        statutory_phrases=[
            "procedure for investigation", "police officer's power to investigate",
            "examination of witnesses by police", "report of police officer on completion of investigation"
        ],
        section_candidates={
            "bnss_2023": ["175", "176", "179", "180", "193"],
        },
    ),
    ConceptMapping(
        canonical_concept="evidence relevance",
        related_terms=[
            "evidence", "evidence is relevant", "relevant evidence", "relevancy",
            "murder trial", "facts relevant", "proof", "admissible evidence", "trial evidence"
        ],
        statutory_phrases=[
            "relevancy of facts", "facts necessary to explain or introduce relevant facts",
            "things said or done by conspirator in reference to common design",
            "dying declaration", "burden of proof", "the evidence is admissible"
        ],
        section_candidates={
            "bsa_2023": ["4", "5", "6", "7", "8", "26", "45", "104", "105", "159"],
        },
    ),
    ConceptMapping(
        canonical_concept="arrest",
        related_terms=[
            "arrest", "arrest without warrant", "procedure of arrest", "rights of arrested person",
            "memorandum of arrest"
        ],
        statutory_phrases=[
            "when police may arrest without warrant", "procedure of arrest and duties of officer making arrest",
            "person arrested to be informed of grounds of arrest and of right to bail"
        ],
        section_candidates={
            "bnss_2023": ["35", "36", "37", "47", "48"],
        },
    ),
    ConceptMapping(
        canonical_concept="bail",
        related_terms=[
            "bail", "anticipatory bail", "bailable offence", "non-bailable offence",
            "default bail", "regular bail"
        ],
        statutory_phrases=[
            "in what cases bail to be taken", "when bail may be taken in case of non-bailable offence",
            "direction for grant of bail to person apprehending arrest"
        ],
        section_candidates={
            "bnss_2023": ["478", "479", "480", "482"],
        },
    ),
    ConceptMapping(
        canonical_concept="theft",
        related_terms=[
            "theft", "dishonest intention", "movable property", "taking without consent"
        ],
        statutory_phrases=[
            "whoever, intending to take dishonestly any movable property", "punishment for theft"
        ],
        section_candidates={
            "bns_2023": ["303", "304", "305"],
        },
    ),
    ConceptMapping(
        canonical_concept="cheating",
        related_terms=[
            "cheating", "fraud", "dishonest inducement", "delivery of property"
        ],
        statutory_phrases=[
            "whoever, by deceiving any person, fraudulently or dishonestly induces", "punishment for cheating"
        ],
        section_candidates={
            "bns_2023": ["318", "319"],
        },
    ),
    ConceptMapping(
        canonical_concept="fundamental rights",
        related_terms=[
            "fundamental rights", "article 21", "right to life", "personal liberty",
            "article 14", "equality before law", "article 19", "writ petition"
        ],
        statutory_phrases=[
            "protection of life and personal liberty", "equality before the law",
            "remedies for enforcement of rights conferred by this Part"
        ],
        section_candidates={
            "constitution_of_india": ["14", "19", "21", "22", "32", "226"],
        },
    ),
    ConceptMapping(
        canonical_concept="child sexual offences",
        related_terms=[
            "pocso", "penetrative sexual assault", "aggravated penetrative sexual assault",
            "sexual assault", "sexual harassment of a child"
        ],
        statutory_phrases=[
            "penetrative sexual assault", "punishment for penetrative sexual assault"
        ],
        section_candidates={
            "pocso_act_2012": ["3", "4", "5", "6", "7", "8"],
        },
    ),
    ConceptMapping(
        canonical_concept="workplace sexual harassment",
        related_terms=[
            "posh", "sexual harassment at workplace", "internal committee", "icc",
            "complaint of sexual harassment", "inquiry into complaint"
        ],
        statutory_phrases=[
            "constitution of internal complaints committee", "complaint of sexual harassment",
            "inquiry into complaint"
        ],
        section_candidates={
            "sexual_harassment_workplace_act_2013": ["4", "9", "11", "13"],
        },
    ),
    ConceptMapping(
        canonical_concept="right to information",
        related_terms=[
            "rti", "request for obtaining information", "disposal of request",
            "central information commission", "public information officer", "pio"
        ],
        statutory_phrases=[
            "right to information and obligations of public authorities",
            "request for obtaining information", "exemption from disclosure of information"
        ],
        section_candidates={
            "right_to_information_act_2005": ["3", "4", "6", "7", "8", "19"],
        },
    ),
    ConceptMapping(
        canonical_concept="corporate insolvency",
        related_terms=[
            "ibc", "cirp", "corporate insolvency resolution process", "moratorium",
            "committee of creditors", "resolution plan", "liquidation"
        ],
        statutory_phrases=[
            "initiation of corporate insolvency resolution process by financial creditor",
            "moratorium", "committee of creditors", "approval of resolution plan"
        ],
        section_candidates={
            "insolvency_bankruptcy_code_2016": ["7", "9", "10", "14", "21", "30", "31"],
        },
    ),
]


class LegalConceptMapper:
    """Finds matching legal concepts, expanded keywords, and candidate sections."""

    def __init__(self, registry: Optional[List[ConceptMapping]] = None) -> None:
        self.registry = registry or LEGAL_CONCEPT_REGISTRY

    def map_query_concepts(
        self,
        query: str,
        document_id: Optional[str] = None,
        entities: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Map query to expanded search terms, statutory phrases, and section candidates.

        Args:
            query: User's query text.
            document_id: Detected statute ID (e.g. "bns_2023").
            entities: Extracted entities from query analyzer.

        Returns:
            Tuple of (expanded_keywords, statutory_phrases, candidate_sections).
        """
        lower_query = query.lower()
        active_entities = [e.lower() for e in (entities or [])]

        matched_terms: Set[str] = set()
        matched_phrases: Set[str] = set()
        matched_sections: Set[str] = set()

        for entry in self.registry:
            is_matched = False
            # Check canonical concept
            if entry.canonical_concept in lower_query or entry.canonical_concept in active_entities:
                is_matched = True
            else:
                # Check related terms
                for term in entry.related_terms:
                    if term in lower_query:
                        is_matched = True
                        break

            if is_matched:
                matched_terms.update(entry.related_terms[:6])
                matched_phrases.update(entry.statutory_phrases[:3])

                # Get candidate sections for the target document
                if document_id and document_id in entry.section_candidates:
                    matched_sections.update(entry.section_candidates[document_id])
                elif not document_id:
                    for doc, secs in entry.section_candidates.items():
                        matched_sections.update(secs)

        return (
            sorted(list(matched_terms)),
            sorted(list(matched_phrases)),
            sorted(list(matched_sections)),
        )


_CONCEPT_MAPPER_INSTANCE = None

def get_legal_concept_mapper() -> LegalConceptMapper:
    """Return singleton instance of LegalConceptMapper."""
    global _CONCEPT_MAPPER_INSTANCE
    if _CONCEPT_MAPPER_INSTANCE is None:
        _CONCEPT_MAPPER_INSTANCE = LegalConceptMapper()
    return _CONCEPT_MAPPER_INSTANCE
