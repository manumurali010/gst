
import os
import sys
import json
import logging

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.services.scrutiny_parser import ScrutinyParser
except ImportError:
    sys.path.append(os.getcwd())
    from src.services.scrutiny_parser import ScrutinyParser

def test_sop9_integration():
    print("--- Starting SOP-9 Integration Test ---")
    
    # 1. Setup
    parser = ScrutinyParser()
    sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return

    # 2. Prepare Arguments
    # parse_file(self, file_path, extra_files=None, configs=None, gstr2a_analyzer=None)
    # expected: file_path=None (no excel), extra_files={'gstr3b_test': pdf_path}
    
    extra_files = {
        "gstr3b_monthly_feb": sample_pdf
    }
    
    # 3. Execute
    print("Invoking parse_file...")
    try:
        result = parser.parse_file(file_path=None, extra_files=extra_files)
        
        # 4. Analyze Results
        issues = result.get('issues', [])
        print(f"Total Issues Returned: {len(issues)}")
        
        sop9_issue = next((i for i in issues if i.get('issue_id') == 'SEC_16_4_VIOLATION'), None)
        
        if sop9_issue:
            print(f">>> SOP-9 Found!")
            print(f"Status: {sop9_issue.get('status')}")
            print(f"Message: {sop9_issue.get('status_msg')}")
            print(f"Total Shortfall: {sop9_issue.get('total_shortfall')}")
            
            # Check Table
            tbl = sop9_issue.get('summary_table', {})
            rows = tbl.get('rows', [])
            print(f"Rows ({len(rows)}):")
            for r in rows:
                print(r)
                
            # Verify Logic
            # FY 2022-23 -> Cutoff 30 Nov 2023.
            # ARN Date 20/03/2023.
            # 20 Mar 2023 <= 30 Nov 2023 -> PASS.
            
            if sop9_issue['status'] == 'pass':
                print(">>> SUCCESS: Status is PASS as expected (Mar 2023 < Nov 2023)")
            else:
                print(">>> FAIL: Status should be PASS")
                
        else:
            print(">>> FAIL: SOP-9 Issue NOT found in payload.")
            
    except Exception as e:
        print(f"Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sop9_integration()
