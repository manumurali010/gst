import fitz
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')


def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"Analyzing {pdf_path}")
    
    for page in doc:
        text = page.get_text("blocks")
        # sort by vertical position
        text.sort(key=lambda b: b[1])
        

        for i, b in enumerate(text):
            content = b[4].strip()
            # print all blocks around 6.1
            if "6.1" in content or "Payment of tax" in content:
                print(f"--- FOCAL POINT {i} ---")
                for j in range(max(0, i), min(len(text), i + 20)):
                     print(f"BLOCK {j}: {text[j][4].strip()} | Rect: {text[j][:4]}")


if __name__ == "__main__":
    pdf_path = r"c:\Users\manum\.gemini\antigravity\gst\GSTR3B_32AAFCP2036B1Z5_032023.pdf"
    # analyze_pdf(pdf_path) # Comment out analysis block printing
    
    print("\n--- Testing Parser Function ---")
    try:
        from src.utils.pdf_parsers import parse_gstr3b_pdf_table_6_1_cash
        res = parse_gstr3b_pdf_table_6_1_cash(pdf_path)
        print(f"Parser Result: {res}")
    except Exception as e:
        print(f"Parser Error: {e}")

