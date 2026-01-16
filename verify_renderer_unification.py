import sys
import os
import pandas as pd
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst")

from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

def verify_renderer_unification():
    print("=== VERIFYING RENDERER UNIFICATION (SOP-5 & SOP-7) ===")
    
    # 1. Setup Mock Data
    mock_2a_path = "mock_2a_unified.xlsx"
    mock_3b_path = "mock_3b_unified.pdf" # Dummy path, parser will skip if not found but we need it for arg
    
    # Create Mock 2A Excel
    with pd.ExcelWriter(mock_2a_path) as writer:
        # SOP-7 Data (B2B)
        pd.DataFrame({
            'GSTIN of Supplier': ['32AAAAA1111A1Z5'],
            'Invoice Number': ['INV-001'],
            'Invoice Date': ['01-01-2023'],
            'Supplier Registration Status': ['Cancelled'], 
            'Effective Date of Cancellation': ['01-12-2022'], 
            'Central Tax': [100], 
            'State Tax': [100], 
            'Integrated Tax': [0],
            'GSTR-3B Filing Status': ['Yes']
        }).to_excel(writer, sheet_name='B2B', index=False)
        
        # SOP-5 Data (TDS/TCS)
        pd.DataFrame({
            'GSTIN of Deductor': ['32AAAAA2222A1Z5'],
            'Trade Name': ['Test Deductor'],
            'Taxable Value': [50000],
            'TDS Amount': [1000] # Should be ignored if Taxable Value present
        }).to_excel(writer, sheet_name='TDS Credit Received', index=False)
        
        pd.DataFrame({
            'GSTIN of Collection': ['32AAAAA3333A1Z5'],
            'Net Value': [20000], # Base value for TCS
            'TCS Amount': [200]
        }).to_excel(writer, sheet_name='TCS Credit Received', index=False)

    print(f"[SETUP] Created {mock_2a_path}")
    
    # 2. Analyze
    parser = ScrutinyParser()
    analyzer = GSTR2AAnalyzer(mock_2a_path)
    
    # Mocking parser extra_files for 3B path if needed
    # We might need to mock parse_gstr3b_pdf_table_3_1_a if we want SOP-5 to fully calc
    # But for structural check, getting 'Data Not Available' with summary_table is also a success if it avoids 'tables'.
    
    # Run SOP-7 Verification
    print("\n--- Verifying SOP-7 (Cancelled Suppliers) ---")
    res_7 = analyzer.analyze_sop(7)
    # Inject result into parser flow simulation
    # ScrutinyParser.parse_file calls analyze_sop(7) internally.
    
    import src.services.scrutiny_parser as parser_module
    
    original_3b_parser = parser_module.parse_gstr3b_pdf_table_3_1_a

    def mock_3b_parser(pdf_path):
        print(f"DEBUG: Mocking 3B Parser for {pdf_path}")
        return {"taxable_value": 100000.0} # Dummy value to pass checks

    parser_module.parse_gstr3b_pdf_table_3_1_a = mock_3b_parser

    # Mock SOP-7 Computation for Success Path
    # We patch GSTR2AAnalyzer._compute_sop_7 to return valid rows.
    # This bypasses the brittleness of Excel column matching in mock data.
    original_sop7_computer = GSTR2AAnalyzer._compute_sop_7
    
    def mock_compute_sop7(self):
         print("DEBUG: Executing MOCK _compute_sop_7 (Force Success)")
         return {
             'rows': [
                 {
                     'gstin': '32AAAAA1111A1Z5',
                     'invoice_no': 'INV-001',
                     'invoice_date': '01-01-2023',
                     'cancellation_date': '01-12-2022',
                     'igst': 0, 'cgst': 100, 'sgst': 100
                 }
             ],
             'total_liability': 200.0,
             'status': 'fail'
         }
    
    GSTR2AAnalyzer._compute_sop_7 = mock_compute_sop7

    # We will call parse_file directly.
    try:
        # Pass as dict. The key 'gstr3b' is used by _parse_tds_tcs_phase2.
        extra_files_dict = {'gstr3b': mock_3b_path, 'gstr3b_yearly': mock_3b_path}
        result = parser.parse_file(mock_2a_path, gstr2a_analyzer=analyzer, extra_files=extra_files_dict)
        issues = result.get('issues', []) if isinstance(result, dict) else result
    finally:
        parser_module.parse_gstr3b_pdf_table_3_1_a = original_3b_parser # Restore
        GSTR2AAnalyzer._compute_sop_7 = original_sop7_computer # Restore
    
    # DEBUG
    print(f"DEBUG: Issues type: {type(issues)}")
    if isinstance(issues, list):
         print(f"DEBUG: Issues count: {len(issues)}")
         if len(issues) > 0:
              print(f"DEBUG: Item 0 types: {type(issues[0])}")
              print(f"DEBUG: Item 0 content: {issues[0]}")
    
    sop7_issue = next((i for i in issues if isinstance(i, dict) and i.get('issue_id') == 'CANCELLED_SUPPLIERS'), None)
    if not sop7_issue:
        print("[FAIL] SOP-7 Issue NOT found in output.")
    else:
        print("[PASS] SOP-7 Issue Found.")
        if 'tables' in sop7_issue:
            print("[FAIL] FAILURE: 'tables' key present in SOP-7 payload! (Must be removed)")
        else:
            print("[PASS] SUCCESS: 'tables' key absent in SOP-7 payload.")
            
        if 'summary_table' in sop7_issue:
            print("[PASS] SUCCESS: 'summary_table' key present in SOP-7 payload.")
            
            # Check for Total Row
            rows_7 = sop7_issue['summary_table'].get('rows', [])
            if rows_7:
                last_row = rows_7[-1]
                # Check col0 text
                val_col0 = last_row.get('col0', {}).get('value', '')
                if val_col0 == "TOTAL":
                     print("[PASS] SUCCESS: SOP-7 Total Row detected.")
                     # Check if tax columns have values
                     c_val = last_row.get('col4', {}).get('value', '0')
                     print(f"INFO: Total CGST: {c_val}")
                else:
                     print(f"[FAIL] FAILURE: SOP-7 Total Row MISSING. Last Row Col0: {val_col0}")
                     # Debug Info
                     print(f"DEBUG info: SOP-7 Status: {sop7_issue.get('status')}")
                     print(f"DEBUG info: SOP-7 Msg: {sop7_issue.get('status_msg')}")
            else:
                 print("[FAIL] FAIL: SOP-7 rows empty.")
                 print(f"DEBUG info: SOP-7 Status: {sop7_issue.get('status')}")
                 print(f"DEBUG info: SOP-7 Msg: {sop7_issue.get('status_msg')}")
            # Verify Column Structure
            cols = sop7_issue['summary_table'].get('columns', [])
            col_ids = [c['id'] for c in cols]
            expected_ids = ['col0', 'col1', 'col2', 'col3', 'col4', 'col5', 'col6']
            if col_ids == expected_ids:
                 print("[PASS] SUCCESS: Columns match canonical schema (col0-col6).")
            else:
                 print(f"[FAIL] FAILURE: Column IDs mismatch. Found: {col_ids}")
        else:
            print("[FAIL] FAILURE: 'summary_table' key MISSING in SOP-7 payload.")

    # Run SOP-5 Verification
    print("\n--- Verifying SOP-5 (TDS/TCS) ---")
    sop5_issue = next((i for i in issues if i['issue_id'] == 'TDS_TCS_MISMATCH'), None)
    
    if not sop5_issue:
         print("[FAIL] SOP-5 Issue NOT found. (Check parser logic / guard)")
    else:
         print("[PASS] SOP-5 Issue Found.")
         if 'tables' in sop5_issue:
            print("[FAIL] FAILURE: 'tables' key present in SOP-5 payload! (Must be removed)")
         else:
            print("[PASS] SUCCESS: 'tables' key absent in SOP-5 payload.")
            
         if 'summary_table' in sop5_issue:
             print("[PASS] SUCCESS: 'summary_table' key present in SOP-5 payload.")
             # Check rows for combined content
             rows = sop5_issue['summary_table'].get('rows', [])
             has_tds = any("TDS Mismatch" in str(r.get('col0', {}).get('value', '')) for r in rows)
             has_tcs = any("TCS Mismatch" in str(r.get('col0', {}).get('value', '')) for r in rows)
             
             if has_tds and has_tcs:
                 print("[PASS] SUCCESS: Found both TDS and TCS headers in combined summary_table.")
             elif has_tds:
                 print("[WARN] WARNING: Found TDS header but TCS missing (Could be data specific).")
             else:
                 print("[FAIL] FAILURE: Headers missing in combined table.")
         else:
             print("[FAIL] FAILURE: 'summary_table' key MISSING in SOP-5 payload.")

    # Cleanup
    try:
        os.remove(mock_2a_path)
    except: pass
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify_renderer_unification()
