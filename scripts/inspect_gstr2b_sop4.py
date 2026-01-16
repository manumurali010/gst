import pandas as pd
import os
import sys

# Force utf-8 for print
sys.stdout.reconfigure(encoding='utf-8')

file_path = "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheets: {xl.sheet_names}")
    
    target_sheet = next((s for s in xl.sheet_names if "ITC Available" in s), None)
    if target_sheet:
        print(f"\nAnalyzing '{target_sheet}'...")
        # Read without header first to see structure
        df = pd.read_excel(file_path, sheet_name=target_sheet, header=None)
        
        # Look for the specific row text
        keyword = "All other ITC"
        print(f"\nSearching for '{keyword}'...")
        for i, row in df.iterrows():
            row_vals = [str(x) for x in row.values]
            row_str = " ".join(row_vals)
            if keyword in row_str:
                print(f"Row {i} Matches:")
                for j, val in enumerate(row_vals):
                    print(f"  Col {j}: {val}")
    else:
        print("Sheet 'ITC Available' not found.")

except Exception as e:
    print(f"Error: {e}")
