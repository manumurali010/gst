
import pandas as pd
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.gstr_2a_analyzer import GSTR2AAnalyzer

def create_mock_excel(filename):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # --- IMPG Sheet ---
        # Goal: Verify Parent "Amount of tax" + Child "Integrated Tax" is detected.
        # We add 'GSTIN' to ensure we have >= 2 matches even without parent logic if child is good,
        # BUT we rely on Parent to match 'Integrated Tax' if regex needs it? 
        # Actually 'Integrated Tax' alone matches 'igst'.
        # The issue is that the Child line MUST be paired with Parent if Parent is the only text on that line (Row 4).
        
        # Grid setup
        grid = [['' for _ in range(10)] for _ in range(15)]
        
        # Row 4 (Parent): One cell text
        grid[4][6] = "Amount of tax"
        grid[4][5] = "" # Noise
        
        # Row 5 (Child):
        grid[5][0] = "GSTIN of Supplier" # Match 1
        grid[5][6] = "Integrated Tax"    # Match 2 (but "Amount of tax Integrated Tax" is better)
        grid[5][7] = "Cess"              # Match 3
        
        # Row 6 (Data)
        grid[6][0] = "29AAAAA0000A1Z5"
        grid[6][6] = "100.0"
        grid[6][7] = "10.0"
        
        # Fill extra data rows to ensure probe works
        for r in range(7, 10):
             grid[r][0] = "29AAAAA0000A1Z5"
             grid[r][6] = "100.0"
        
        df_impg_final = pd.DataFrame(grid)
        df_impg_final.to_excel(writer, sheet_name='IMPG', header=False, index=False)
        
        # --- TDS Sheet ---
        # Goal: Verify Parent "Amount Paid" + Child "Taxable Value"
        grid_tds = [['' for _ in range(10)] for _ in range(15)]
        
        grid_tds[4][5] = "Amount Paid" # Single text on row
        
        grid_tds[5][0] = "GSTIN of Deductor"
        grid_tds[5][5] = "Taxable Value"
        
        grid_tds[6][0] = "29AAAAA0000A1Z5"
        grid_tds[6][5] = "5000.0"
        
        for r in range(7, 10):
             grid_tds[r][0] = "29AAAAA0000A1Z5"
             grid_tds[r][5] = "5000.0"

        df_tds = pd.DataFrame(grid_tds)
        df_tds.to_excel(writer, sheet_name='TDS', header=False, index=False)

def run_test():
    filename = "repro_sop10_strict.xlsx"
    create_mock_excel(filename)
    
    analyzer = GSTR2AAnalyzer(filename)
    analyzer.load_file()
    
    print("\n--- Testing SOP-10 (IMPG) ---")
    try:
        res10 = analyzer._compute_sop_10()
        print("SOP-10 Result:", res10)
    except Exception as e:
        print("SOP-10 Error:", e)

    print("\n--- Testing SOP-5 (TDS) ---")
    try:
        res5 = analyzer._compute_sop_5_tds()
        print("SOP-5 TDS Result:", res5)
    except Exception as e:
        print("SOP-5 TDS Error:", e)

if __name__ == "__main__":
    run_test()
