import pandas as pd
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
excel_path = "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

def inspect_cdnr():
    if not os.path.exists(excel_path): return
    print("Inspecting CDNR Headers...")
    df = pd.read_excel(excel_path, sheet_name="B2B-CDNR", header=None)
    for i, row in df.head(8).iterrows():
        print(f"Row {i}: {row.values}")

if __name__ == "__main__":
    inspect_cdnr()
