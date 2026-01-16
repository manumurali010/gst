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

def verify_sop3_expanded():
    parser = ScrutinyParser()
    
    # Mock configs/metadata
    parser._extract_metadata = MagicMock(return_value={"gstin": "27AAAAA0000A1Z5", "fy": "2023-24"})
    
    # Mock PDF Parser for 3B Table 4(A)(4)
    # Total A: 3000(IGST), 1500(CGST), 1500(SGST), 30(Cess)
    sp.parse_gstr3b_pdf_table_4_a_4 = MagicMock(side_effect=[
        {"igst": 1000.0, "cgst": 500.0, "sgst": 500.0, "cess": 10.0},
        {"igst": 2000.0, "cgst": 1000.0, "sgst": 1000.0, "cess": 20.0}
    ])
    
    # Mock GSTR-2B Analyzer
    # Total B: 2500(IGST), 1200(CGST), 1200(SGST), 15(Cess)
    # Shortfall: 500(IGST) + 300(CGST) + 300(SGST) + 15(Cess) = 1115.0
    mock_analyzer = MagicMock()
    mock_analyzer.get_isd_raw_data.return_value = {"igst": 2500.0, "cgst": 1200.0, "sgst": 1200.0, "cess": 15.0}
    mock_analyzer.validate_file.return_value = True
    
    # Mock GSTR2BAnalyzer class in scrutiny_parser
    sp.GSTR2BAnalyzer = MagicMock(return_value=mock_analyzer)
    
    # ScrutinyParser keys: gstr3b_pdf (PDF), gstr_2b (Excel)
    extra_files = {
        'gstr3b_pdf': ['month1.pdf', 'month2.pdf'],
        'gstr_2b': ['some_2b.xlsx']
    }
    
    parser._check_sop_guard = MagicMock(return_value=(False, {}))
    
    os.path.exists = MagicMock(return_value=True)
    os.listdir = MagicMock(return_value=[]) 
    
    print("Executing SOP-3 Expanded Verification (Schema Check)...")
    result = parser.parse_file("dummy.xlsx", extra_files=extra_files)
    
    issues = result.get('issues', [])
    sop3_issue = next((i for i in issues if i.get('issue_id') == 'ISD_CREDIT_MISMATCH'), None)
    
    if not sop3_issue:
        print("FAIL: SOP-3 issue not found in results")
        return
        
    print(f"Status: {sop3_issue.get('status')}")
    print(f"Total Shortfall: {sop3_issue.get('total_shortfall')}")
    
    summary_table = sop3_issue.get('summary_table')
    if not summary_table:
        print("FAIL: No summary_table found")
        print(f"Issue Content: {sop3_issue}")
        return
        
    # VERIFY COLUMNS KEY
    columns = summary_table.get('columns')
    if not columns:
         print(f"FAIL: 'columns' key missing in summary_table. Keys: {summary_table.keys()}")
         return
    print(f"Columns: {columns}")
        
    rows = summary_table.get('rows', [])
    r0 = rows[0]
    print(f"\nRow 0 (3B): CGST={r0['col1']['value']}, SGST={r0['col2']['value']}, IGST={r0['col3']['value']}, Cess={r0['col4']['value']}")
    
    if r0['col3']['value'] == 3000.0 and sop3_issue['total_shortfall'] == 1115.0 and len(columns) == 5:
        print("\nSUCCESS: SOP-3 Expanded Table schema verified successfully.")
    else:
        print(f"FAIL: Logic/Schema mismatch.")

if __name__ == "__main__":
    verify_sop3_expanded()
