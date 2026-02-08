
import fitz
import sys
import os

def dump_text(pdf_path, output_path):
    print(f"--- Text Dump: {os.path.basename(pdf_path)} ---")
    try:
        doc = fitz.open(pdf_path)
        with open(output_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(doc):
                f.write(f"--- Page {i+1} ---\n")
                text = page.get_text()
                f.write(text)
                f.write("\n--- End of Page Snippet ---\n")
        doc.close()
        print(f"Dumped to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    dump_text(sample_pdf, "pdf_dump.txt")
