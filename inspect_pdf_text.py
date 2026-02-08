
import fitz
import sys
import os

def dump_text(pdf_path):
    print(f"--- Text Dump: {os.path.basename(pdf_path)} ---")
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            print(f"--- Page {i+1} ---")
            text = page.get_text()
            # Handle encoding for console output
            print(text[:2000].encode('utf-8', errors='replace').decode('utf-8')) 
            print("--- End of Page Snippet ---")
        doc.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    dump_text(sample_pdf)
