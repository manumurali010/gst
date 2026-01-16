import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.scrutiny_parser import ScrutinyParser

def test_gstr9():
    parser = ScrutinyParser()
    pdf_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GST_39_GSTR9_32AAALC0844J1ZJ_032023 filed on 31-12-2023.pdf"
    
    print("Testing Validation...")
    is_valid, msg = parser.validate_gstr9_pdf(pdf_path, "32AAALC0844J1ZJ", "2022-23")
    print(f"Validation: {is_valid}, Msg: {msg}")
    
    print("\nTesting Analysis with GSTR 9 ONLY (No Excel)...")
    results = parser.parse_file(None, extra_files={'gstr9_yearly': pdf_path})
    
    print(f"Metadata: {results.get('metadata')}")
    print(f"Summary: {results.get('summary')}")
    
    print("\nIssues Found:")
    for issue in results.get('issues', []):
        cat = issue.get('category')
        status = issue.get('status')
        msg = issue.get('status_msg', '-')
        shortfall = issue.get('total_shortfall', 0)
        print(f"[{status.upper()}] {cat}: {msg} (Shortfall: {shortfall})")

if __name__ == "__main__":
    test_gstr9()
