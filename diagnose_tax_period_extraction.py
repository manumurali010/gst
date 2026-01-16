
import re
import datetime

def diagnose_extraction(text, label):
    print(f"\n--- Diagnosing: {label} ---")
    print(f"Raw Text Snippet (first 200 chars): {text[:200]!r}...")

    extracted_meta = {}

    # 1. Explicit FY Match
    # Regex from FileValidationService
    regex_fy = r"(?:Financial Year|Year)\s*[:\.]?\s*(20\d{2}-[0-9]{2,4})"
    print(f"Applied Regex (FY): {regex_fy}")
    
    fy_match = re.search(regex_fy, text, re.IGNORECASE)
    if fy_match:
        print(f"  -> MATCH FY: {fy_match.group(1)}")
        extracted_meta['fy'] = fy_match.group(1)
    else:
        print("  -> NO MATCH (FY)")

    # 2. Month-Year Match (Monthly Return)
    # Regex from FileValidationService
    regex_month = r"(?:April|May|June|July|August|September|October|November|December|January|February|March)\s*[\s\S]{0,5}\s*(20\d{2})"
    print(f"Applied Regex (Month-Year): {regex_month}")
    
    date_match = re.search(regex_month, text, re.IGNORECASE)
    if date_match:
        print(f"  -> MATCH Month-Year: {date_match.group(0)}")
        # Logic in Service: "We could infer, but for Phase-1 we rely on explicit FY or WARN. pass"
        print("  -> LOGIC ACTION: Pass (No extraction)")
    else:
        print("  -> NO MATCH (Month-Year)")

    return extracted_meta

# Test Cases
samples = [
    ("GSTIN: 29ABCDE1234F1Z5\nFinancial Year 2017-18\nPeriod: April", "Explicit FY (Standard)"),
    ("GSTIN: 29ABCDE1234F1Z5\nReturn Period: April 2018\nSome other text", "Monthly Return (No Explicit FY)"),
    ("GSTIN: 29ABCDE1234F1Z5\nPeriod: 04-2018\n", "Numeric Period (04-2018)"),
    ("GSTIN: 29ABCDE1234F1Z5\nYear: 2024-25", "Short Year Label"),
]

for s_text, s_label in samples:
    diagnose_extraction(s_text, s_label)
