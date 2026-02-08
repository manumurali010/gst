
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.utils.pdf_parsers import parse_gstr3b_sop9_identifiers
except ImportError:
    sys.path.append(os.getcwd())
    from src.utils.pdf_parsers import parse_gstr3b_sop9_identifiers

def validate_parser(pdf_path):
    print(f"--- Testing SOP-9 Parser on: {os.path.basename(pdf_path)} ---")
    if not os.path.exists(pdf_path):
        print("File not found.")
        return

    meta = parse_gstr3b_sop9_identifiers(pdf_path)
    print(f"Result: {meta}")
    
    if meta['filing_date'] == '20/03/2023' and meta['month'] == 'February' and meta['fy'] == '2022-23':
        print(">>> SUCCESS: Extraction matches expected sample values.")
    else:
        print(">>> FAIL: Extraction mismatch.")

if __name__ == "__main__":
    sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    validate_parser(sample_pdf)
