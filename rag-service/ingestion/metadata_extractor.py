"""
Metadata extraction and mapping for legal documents.

Maps known Indian statutory/constitutional filenames to their standard canonical names,
legal domain classifications, and metadata.
"""

from pathlib import Path
from typing import Any, Dict, Union


# Canonical mapping for standard Indian legal document filenames
KNOWN_LEGAL_DOCUMENTS: Dict[str, Dict[str, str]] = {
    "constitution_of_india.pdf": {
        "document_name": "Constitution of India",
        "document_type": "Constitution",
        "jurisdiction": "India",
        "language": "English",
        "slug": "constitution_of_india",
    },
    "bns_2023.pdf": {
        "document_name": "Bharatiya Nyaya Sanhita, 2023",
        "document_type": "Criminal Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "bns_2023",
    },
    "bnss_2023.pdf": {
        "document_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "document_type": "Criminal Procedure",
        "jurisdiction": "India",
        "language": "English",
        "slug": "bnss_2023",
    },
    "bsa_2023.pdf": {
        "document_name": "Bharatiya Sakshya Adhiniyam, 2023",
        "document_type": "Evidence Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "bsa_2023",
    },
    "consumer_protection_act.pdf": {
        "document_name": "Consumer Protection Act",
        "document_type": "Consumer Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "consumer_protection_act",
    },
    "it_act.pdf": {
        "document_name": "Information Technology Act",
        "document_type": "Cyber Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "it_act",
    },
    "motor_vehicle_act.pdf": {
        "document_name": "Motor Vehicles Act",
        "document_type": "Transport Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "motor_vehicle_act",
    },
    "motor_vehicles_act.pdf": {
        "document_name": "Motor Vehicles Act",
        "document_type": "Transport Law",
        "jurisdiction": "India",
        "language": "English",
        "slug": "motor_vehicles_act",
    },
    "sexual_harassment_workplace_act_2013.pdf": {
        "document_name": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "document_type": "Labour Law / Women's Rights",
        "legal_domain": "Labour Law / Women's Rights",
        "act_name": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
        "short_title": "Sexual Harassment of Women at Workplace Act, 2013",
        "year": "2013",
        "jurisdiction": "India",
        "language": "English",
        "slug": "sexual_harassment_workplace_act_2013",
    },
    "pocso_act_2012.pdf": {
        "document_name": "The Protection of Children from Sexual Offences Act, 2012",
        "document_type": "Criminal Law / Child Protection",
        "legal_domain": "Criminal Law / Child Protection",
        "act_name": "The Protection of Children from Sexual Offences Act, 2012",
        "short_title": "Protection of Children from Sexual Offences Act, 2012",
        "year": "2012",
        "jurisdiction": "India",
        "language": "English",
        "slug": "pocso_act_2012",
    },
    "right_to_information_act_2005.pdf": {
        "document_name": "The Right to Information Act, 2005",
        "document_type": "Constitutional Law / Administrative Law",
        "legal_domain": "Constitutional Law / Administrative Law",
        "act_name": "The Right to Information Act, 2005",
        "short_title": "Right to Information Act, 2005",
        "year": "2005",
        "jurisdiction": "India",
        "language": "English",
        "slug": "right_to_information_act_2005",
    },
    "right_to_education_act_2009.pdf": {
        "document_name": "The Right of Children to Free and Compulsory Education Act, 2009",
        "document_type": "Education Law / Constitutional Rights",
        "legal_domain": "Education Law / Constitutional Rights",
        "act_name": "The Right of Children to Free and Compulsory Education Act, 2009",
        "short_title": "Right of Children to Free and Compulsory Education Act, 2009",
        "year": "2009",
        "jurisdiction": "India",
        "language": "English",
        "slug": "right_to_education_act_2009",
    },
    "gst_act_2017.pdf": {
        "document_name": "The Goods and Services Tax Act, 2017",
        "document_type": "Tax Law",
        "legal_domain": "Tax Law",
        "act_name": "The Goods and Services Tax Act, 2017",
        "short_title": "Goods and Services Tax Act, 2017",
        "year": "2017",
        "jurisdiction": "India",
        "language": "English",
        "slug": "gst_act_2017",
    },
    "companies_act_2013.pdf": {
        "document_name": "The Companies Act, 2013",
        "document_type": "Corporate Law",
        "legal_domain": "Corporate Law",
        "act_name": "The Companies Act, 2013",
        "short_title": "Companies Act, 2013",
        "year": "2013",
        "jurisdiction": "India",
        "language": "English",
        "slug": "companies_act_2013",
    },
    "insolvency_bankruptcy_code_2016.pdf": {
        "document_name": "The Insolvency and Bankruptcy Code, 2016",
        "document_type": "Corporate Law / Insolvency Law",
        "legal_domain": "Corporate Law / Insolvency Law",
        "act_name": "The Insolvency and Bankruptcy Code, 2016",
        "short_title": "Insolvency and Bankruptcy Code, 2016",
        "year": "2016",
        "jurisdiction": "India",
        "language": "English",
        "slug": "insolvency_bankruptcy_code_2016",
    },
}


def extract_metadata_for_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Infer metadata for a legal PDF based on its filename.

    Args:
        file_path: Path to the target PDF file.

    Returns:
        Dictionary containing document_name, document_type, jurisdiction,
        language, slug, source_filename, and source_path.
    """
    path = Path(file_path)
    filename_lower = path.name.lower()

    if filename_lower in KNOWN_LEGAL_DOCUMENTS:
        meta = KNOWN_LEGAL_DOCUMENTS[filename_lower].copy()
    else:
        # Fallback for unrecognized or additional legal documents
        fallback_name = path.stem.replace("_", " ").replace("-", " ").title()
        meta = {
            "document_name": fallback_name,
            "document_type": "Unknown",
            "jurisdiction": "India",
            "language": "English",
            "slug": path.stem.lower(),
        }

    meta["source_filename"] = path.name
    meta["source_path"] = str(path).replace("\\", "/")
    return meta
