import pandas as pd
import json
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer
from src.services.scrutiny_parser import ScrutinyParser

def create_mock_sop7_file():
    """Creates a mock GSTR-2A file with B2B sheet for testing SOP-7"""
    filename = "mock_sop7_test.xlsx"
    
    # Create Data
    data = {
        'GSTIN of Supplier': ['29ABCDE1234F1Z5', '29ABCDE1234F1Z5', '29XYZDE1234F1Z5'],
        'Invoice Number': ['INV-001', 'INV-002', 'INV-003'],
        'Invoice Date': ['01-Jan-2024', '15-Mar-2024', '01-Jan-2024'],
        'Effective Date of Cancellation': ['01-Feb-2024', '01-Feb-2024', ''], # Supplier 1 Cancelled on Feb 1
        'IGST': [5000, 2000, 100],
        'CGST': [0, 0, 0],
        'SGST': [0, 0, 0]
    }
    # Expected: INV-002 is AFTER Cancellation (Mar 15 > Feb 1) -> Should be flagged.
    # INV-001 is BEFORE -> Should be ignored.
    # INV-003 -> Supplier not cancelled -> Ignored.
    
    df = pd.DataFrame(data)
    with pd.ExcelWriter(filename) as writer:
        df.to_excel(writer, sheet_name='B2B', index=False)
        
    return filename

def test_sop7_flow():
    print("--- starting sop7 verification ---")
    mock_file = create_mock_sop7_file()
    
    # 1. Test Analyzer Directly
    print("\n[1] Testing GSTR2AAnalyzer...")
    analyzer = GSTR2AAnalyzer(mock_file)
    analyzer.load_file()
    
    res = analyzer.analyze_sop(7)
    print("Analyzer Result:")
    print(json.dumps(res, indent=2, default=str))
    
    assert res['status'] == 'fail'
    assert len(res['rows']) == 1
    assert res['rows'][0]['invoice_no'] == 'INV-002'
    print("Analyzer: PASS")
    
    # 2. Test Parser Integration
    print("\n[2] Testing ScrutinyParser Integration...")
    parser = ScrutinyParser()
    
    # Mocking parser.parse_file context manually effectively
    # But let's verify what parse_file produces.
    # We need to minimally invoke the logic path.
    # We can invoke parser.parse_file with the mock file and the analyzer instance.
    
    final_output = parser.parse_file(mock_file, gstr2a_analyzer=analyzer)
    
    # Extract SOP-7 Issue
    issue = next((i for i in final_output['issues'] if i['issue_id'] == 'CANCELLED_SUPPLIERS'), None)
    
    if not issue:
        print("ERROR: SOP-7 Issue not found in parser output")
        return
        
    print("\nParser Issue Payload:")
    print(json.dumps(issue, indent=2, default=str))
    
    # Assertions on UI Contract
    assert 'tables' in issue, "Parser must produce 'tables' payload"
    table = issue['tables'][0]
    cols = [c['id'] for c in table['columns']]
    expected_cols = ["c_gstin", "c_inv", "c_date", "c_cancel", "c_cgst", "c_sgst", "c_igst"]
    assert cols == expected_cols, f"Columns Mismatch. Got: {cols}"
    
    assert len(table['rows']) == 1
    row = table['rows'][0]
    assert row['c_inv']['value'] == 'INV-002'
    assert row['c_igst']['value'] == 2000.0
    
    print("\nParser Integration: PASS")
    print("--- verification complete ---")

if __name__ == "__main__":
    test_sop7_flow()
