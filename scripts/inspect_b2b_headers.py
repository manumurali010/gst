import pandas as pd
import os
import sys

# Force output encoding
sys.stdout.reconfigure(encoding='utf-8')

excel_path = "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

def inspect_b2b():
    if not os.path.exists(excel_path): return
    print("Inspecting B2B Headers...")
    df = pd.read_excel(excel_path, sheet_name="B2B", header=None)
    # Print first 8 rows (Headers usually around row 6)
    for i, row in df.head(8).iterrows():
        print(f"Row {i}: {row.values}")

if __name__ == "__main__":
    inspect_b2b()
