
import pandas as pd
import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'src'))
from services.gstr_2a_analyzer import GSTR2AAnalyzer

def create_mock_excel(filename):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # --- SOP-3 (ISD) ---
        # Trap:
        # Row 0: "GSTIN of Supplier" (1 col)
        # Row 1: "Invoice Date" (1 col)
        # Row 2: "Some other text"
        #
        # If relaxed: Row 0 is candidate. Merged with Row 1 = "GSTIN... Invoice Date...".
        # Matches: GSTIN, Invoice Date (2 matches).
        # Result: Headers detected at 0.
        # Problem: Real data is at Row 6. Row 2,3,4,5 are garbage/metadata.
        # The analyzer will think Row 2 is data (start row = 0+2 = 2).
        # Row 2 is "Some other text". Columns "GSTIN" and "Invoice Date" will map to Col 0.
        # But tax columns won't match (count=2 < 3, but is_valid_probe might pass if row 2 has numbers? No.)
        # Wait, validation logic: "if match_cnt >= 2: probe_idx = i+2 ... if nums_probe > 0".
        # If Row 2 is text, nums_probe=0. So it might reject.
        # Let's put a number in Row 2 to FORCE a false positive.
        
        grid_isd = [['' for _ in range(10)] for _ in range(20)]
        
        # False Header Candidate
        grid_isd[0][0] = "GSTIN of Supplier"
        grid_isd[1][0] = "Invoice Date"
        
        # False Data (Probe validation)
        grid_isd[2][0] = "123456" # Numeric text
        
        # Real Header (Row 6)
        grid_isd[6][0] = "GSTIN of Supplier"
        grid_isd[6][1] = "Invoice Number"
        grid_isd[6][2] = "Invoice Date"
        grid_isd[6][3] = "Integrated Tax" # IGST
        grid_isd[6][4] = "Central Tax"
        grid_isd[6][5] = "State Tax"
        
        # Real Data
        grid_isd[7][0] = "29AAA..."
        grid_isd[7][1] = "INV-001"
        grid_isd[7][2] = "01-01-2022"
        grid_isd[7][3] = "100"
        grid_isd[7][4] = "50"
        grid_isd[7][5] = "50"
        
        df_isd = pd.DataFrame(grid_isd)
        df_isd.to_excel(writer, sheet_name='ISD', header=False, index=False)
        
        # --- SOP-10 (IMPG) ---
        # Needs Relaxed Logic
        grid_impg = [['' for _ in range(10)] for _ in range(15)]
        grid_impg[4][6] = "Amount of tax"
        grid_impg[5][6] = "Integrated Tax"
        grid_impg[5][7] = "Cess"
        grid_impg[6][6] = "500.0"
        
        df_impg = pd.DataFrame(grid_impg)
        df_impg.to_excel(writer, sheet_name='IMPG', header=False, index=False)

def run_test():
    filename = "regression_strict.xlsx"
    create_mock_excel(filename)
    
    analyzer = GSTR2AAnalyzer(filename)
    analyzer.load_file()
    
    print("\n--- Testing SOP-3 (ISD) [Should match Row 6, NOT Row 0] ---")
    hm_3, row_3 = analyzer._scan_headers('ISD', sop_id='sop_3')
    print(f"SOP-3 Detected Row: {row_3} (Expected: 8 [Row 6+2])")
    # Row 6 is header. +1 (child is 7, but here single line header effectiveness).
    # If merged 6+7: 6 is header, 7 is data.
    # match_cnt on 6+7 will be high.
    # Detected at 6. Return 6+2 = 8.
    
    if row_3 == 2:
        print("❌ FAIL: SOP-3 falsely detected headers at Row 0 (Strict check failed)")
    elif row_3 == 8:
         print("✅ PASS: SOP-3 correctly detected headers at Row 6")
    else:
         print(f"⚠️  WARN: SOP-3 detected at {row_3}")

    print("\n--- Testing SOP-10 (IMPG) [Should match Row 4] ---")
    hm_10, row_10 = analyzer._scan_headers('IMPG', sop_id='sop_10')
    print(f"SOP-10 Detected Row: {row_10} (Expected: 6 [Row 4+2])")
    
    if row_10 == 6:
        print("✅ PASS: SOP-10 correctly detected headers at Row 4")
    else:
        print("❌ FAIL: SOP-10 failed to detect headers (Relaxed check failed)")

if __name__ == "__main__":
    run_test()
