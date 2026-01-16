import fitz # PyMuPDF
import re

gstr1_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR-1_IFF_32AAMFM4610Q1Z0_032023.pdf"
gstr3b_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"

def extract_gstr3b_31a(path):
    print(f"--- Analyzing GSTR-3B: {path} ---")
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        # Search for Table 3.1 (a)
        # Pattern: (a) Outward taxable supplies... <Taxable> <IGST> <CGST> <SGST> <Cess>
        # Note: PDF text order varies.
        # Simplified: Look for "(a) Outward taxable supplies" and grab numbers nearby.
        print("Extracted Text Fragment (3.1):")
        start = text.find("(a) Outward taxable supplies")
        if start != -1:
            print(text[start:start+500])
        else:
            print("Table 3.1(a) not found.")
            
    except Exception as e:
        print(f"Error 3B: {e}")

def extract_gstr1_total(path):
    print(f"\n--- Analyzing GSTR-1: {path} ---")
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        print("Extracted Text Fragment (Total Liability):")
        # Look for "Total Liability" or "17. Total Liability"
        # Since this is a summary PDF, format might vary.
        if "Total Liability" in text:
             idx = text.find("Total Liability")
             print(text[idx:idx+500])
        else:
             print("Total Liability key not found.")

    except Exception as e:
        print(f"Error GSTR-1: {e}")

extract_gstr3b_31a(gstr3b_path)
extract_gstr1_total(gstr1_path)
