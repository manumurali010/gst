import fitz
import sys
import json

def extract_gstr9_data(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = ""
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        all_text += f"\n--- PAGE {page_num + 1} ---\n"
        all_text += text
        pages_text.append(text)
    
    return all_text, pages_text

if __name__ == "__main__":
    pdf_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GST_39_GSTR9_32AAALC0844J1ZJ_032023 filed on 31-12-2023.pdf"
    all_text, pages_text = extract_gstr9_data(pdf_path)
    
    with open("gstr9_extraction.txt", "w", encoding="utf-8") as f:
        f.write(all_text)
    
    print("Extraction complete. check gstr9_extraction.txt")
