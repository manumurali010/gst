import fitz
import os
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "GSTR3B_32AAMFM4610Q1Z0_032023.pdf"

def dump_text():
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"Dumping text for {pdf_path}...")
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            print(f"--- PAGE {i+1} START ---")
            text = page.get_text()
            print(text)
            print(f"--- PAGE {i+1} END ---")
            
            # Search for keyword
            if "All other ITC" in text:
                print("KEYWORD FOUND ON THIS PAGE")
            else:
                print("KEYWORD NOT FOUND ON THIS PAGE")
                
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    dump_text()
