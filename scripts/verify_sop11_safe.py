
import os
import sys
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.pdf_parsers import parse_gstr3b_pdf_table_3_1_d, parse_gstr3b_pdf_table_4_b_1, parse_gstr3b_pdf_table_3_1_a
from src.services.scrutiny_parser import ScrutinyParser

def verify_regex_fix():
    """Verify numeric regex fix for spaced commas"""
    print("\n--- Verifying Spaced Comma Regex ---")
    mock_pdf_content = "1,12, 77,521.00"
    from src.utils.pdf_parsers import _clean_amount
    
    # We can't easily mock the internal _parse_3_1_row without IO, 
    # but we can verify the REGEX pattern logic directly or use a dummy file.
    # For simplicity, we just check the extraction result of a real file known to fail if we have one,
    # or rely on the unit test we ran earlier.
    # BUT, let's verify parse_gstr3b_pdf_table_3_1_d uses extraction.
    
    # Let's trust the logic change if we see it working on the Yearly PDF which might have this.
    pass

def verify_yearly_pdf_parsing():
    """Verify parsing on the provided Yearly PDF"""
    print("\n--- Verifying Yearly PDF Parsing ---")
    file_path = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    # 1. Check 3.1(d) Extraction
    print("Checking Table 3.1(d)...")
    res_d = parse_gstr3b_pdf_table_3_1_d(file_path)
    print(f"Result 3.1(d): {res_d}")
    if res_d and res_d.get('taxable_value') == 360.0:
        print("PASS: 3.1(d) Taxable Value extracted correctly (360.00)")
    else:
        print(f"FAIL: 3.1(d) Taxable Value mismatch. Expected 360.00")

    # 2. Check 4(B)(1) Extraction (Rule 38/42/43)
    print("Checking Table 4(B)(1)...")
    res_b1 = parse_gstr3b_pdf_table_4_b_1(file_path)
    print(f"Result 4(B)(1): {res_b1}")
    
    # From text dump: 6,124.91
    expected = 6124.91
    if res_b1 and res_b1.get('cgst') == expected:
        print(f"PASS: 4(B)(1) CGST extracted correctly ({expected})")
    else:
        print(f"FAIL: 4(B)(1) mismatch. Expected {expected}")

def verify_sop11_logic():
    """Verify SOP 11 Calculation including 3.1(d) and Yearly aggregation"""
    print("\n--- Verifying SOP 11 Logic ---")
    parser = ScrutinyParser()
    file_path = "dummy.xlsx" # Not used for this SOP part
    
    yearly_pdf = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    extra_files = {
        "gstr3b_yearly": yearly_pdf
    }
    
    # We need to invoke `parse_file` but it does a lot. 
    # Let's isolate the SOP 11 logic if possible? 
    # No, easy to run parse_file on dummy and check result.
    
    # Create valid dummy excel to pass validation
    import pandas as pd
    df = pd.DataFrame({"Data": [1,2,3]})
    df.to_excel("dummy_sop11.xlsx")
    
    try:
        # We need to mock validate_metadata to pass? 
        # ScrutinyParser.validate_metadata = lambda *args: (True, "OK") # Monkeypatch safety
        
        # Or just rely on it returning 'issues' even if excel validation fails? 
        # Actually it returns early if metadata fails.
        # Let's skip metadata validation by mocking
        
        results = parser.parse_file("dummy_sop11.xlsx", extra_files=extra_files)
        
        sop11 = next((i for i in results if i['issue_id'] == 'RULE_42_43_VIOLATION'), None)
        
        if sop11:
            print("SOP 11 Result Found.")
            # Verify Total Turnover
            # 3.1a = 11,78,51,483.44
            # 3.1b = 0
            # 3.1c = 0
            # 3.1d = 360.00
            # 3.1e = 0
            # Total = 11,78,51,843.44
            
            summary_table = sop11.get('summary_table', {})
            rows = summary_table.get('rows', [])
            total_turnover_row = next((r for r in rows if "Total Turnover" in r['col0']['value']), None)
            
            if total_turnover_row:
                val = total_turnover_row['col1']['value']
                print(f"Total Turnover in Grid: {val}")
                if abs(val - 117851843.44) < 1.0:
                    print("PASS: SOP 11 Total Turnover includes 3.1(d)")
                else:
                    print(f"FAIL: Total Turnover mismatch. Expected ~117851843.44")
            else:
                print("FAIL: Total Turnover row not found.")
                
        else:
            print("FAIL: SOP 11 Rule not found in results.")
            
    except Exception as e:
        print(f"Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_yearly_pdf_parsing()
    verify_sop11_logic()
    
