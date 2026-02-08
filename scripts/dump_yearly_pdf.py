import fitz
import sys

def analyze_pdf(file_path):
    print(f"Analyzing: {file_path}")
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
    
    # Dump first 2000 chars to see headers and layout
    print("--- TEXT DUMP (FIRST 2000 CHARS) ---")
    print(full_text[:2000].encode('ascii', 'ignore').decode('ascii'))
    
    print("\n--- TEXT DUMP (TABLE 4 SECTION) ---")
    # Find Table 4 area
    idx4 = full_text.find("4. Eligible ITC")
    if idx4 != -1:
        print(full_text[idx4:idx4+2000].encode('ascii', 'ignore').decode('ascii'))
    else:
        print("Table 4 Header not found via simple string.")

if __name__ == "__main__":
    analyze_pdf(r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf")
