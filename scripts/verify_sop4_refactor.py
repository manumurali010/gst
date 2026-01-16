import os
import sys
from unittest.mock import MagicMock

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

# Mocking external dependencies
sys.modules['openpyxl'] = MagicMock()
sys.modules['fitz'] = MagicMock() # PyMuPDF
sys.modules['pdfplumber'] = MagicMock()

import services.scrutiny_parser as sp
from services.scrutiny_parser import ScrutinyParser

def verify_sop4_refactor():
    print("--- Verifying SOP-4 Refactor ---")
    
    # ---------------------------------------------------------
    # Scenario A: Primary Path (GSTR-3B + GSTR-2B Present)
    # ---------------------------------------------------------
    print("\n[Scenario A] Primary Path (3B + 2B)...")
    parser = ScrutinyParser()
    parser._extract_metadata = MagicMock(return_value={"gstin": "27AAAAA0000A1Z5", "fy": "2023-24"})
    parser._check_sop_guard = MagicMock(return_value=(False, {})) # Ensure we don't trip guards
    
    # Mock SOP-3 to avoid crash in prior steps if called
    sp.parse_gstr3b_pdf_table_4_a_4 = MagicMock(return_value=None) 
    
    # MOCK 3B Table 4(A)(5) - All Other ITC
    # Value: 1000 each
    sp.parse_gstr3b_pdf_table_4_a_5 = MagicMock(return_value={
        "igst": 1000.0, "cgst": 1000.0, "sgst": 1000.0, "cess": 100.0
    })
    
    # MOCK 2B - All Other ITC
    # Value: 800 each (Shortfall 200)
    mock_analyzer = MagicMock()
    mock_analyzer.get_all_other_itc_raw_data.return_value = {
        "igst": 800.0, "cgst": 800.0, "sgst": 800.0, "cess": 80.0
    }
    # Also mock SOP-3 call on analyzer
    mock_analyzer.get_isd_raw_data.return_value = None
    
    sp.GSTR2BAnalyzer = MagicMock(return_value=mock_analyzer)
    
    extra_files = {
        'gstr3b_pdf': ['dummy_3b.pdf'],
        'gstr_2b': ['dummy_2b.xlsx']
    }
    
    os.path.exists = MagicMock(return_value=True) # For file checks
    
    # Run
    res = parser.parse_file("dummy_excel.xlsx", extra_files=extra_files)
    issues = res.get('issues', [])
    sop4 = next((i for i in issues if i.get('issue_id') == "ITC_3B_2B_OTHER"), None)
    
    if sop4:
        print(f"Status: {sop4.get('status')} (Expected: fail)")
        print(f"Total Shortfall: {sop4.get('total_shortfall')} (Expected: 200*3 + 20 = 620.0 ? No, logic check needed)")
        
        # Check Computation
        # 3B: 1000, 1000, 1000, 100
        # 2B: 800, 800, 800, 80
        # Diff: 200, 200, 200, 20
        # Liab: 200, 200, 200, 20 -> Sum = 620.0
        
        if sop4.get('total_shortfall') == 620.0:
            print("SUCCESS: Computation Correct.")
        else:
            print(f"FAIL: Computation Error. Got {sop4.get('total_shortfall')}")
            
        # Check Schema
        st = sop4.get('summary_table', {})
        if 'columns' in st:
            print("SUCCESS: 'columns' key present.")
        else:
            print("FAIL: 'columns' key missing.")
            
        rows = st.get('rows', [])
        if len(rows) == 4:
            print("SUCCESS: 4 Rows present.")
            # Verify Canoncial Format
            if isinstance(rows[0].get('col1'), dict) and 'value' in rows[0]['col1']:
                print("SUCCESS: Canonical Cell Format Verified.")
            else:
                 print(f"FAIL: Invalid Cell Format: {rows[0].get('col1')}")
        else:
            print(f"FAIL: Row count {len(rows)}")

    else:
        print("FAIL: SOP-4 Issue Not Generated in Primary Path.")

    # ---------------------------------------------------------
    # Scenario B: Fallback Path (No Source Files)
    # ---------------------------------------------------------
    print("\n[Scenario B] Fallback Path (Excel Only)...")
    
    # Reset mocks to simulate missing files
    sp.GSTR2BAnalyzer = MagicMock(side_effect=Exception("Should not be called if files missing"))
    
    parser_fb = ScrutinyParser()
    parser_fb._extract_metadata = MagicMock(return_value={"gstin": "27AAAAA0000A1Z5", "fy": "2023-24"})
    parser_fb._check_sop_guard = MagicMock(return_value=(False, {}))
    
    # Mock legacy function behavior
    parser_fb._parse_group_b_itc_summary = MagicMock(return_value={
        "issue_id": "ITC_3B_2B_OTHER", "status": "legacy_fallback_ok"
    })
    
    # No extra files provided
    res_fb = parser_fb.parse_file("legacy_excel.xlsx", extra_files={})
    issues_fb = res_fb.get('issues', [])
    sop4_fb = next((i for i in issues_fb if i.get('issue_id') == "ITC_3B_2B_OTHER"), None)
    
    if sop4_fb and sop4_fb.get('status') == "legacy_fallback_ok":
        print("SUCCESS: Fallback logic triggered correctly.")
    else:
        print(f"FAIL: Fallback not triggered. Got: {sop4_fb}")

if __name__ == "__main__":
    verify_sop4_refactor()
