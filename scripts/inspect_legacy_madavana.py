import pandas as pd
import os

file_path = "2022-23_32AAMFM4610Q1Z0_Tax liability and ITC comparison.xlsx"

def inspect_legacy():
    if not os.path.exists(file_path):
        print("Legacy Excel not found!")
        return

    try:
        xl = pd.ExcelFile(file_path)
        sheet_name = "ITC (Other)" # Guessing based on logic
        # Logic uses: sheet_keyword="ITC (Other"
        target_sheet = next((s for s in xl.sheet_names if "ITC (Other" in s), None)
        
        if not target_sheet:
            print(f"Sheet 'ITC (Other*' not found. Sheets: {xl.sheet_names}")
            return
            
        print(f"Inspecting Sheet: {target_sheet}")
        df = pd.read_excel(file_path, sheet_name=target_sheet)
        
        # Logic uses "All Other ITC (GSTR 3B vs GSTR 2B)" which implies checking diff cols
        # Scrutiny parser logic:
        # claimed_indices = [1, 2, 3, 4] (3B)
        # diff_indices = [9, 10, 11, 12] (Diff)
        
        # Let's print the 'Total' row or just sum the diff columns (9,10,11,12)
        # Assuming header row is 0 or 1.
        
        total_diff = 0.0
        
        # Iterate and sum positive diffs (liability)
        print("Rows with Positive Diff (> 1.0):")
        for i, row in df.iterrows():
            # Skip totals/headers done by parser filter
            # Checks: period not nan, not "TOTAL"
            period = str(row.iloc[0])
            if "TOTAL" in period.upper() or period == "nan": continue
            
            row_vals = row.values
            # Diff indices are 9, 10, 11, 12 (0-indexed)
            # IGST, CGST, SGST, Cess
            
            row_liab = 0
            if len(row_vals) > 12:
                for idx in [9, 10, 11, 12]:
                    val = row_vals[idx]
                    try:
                        f_val = float(val)
                        if f_val > 1.0:
                            row_liab += f_val
                    except: pass
            
            if row_liab > 0:
                print(f"Row {i} ({period}): Liab {row_liab}")
                total_diff += row_liab
                
        print(f"\nTotal Legacy Liability: {total_diff}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_legacy()
