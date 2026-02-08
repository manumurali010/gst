
import fitz
import sys
import os

def dump_text(pdf_path, output_path):
    print(f"--- Dumping Text: {os.path.basename(pdf_path)} -> {output_path} ---")
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for i, page in enumerate(doc):
            full_text += f"\n--- Page {i+1} ---\n"
            full_text += page.get_text()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print("Done.")
        doc.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    pdf_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GST_39_GSTR9_32AAALC0844J1ZJ_032023 filed on 31-12-2023.pdf"
    output_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\gstr9_dump.txt"
    dump_text(pdf_path, output_path)
