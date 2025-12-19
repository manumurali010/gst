import pandas as pd
import openpyxl

file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"
sheets = ["ITC (Other than IMPG)", "ITC (IMPG)", "RCM_LIABILITY_ITC"]

for sheet in sheets:
    print(f"\n--- SHEET: {sheet} ---")
    try:
        # Read the first 10 rows to see headers
        df = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=10)
        for i, row in df.iterrows():
            print(f"Row {i+1}: {' | '.join([str(v) for v in row if pd.notna(v)])}")
        
        # Check for "Total" row as well
        df_full = pd.read_excel(file_path, sheet_name=sheet, header=None)
        # Find the last row with "Total" in the first column
        total_row_idx = None
        for i, row in df_full.iterrows():
            if str(row.iloc[0]).strip().lower() == "total":
                total_row_idx = i
                break
        
        if total_row_idx is not None:
             total_row = df_full.iloc[total_row_idx]
             print(f"TOTAL ROW (Row {total_row_idx+1}): {' | '.join([str(v) for v in total_row if pd.notna(v)])}")
    except Exception as e:
        print(f"Error reading {sheet}: {e}")
