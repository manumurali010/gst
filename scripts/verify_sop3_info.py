import os
import sys
from unittest.mock import MagicMock

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

# Mocking external dependencies
sys.modules['openpyxl'] = MagicMock()

import services.scrutiny_parser as sp
from services.scrutiny_parser import ScrutinyParser

def verify_sop3_info():
    parser = ScrutinyParser()
    parser._extract_metadata = MagicMock(return_value={"gstin": "27AAAAA0000A1Z5", "fy": "2023-24"})
    
    # 1. Test case: 3B returns None (Table Missing)
    sp.parse_gstr3b_pdf_table_4_a_4 = MagicMock(return_value=None)
    
    # Mock GSTR-2B Analyzer returns None (ISD row not found)
    mock_analyzer = MagicMock()
    mock_analyzer.get_isd_raw_data.return_value = None
    mock_analyzer.validate_file.return_value = True
    sp.GSTR2BAnalyzer = MagicMock(return_value=mock_analyzer)
    
    extra_files = {
        'gstr3b_pdf': ['some.pdf'],
        'gstr_2b': ['some_2b.xlsx']
    }
    
    parser._check_sop_guard = MagicMock(return_value=(False, {}))
    os.path.exists = MagicMock(return_value=True)
    os.listdir = MagicMock(return_value=[]) 
    
    print("Executing SOP-3 Info Status Verification...")
    result = parser.parse_file("dummy.xlsx", extra_files=extra_files)
    
    issues = result.get('issues', [])
    sop3_issue = next((i for i in issues if i.get('issue_id') == 'ISD_CREDIT_MISMATCH'), None)
    
    if not sop3_issue:
        print("FAIL: SOP-3 issue not found in results")
        return
        
    print(f"Status: {sop3_issue.get('status')}")
    print(f"Status Msg: {sop3_issue.get('status_msg')}")
    
    expected_msg = "GSTR-3B Table 4(A)(4) missing; GSTR-2B ISD row not found"
    if sop3_issue.get('status') == 'info' and expected_msg in sop3_issue.get('status_msg'):
        print("\nSUCCESS: SOP-3 Info Status verified successfully.")
    else:
        print(f"FAIL: Status mismatch. Status={sop3_issue.get('status')}, Msg='{sop3_issue.get('status_msg')}'")

if __name__ == "__main__":
    verify_sop3_info()
