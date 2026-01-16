import fitz
import re
import pandas as pd
import os

pdf_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_042022.pdf"
excel_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

print(f"--- Analyzing PDF: {os.path.basename(pdf_path)} ---")
try:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    # Dump relevant section for Table 4
    # Looking for "(D) Ineligible ITC" or similar to bound the fetch, but specifically 4(A)(4) "Inward supplies from ISD"
    print("Extracting text around 'Inward supplies from ISD':")
    
    # Simple window extraction around the keyword
    keyword = "Inward supplies from ISD"
    idx = text.find(keyword)
    if idx != -1:
        start = max(0, idx - 100)
        end = min(len(text), idx + 300)
        print(text[start:end])
    else:
        print("Keyword 'Inward supplies from ISD' not found.")
        # Fallback dump of Table 4 header
        idx_t4 = text.find("4. Eligible ITC")
        if idx_t4 != -1:
             print("Table 4 Header found. Dumping next 500 chars:")
             print(text[idx_t4:idx_t4+500])

    doc.close()
except Exception as e:
    print(f"PDF Error: {e}")

print(f"\n--- Analyzing Excel: {os.path.basename(excel_path)} ---")
try:
    xl = pd.ExcelFile(excel_path)
    print(f"Sheet Names: {xl.sheet_names}")
    
    isd_sheet = next((s for s in xl.sheet_names if "ISD" == s), None) # Strict match based on list
    if isd_sheet:
        print(f"Found ISD Sheet: {isd_sheet}")
        # Parse first 10 rows
        df = xl.parse(isd_sheet, header=None, nrows=10)
        
        # Iterate and print safely
        print("Rows:")
        for idx, row in df.iterrows():
             safe_row = [str(x).encode('ascii', 'replace').decode('ascii') for x in row.tolist()]
             print(f"{idx}: {safe_row}")
             
    isda_sheet = next((s for s in xl.sheet_names if "ISDA" in s), None)
    if isda_sheet:
        print(f"Found ISDA Sheet: {isda_sheet}")
        df_isda = xl.parse(isda_sheet, header=None, nrows=5)
        for idx, row in df_isda.iterrows():
             safe_row = [str(x).encode('ascii', 'replace').decode('ascii') for x in row.tolist()]
             print(f"{idx}: {safe_row}")

except Exception as e:
    print(f"Excel Error: {e}")
