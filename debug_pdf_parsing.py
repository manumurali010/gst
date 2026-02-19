
import fitz
import re
import sys
import os

pdf_path = r"c:\Users\manum\.gemini\antigravity\gst\GSTR3B_32AAFCP2036B1Z5_032023.pdf"

def analyze_table_6_1(pdf_path):
    print(f"Analyzing {pdf_path}...")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    found_table = False
    
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        
        if "6.1 Payment of Tax" in text:
            print(f"\n--- Found Table 6.1 on Page {page_num + 1} ---")
            found_table = True
            
            # Extract lines around the table
            lines = text.split('\n')
            start_idx = -1
            for i, line in enumerate(lines):
                if "6.1 Payment of Tax" in line:
                    start_idx = i
                    break
            
            if start_idx != -1:
                print("Context around Table 6.1:")
                for i in range(max(0, start_idx), min(len(lines), start_idx + 30)):
                    print(f"[{i}] {lines[i]}")
                    
                # Try to find (B) Reverse charge
                print("\nSearching for (B) Reverse charge row:")
                for i in range(start_idx, min(len(lines), start_idx + 40)):
                    if "(B)" in lines[i] or "Reverse charge" in lines[i]:
                        print(f"POTENTIAL MATCH [{i}]: {lines[i]}")
                        # Print next few lines which might contain values
                        if i + 1 < len(lines): print(f"  Next: {lines[i+1]}")
                        if i + 2 < len(lines): print(f"  Next+1: {lines[i+2]}")
                        if i + 3 < len(lines): print(f"  Next+2: {lines[i+3]}")

    if not found_table:
        print("Table 6.1 not found in text extraction.")

if __name__ == "__main__":
    if os.path.exists(pdf_path):
        analyze_table_6_1(pdf_path)
    else:
        print(f"File not found: {pdf_path}")
