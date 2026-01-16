import sys
import os
import pandas as pd
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst")

from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

def verify_sop8_expanded():
    print("=== VERIFYING SOP-8 EXPANDED TABLE ===")
    
    mock_2a_path = "mock_2a_sop8.xlsx"
    mock_3b_path = "mock_3b_dummy.pdf" # Not read for SOP-8 logic but needed for args
    
    # Create Mock Data
    with pd.ExcelWriter(mock_2a_path) as writer:
        df = pd.DataFrame({
            'GSTIN of Supplier': [None, '32AAAAA1111A1Z5', '32AAAAA2222A1Z5'],
            'Invoice Number': [None, 'INV-NON-FILER', 'INV-FILER'],
            'Invoice Date': [None, '01-01-2023', '01-01-2023'],
            'GSTR-2A Period': [None, 'Dec-2022', 'Dec-2022'],
            'Taxable Value': [None, 1000, 2000],
            'Central Tax': [None, 90, 180],
            'State Tax': [None, 90, 180],
            'Integrated Tax': [None, 0, 0],
            'GSTR-3B Filing Status': [None, 'No', 'Yes'] 
        })
        df.to_excel(writer, sheet_name='B2B', index=False)
        
    print(f"[SETUP] Created {mock_2a_path}")
    
    # Setup Logic
    parser = ScrutinyParser()
    analyzer = GSTR2AAnalyzer(mock_2a_path)
    
    # Ensure analyzer reads our mock file
    if not analyzer.load_file():
        print("[FAIL] Analyzer failed to load mock file.")
        return

    # Patch 3B parser (referenced by SOP-5) just in case
    import src.services.scrutiny_parser as parser_module
    original_3b = getattr(parser_module, 'parse_gstr3b_pdf_table_3_1_a', None)
    parser_module.parse_gstr3b_pdf_table_3_1_a = lambda x: {"taxable_value": 0}
    
    try:
        extra_files = {'gstr3b': mock_3b_path}
        # Parse
        # Note: parse_file runs all SOPs. SOP-8 should trigger.
        result = parser.parse_file(mock_2a_path, gstr2a_analyzer=analyzer, extra_files=extra_files)
        issues = result.get('issues', [])
        
        # Find SOP-8
        sop8 = next((i for i in issues if i['issue_id'] == 'NON_FILER_SUPPLIERS'), None)
        
        if not sop8:
            print("[FAIL] SOP-8 Issue NOT found in results.")
            return
            
        print("[PASS] SOP-8 Issue Found.")
        
        # 1. check summary_table key
        if 'summary_table' not in sop8:
            print("[FAIL] 'summary_table' key missing in SOP-8 payload.")
            print(f"DEBUG: Keys found: {sop8.keys()}")
            if 'template_type' in sop8: print(f"DEBUG: Found template_type: {sop8['template_type']}")
            return
            
        print("[PASS] 'summary_table' key used.")
        
        # 2. Check Columns
        st = sop8['summary_table']
        cols = st.get('columns', [])
        expected_cols = ['col0', 'col1', 'col2', 'col3', 'col4', 'col5', 'col6', 'col7']
        found_cols = [c['id'] for c in cols]
        
        if found_cols != expected_cols:
             print(f"[FAIL] Column ID Mismatch. Expected {expected_cols}, Found {found_cols}")
        else:
             print("[PASS] Columns match schema (col0-col7).")
             
        # 3. Check Rows filtering (Non-Filer only)
        rows = st.get('rows', [])
        # Expect 1 data row + 1 total row = 2 rows
        if len(rows) != 2:
             print(f"[FAIL] Row count mismatch. Expected 2 (1 Data + 1 Total). Found {len(rows)}.")
             for r in rows: print(r)
        else:
             print("[PASS] Row count correct (1 Data + 1 Total).")
             
             # Verify Data Row
             data_row = rows[0]
             if data_row['col1']['value'] == '32AAAAA1111A1Z5':
                  print("[PASS] Correct Non-Filer filtered.")
             else:
                  print(f"[FAIL] Wrong data row. Found GSTIN: {data_row['col1']['value']}")
                  
             # Verify Total Row
             total_row = rows[1]
             if total_row['col0']['value'] == "TOTAL":
                  print("[PASS] Total Row detected.")
             else:
                  print(f"[FAIL] Total Row label missing/wrong: {total_row['col0']['value']}")
                  
             # Verify Sums
             # Taxable: 1000, CGST: 90, SGST: 90
             # Formatted .2f -> "1000.00", "90.00"
             
             t_taxable = total_row.get('col4', {}).get('value')
             t_cgst = total_row.get('col5', {}).get('value')
             
             if t_taxable == "1000.00":
                  print("[PASS] Total Taxable correct (1000.00).")
             else:
                  print(f"[FAIL] Total Taxable wrong. Got {t_taxable}")
                  
             if t_cgst == "90.00":
                  print("[PASS] Total CGST correct (90.00).")
             else:
                  print(f"[FAIL] Total CGST wrong. Got {t_cgst}")

    except Exception as e:
        print(f"[CRASH] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore patch
        if original_3b: parser_module.parse_gstr3b_pdf_table_3_1_a = original_3b
        try: os.remove(mock_2a_path)
        except: pass

if __name__ == "__main__":
    verify_sop8_expanded()
