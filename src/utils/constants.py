import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

TAXPAYERS_FILE = os.path.join(DATA_DIR, 'taxpayers.csv')
CASES_FILE = os.path.join(DATA_DIR, 'cases.csv')
CASE_FILES_FILE = os.path.join(DATA_DIR, 'case_files.csv')
SECTIONS_FILE = os.path.join(DATA_DIR, 'sections.txt')
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.txt')

# GST Constants
PROCEEDING_TYPES = [
    "Section 61 (Scrutiny of returns)",
    "Section 62 (Assessment of non-filers of returns)",
    "Section 63 (Assessment of unregistered persons)",
    "Section 73 (Determination of tax not paid - non-fraud)",
    "Section 74 (Determination of tax - willful misstatement or fraud)",
    "Section 74A (Determination of tax - special cases)",
    "Section 64 (Summary assessment)",
    "Section 122 (Penalty for certain offences)",
    "Section 125 (General Penalty)",
    "Section 129 (Detention, seizure and release of goods)",
    "Section 130 (Confiscation of goods or conveyances)"
]

FORMS_MAP = {
    "Section 61": ["ASMT-10"],
    "Section 62": ["ASMT-13"],
    "Section 63": ["ASMT-14", "ASMT-15"],
    "Section 73": ["DRC-01A", "SCN", "Order-in-Original"],
    "Section 74": ["DRC-01A", "SCN", "Order-in-Original"],
    "Section 74A": ["DRC-01A", "SCN", "Order-in-Original"],
    "Section 129": ["MOV-06", "MOV-07", "MOV-09", "MOV-10"],
    "Section 130": ["MOV-10", "MOV-11"],
    "Default": ["DRC-01", "DRC-01A", "DRC-02", "DRC-03", "DRC-07", "RFD-01", "REG-17", "SCN", "Order"]
}

TAX_TYPES = ["CGST", "SGST", "IGST", "CESS"]
