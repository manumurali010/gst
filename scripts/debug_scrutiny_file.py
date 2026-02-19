import pandas as pd
import os
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison (1).xlsx")

try:
    xl = pd.ExcelFile(FILE_PATH)
    print("--- SHEET NAMES ---")
    for s in xl.sheet_names:
        print(f"'{s}'")
    
    print("\n--- HEADER ANALYSIS ---")
    
    target_sheets = [
        "ITC (Other"
    ]
    
    def inspect_sheet_values(sheet_keyword):
        # Find partial match
        sheet_name = next((s for s in xl.sheet_names if sheet_keyword.lower() in s.lower() and "summary" not in s.lower()), None)
        if not sheet_name:
            print(f"\n[MISSING] Sheet for keyword '{sheet_keyword}' not found.")
            return

        print(f"\n--- Scanning Sheet: '{sheet_name}' (Keyword: {sheet_keyword}) ---")
        try:
            # Read with header indices 4,5 (Row 5,6) as recently fixed
            df = pd.read_excel(FILE_PATH, sheet_name=sheet_name, header=[4, 5])
            
            # Find Diff Columns
            diff_cols = []
            for idx, col in enumerate(df.columns):
                # Col is a tuple likely
                col_str = str(col).upper()
                if ("SHORTFALL" in col_str or "EXCESS" in col_str or "DIFFERENCE" in col_str) and "PERCENTAGE" not in col_str:
                    diff_cols.append((idx, col))
            
            if not diff_cols:
                print("  No 'Shortfall/Excess/Difference' columns found.")
                # Print columns to debug
                print("  Columns Found:", df.columns.tolist()[:5])
                return

            print(f"  Found {len(diff_cols)} diff columns.")
            
            # Check for non-zero values
            found_data = False
            for idx, row in df.iterrows():
                # Skip Total rows or NaN
                if "Total" in str(row.iloc[0]): continue
                
                for col_idx, col_name in diff_cols:
                    val = row.iloc[col_idx]
                    try:
                        f_val = float(val)
                        if abs(f_val) > 1.0:
                            print(f"  Row {idx}: {col_name} = {f_val}")
                            found_data = True
                    except:
                        pass
            
            if not found_data:
                print("  No significant values (> 1.0) found in diff columns.")
                
        except Exception as e:
            print(f"  Error reading sheet: {e}")

    for ts in target_sheets:
        inspect_sheet_values(ts)

except Exception as e:
    print(f"Failed to load file: {e}")
