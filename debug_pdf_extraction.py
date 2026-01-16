
import fitz
import re
from datetime import datetime

file_path = "GSTR3B_32AADFW8764E1Z1_042022.pdf"

print(f"--- Analyzing {file_path} ---")

try:
    doc = fitz.open(file_path)
    text = ""
    for i in range(min(3, len(doc))):
        page_text = doc[i].get_text()
        print(f"\n[PAGE {i+1} RAW START]")
        # Safe Print
        safe_text = page_text[:500].encode('ascii', 'replace').decode('ascii')
        print(safe_text) 
        print(f"[PAGE {i+1} RAW END]")
        text += page_text + "\n"
    doc.close()
    
    print("\n--- Applying Regex ---")
    
    # 1. Explicit FY
    fy_match = re.search(r"(?:Financial Year|Year)\s*[:\.]?\s*(20\d{2}-[0-9]{2,4})", text, re.IGNORECASE)
    print(f"Explicit FY Match: {fy_match.group(1) if fy_match else 'None'}")
    
    # 2. Month Year
    date_match = re.search(r"(April|May|June|July|August|September|October|November|December|January|February|March)\s*[\s\S]{0,5}\s*(20\d{2})", text, re.IGNORECASE)
    print(f"Month-Year Match: {date_match.groups() if date_match else 'None'}")

    # 3. Period Numeric
    period_match = re.search(r"(?:Period|Month)\s*[:\-\.]?\s*(\d{2})[/\-](\d{4})", text, re.IGNORECASE)
    print(f"Period (Numeric) Match: {period_match.groups() if period_match else 'None'}")
    
    # 4. GSTIN
    gstin_match = re.findall(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", text, re.IGNORECASE)
    print(f"GSTIN Candidates: {list(set(gstin_match))}")

except Exception as e:
    print(f"Error: {e}")
