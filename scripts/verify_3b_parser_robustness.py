import os
import sys
import re

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from utils.pdf_parsers import parse_gstr3b_pdf_table_4_a_5
import fitz

pdf_path = "GSTR3B_32AAMFM4610Q1Z0_032023.pdf"

def verify_3b():
    if not os.path.exists(pdf_path):
        print("PDF not found.")
        return

    print(f"Testing Parser on {pdf_path}...")
    res = parse_gstr3b_pdf_table_4_a_5(pdf_path)
    print(f"Parser Result: {res}")
    
    if res is None:
        print("Parsing Failed. Dumping Text around 'All other ITC'...")
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            if "All other ITC" in text:
                print(f"--- PAGE {page.number} MATCH ---")
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if "All other ITC" in line:
                        print(f"Context [-2:+5]:")
                        for j in range(max(0, i-2), min(len(lines), i+6)):
                             print(f"L{j}: {repr(lines[j])}")

if __name__ == "__main__":
    verify_3b()
