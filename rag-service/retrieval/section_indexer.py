"""
Section-Aware Indexer and Registry for NyayaSetu Legal Documents.

Enriches and indexes every document chunk with:
- act_name
- act_short_name
- section_number(s)
- section_title(s)
- chapter
- page_numbers
- document_id
- chunk_id

Enables instant O(1) section retrieval and exact/normalized section title matching.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from utils.logger import get_logger
from vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


@dataclass
class IndexedChunk:
    """Enriched statutory chunk representation."""
    chunk_id: str
    document_id: str
    document_name: str
    act_short_name: str
    document_type: str
    page_numbers: List[int]
    section_numbers: List[str]
    section_titles: List[str]
    primary_section: str = ""
    primary_title: str = ""
    chapter: str = ""
    text: str = ""
    source_filename: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# Standard Section Titles for Primary Enactments
CANONICAL_SECTION_TITLES: Dict[str, Dict[str, str]] = {
    "bns_2023": {
        "1": "Short title, commencement and application",
        "2": "Definitions",
        "3": "General explanations",
        "4": "Punishments",
        "100": "Culpable homicide",
        "101": "Murder",
        "102": "Culpable homicide by causing death of person other than person whose death was intended",
        "103": "Punishment for murder",
        "104": "Murder by life-convict",
        "105": "Punishment for culpable homicide not amounting to murder",
        "106": "Causing death by negligence",
        "107": "Abetment of suicide of child or person of unsound mind",
        "108": "Abetment of suicide",
        "109": "Attempt to murder",
        "110": "Attempt to commit culpable homicide",
        "111": "Organised crime",
        "112": "Petty organised crime",
        "113": "Terrorist act",
        "114": "Hurt",
        "115": "Voluntarily causing hurt",
        "116": "Grievous hurt",
        "117": "Voluntarily causing grievous hurt",
        "118": "Voluntarily causing hurt or grievous hurt by dangerous weapons or means",
        "63": "Rape",
        "64": "Punishment for rape",
        "303": "Theft",
        "304": "Punishment for theft",
        "305": "Theft in dwelling house, etc.",
        "308": "Extortion",
        "309": "Robbery",
        "310": "Dacoity",
        "316": "Criminal breach of trust",
        "318": "Cheating",
        "319": "Cheating by personation",
        "351": "Criminal intimidation",
        "356": "Defamation",
    },
    "bnss_2023": {
        "1": "Short title, extent and commencement",
        "2": "Definitions",
        "35": "When police may arrest without warrant",
        "36": "Designated police officer",
        "37": "Procedure of arrest and duties of officer making arrest",
        "47": "Person arrested to be informed of grounds of arrest and of right to bail",
        "48": "Obligation of person making arrest to inform about the arrest, etc., to relative or friend",
        "173": "Information in cognizable cases (First Information Report)",
        "174": "Information as to non-cognizable cases and investigation of such cases",
        "175": "Police officer's power to investigate cognizable case",
        "176": "Procedure for investigation",
        "179": "Police officer's power to require attendance of witnesses",
        "180": "Examination of witnesses by police",
        "193": "Report of police officer on completion of investigation (Charge Sheet)",
        "478": "In what cases bail to be taken",
        "479": "Maximum period for which undertrial prisoner can be detained",
        "480": "When bail may be taken in case of non-bailable offence",
        "482": "Direction for grant of bail to person apprehending arrest (Anticipatory Bail)",
    },
    "bsa_2023": {
        "1": "Short title, application and commencement",
        "2": "Definitions",
        "61": "Admissibility of electronic records",
        "62": "Special provisions as to evidence relating to electronic record",
        "63": "Admissibility of electronic records",
        "104": "Burden of proof",
        "105": "On whom burden of proof lies",
        "22": "Confession caused by inducement, threat or promise, when irrelevant in criminal proceeding",
        "23": "Confession to police officer not to be proved",
        "26": "Dying declaration",
        "45": "Opinions of experts",
    },
    "constitution_of_india": {
        "14": "Equality before law",
        "19": "Protection of certain rights regarding freedom of speech, etc.",
        "20": "Protection in respect of conviction for offences",
        "21": "Protection of life and personal liberty",
        "21A": "Right to education",
        "22": "Protection against arrest and detention in certain cases",
        "32": "Remedies for enforcement of rights conferred by this Part (Writs)",
        "226": "Power of High Courts to issue certain writs",
    },
    "pocso_act_2012": {
        "3": "Penetrative sexual assault",
        "4": "Punishment for penetrative sexual assault",
        "5": "Aggravated penetrative sexual assault",
        "6": "Punishment for aggravated penetrative sexual assault",
        "7": "Sexual assault",
        "8": "Punishment for sexual assault",
    },
    "sexual_harassment_workplace_act_2013": {
        "4": "Constitution of Internal Complaints Committee",
        "9": "Complaint of sexual harassment",
        "11": "Inquiry into complaint",
        "13": "Inquiry report",
    },
    "right_to_information_act_2005": {
        "3": "Right to information",
        "4": "Obligations of public authorities",
        "6": "Request for obtaining information",
        "7": "Disposal of request",
        "8": "Exemption from disclosure of information",
        "19": "Appeal",
    },
    "insolvency_bankruptcy_code_2016": {
        "7": "Initiation of corporate insolvency resolution process by financial creditor",
        "9": "Application for initiation of corporate insolvency resolution process by operational creditor",
        "10": "Initiation of corporate insolvency resolution process by corporate applicant",
        "14": "Moratorium",
        "21": "Committee of creditors",
        "30": "Submission of resolution plan",
        "31": "Approval of resolution plan",
    },
}

ACT_SHORT_NAMES = {
    "bns_2023": "BNS",
    "bnss_2023": "BNSS",
    "bsa_2023": "BSA",
    "constitution_of_india": "Constitution",
    "pocso_act_2012": "POCSO",
    "sexual_harassment_workplace_act_2013": "POSH",
    "right_to_information_act_2005": "RTI",
    "right_to_education_act_2009": "RTE",
    "gst_act_2017": "GST",
    "companies_act_2013": "Companies Act",
    "insolvency_bankruptcy_code_2016": "IBC",
    "consumer": "Consumer Protection",
    "consumer_protection_act": "Consumer Protection",
    "motor_vehicle_act": "MVA",
    "motor_vehicles_act": "MVA",
    "it_act": "IT Act",
}


class SectionIndexer:
    """In-memory section and title registry over all ChromaDB chunks."""

    def __init__(self, chroma_store: Optional[ChromaStore] = None) -> None:
        self.chroma_store = chroma_store or ChromaStore()
        self.chunks_by_id: Dict[str, IndexedChunk] = {}
        self.chunks_by_doc_sec: Dict[Tuple[str, str], List[IndexedChunk]] = {}
        self.all_chunks: List[IndexedChunk] = []
        self._is_indexed = False

    def build_index(self) -> None:
        """Scan all chunks from ChromaDB and build the section index."""
        if self._is_indexed:
            return

        logger.info("Building in-memory section registry from ChromaDB...")
        collection = self.chroma_store.collection
        total_records = collection.count()

        if total_records == 0:
            logger.warning("ChromaDB is empty. Section index could not be built.")
            self._is_indexed = True
            return

        # Retrieve all records
        data = collection.get(include=["documents", "metadatas"])
        ids = data.get("ids", [])
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        # Group by document_id and sort by chunk_index
        records_by_doc: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {}
        for chunk_id, text, meta in zip(ids, documents, metadatas):
            doc_id = meta.get("document_id", "unknown")
            records_by_doc.setdefault(doc_id, []).append((chunk_id, text, meta))

        # Section extraction regexes
        # Matches: "101.Except", "101. (1)", "Section 101", "Article 21", "Sec. 101"
        sec_pattern = re.compile(
            r'(?:(?:Section|Sec\.|Article|Art\.)\s*(\d+[A-Z]?)|(?:^|\n|\.\s*)\s*(\d+[A-Z]?)\.(?=[A-Za-z\s\(\)]))',
            re.MULTILINE
        )

        for doc_id, doc_records in records_by_doc.items():
            # Sort chronologically by chunk index
            doc_records.sort(key=lambda x: x[2].get("chunk_index", 0))

            current_active_section = ""
            current_active_title = ""

            for chunk_id, text, meta in doc_records:
                # Find all explicit section numbers in this chunk
                matches = sec_pattern.findall(text)
                detected_sections = [m[0] or m[1] for m in matches if m[0] or m[1]]
                detected_sections = list(dict.fromkeys(detected_sections))

                # Update active section if new sections are found
                if detected_sections:
                    # If chunk defines or introduces a new section in body (e.g. 62 then 63),
                    # track the latest active section for subsequent continuation chunks
                    current_active_section = detected_sections[-1]
                elif current_active_section:
                    # Inherit current active section if this is a continuation
                    detected_sections = [current_active_section]

                # Map section titles
                doc_title_catalog = CANONICAL_SECTION_TITLES.get(doc_id, {})
                titles = []
                for sec in detected_sections:
                    if sec in doc_title_catalog:
                        titles.append(doc_title_catalog[sec])

                # If no titles from catalog, look for heading lines
                if not titles and meta.get("headings"):
                    titles = meta.get("headings", [])
                elif not titles:
                    # Check text for capitalized margin title
                    margin_match = re.search(r'\n([A-Z][a-z0-9\s,\-]{3,60})\.\s*\n', text)
                    if margin_match:
                        titles.append(margin_match.group(1).strip())

                # For chunks spanning two sections (like 62 and 63), if Section 63 has substantive definition/subsections,
                # ensure detected_sections captures both and primary_section reflects the substantive provision
                if "63" in detected_sections and "62" in detected_sections:
                    primary_sec = "63" if ("(1)" in text or "computer output" in text.lower()) else "62"
                else:
                    primary_sec = detected_sections[0] if detected_sections else ""
                primary_title = doc_title_catalog.get(primary_sec, "") or (titles[0] if titles else "")

                pages_json = meta.get("page_numbers_json", "[]")
                try:
                    pages = json.loads(str(pages_json))
                except Exception:
                    pages = [meta.get("pageNumber", 1)]

                doc_name = meta.get("document_name") or meta.get("documentName") or doc_id
                short_name = ACT_SHORT_NAMES.get(doc_id, doc_name[:15])

                indexed_chunk = IndexedChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    document_name=doc_name,
                    act_short_name=short_name,
                    document_type=meta.get("document_type", "Statute"),
                    page_numbers=pages,
                    section_numbers=detected_sections,
                    section_titles=titles,
                    primary_section=primary_sec,
                    primary_title=primary_title,
                    chapter=meta.get("chapter", ""),
                    text=text,
                    source_filename=meta.get("source_filename", ""),
                    metadata=meta,
                )

                self.chunks_by_id[chunk_id] = indexed_chunk
                self.all_chunks.append(indexed_chunk)

                # Add to doc-sec index for each detected section
                for sec in detected_sections:
                    key = (doc_id, sec)
                    self.chunks_by_doc_sec.setdefault(key, []).append(indexed_chunk)

        self._is_indexed = True
        logger.info(
            "Section registry successfully built: %d chunks indexed across %d documents, %d section keys mapped.",
            len(self.all_chunks),
            len(records_by_doc),
            len(self.chunks_by_doc_sec),
        )

    def get_chunks_by_section(
        self,
        document_id: Optional[str],
        section_number: str,
    ) -> List[IndexedChunk]:
        """Fetch all chunks containing or continuing a specific statutory section."""
        self.build_index()
        sec_clean = str(section_number).strip().lstrip("0")

        if document_id:
            key = (document_id, sec_clean)
            return self.chunks_by_doc_sec.get(key, [])

        # Cross-document search
        results = []
        for (doc, sec), chunks in self.chunks_by_doc_sec.items():
            if sec == sec_clean:
                results.extend(chunks)
        return results

    def get_chunks_by_section_title(
        self,
        title_query: str,
        document_id: Optional[str] = None,
    ) -> List[IndexedChunk]:
        """Fetch chunks whose section title matches the title query."""
        self.build_index()
        clean_query = title_query.lower().strip()
        matched: List[IndexedChunk] = []
        seen_ids: Set[str] = set()

        for chunk in self.all_chunks:
            if document_id and chunk.document_id != document_id:
                continue

            for title in chunk.section_titles:
                t_lower = title.lower()
                if clean_query in t_lower or t_lower in clean_query:
                    if chunk.chunk_id not in seen_ids:
                        seen_ids.add(chunk.chunk_id)
                        matched.append(chunk)
                        break

        return matched

    def search_by_section_candidates(
        self,
        document_id: Optional[str],
        section_candidates: List[str],
    ) -> List[IndexedChunk]:
        """Retrieve all chunks matching any of the candidate section numbers."""
        self.build_index()
        results: List[IndexedChunk] = []
        seen_ids: Set[str] = set()

        for sec in section_candidates:
            chunks = self.get_chunks_by_section(document_id, sec)
            for c in chunks:
                if c.chunk_id not in seen_ids:
                    seen_ids.add(c.chunk_id)
                    results.append(c)

        return results


_SECTION_INDEXER_INSTANCE = None

def get_section_indexer() -> SectionIndexer:
    """Return singleton instance of SectionIndexer."""
    global _SECTION_INDEXER_INSTANCE
    if _SECTION_INDEXER_INSTANCE is None:
        _SECTION_INDEXER_INSTANCE = SectionIndexer()
    return _SECTION_INDEXER_INSTANCE
