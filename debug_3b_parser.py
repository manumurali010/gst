import fitz
import re
import sys
import os

pdf_path = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"

def debug_3b(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Analyzing: {file_path}")
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()

    print("\n--- RAW TEXT DUMP (Start) ---")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass # If fails, fallback to replacement printing
    print(full_text[:2000])
    
    # Locate section 3.1
    idx_31 = full_text.find("3.1 Details")
    if idx_31 != -1:
        print(f"\n--- Found '3.1 Details' at index {idx_31} ---")
        print(full_text[idx_31:idx_31+2000])
    else:
        print("\n--- '3.1 Details' NOT FOUND ---")
        
    # Search for "Outward"
    idx_out = full_text.find("Outward taxable supplies")
    if idx_out != -1:
        print(f"\n--- Found 'Outward taxable supplies' at {idx_out} ---")
        print(full_text[max(0, idx_out-100):idx_out+500])

if __name__ == "__main__":
    debug_3b(pdf_path)
