import pandas as pd
import fitz
import os

EXCEL_FILE = "new sops.xlsx"
GSTR3B_PDF = "GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
GSTR2B_EXCEL = "062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

def analyze_new_sops():
    print(f"\n--- Analyzing {EXCEL_FILE} ---")
    try:
        xl = pd.ExcelFile(EXCEL_FILE, engine='openpyxl')
        print(f"Sheets found: {xl.sheet_names}")
        for sheet in xl.sheet_names:
            print(f"\n[SOP: {sheet}]")
            df = pd.read_excel(xl, sheet_name=sheet)
            print(df.head().to_string())
    except Exception as e:
        print(f"Error reading {EXCEL_FILE}: {e}")

def analyze_pdf():
    print(f"\n--- Analyzing PDF: {GSTR3B_PDF} ---")
    if not os.path.exists(GSTR3B_PDF): return
    try:
        doc = fitz.open(GSTR3B_PDF)
        text = doc[0].get_text()
        # Encode to ascii to avoid console errors
        safe_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(f"Page 1 Text Sample:\n{safe_text[:1000]}")
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    analyze_new_sops()
    analyze_pdf()
