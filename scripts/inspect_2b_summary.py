import pandas as pd
import os

files = [
    r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2B_32AADCR5842H1ZH_2022-23.xlsx",
    r"C:\Users\manum\.gemini\antigravity\scratch\gst\062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
]

for f in files:
    print(f"\n--- Analyzing: {os.path.basename(f)} ---")
    if not os.path.exists(f):
        print("File not found!")
        continue
        
    try:
        xl = pd.ExcelFile(f)
        target_sheet = next((s for s in xl.sheet_names if "ITC Available" in s), None)
        
        if target_sheet:
            print(f"Reading Sheet: {target_sheet}")
            # Read first 50 rows to capture Summary blocks
            df = xl.parse(target_sheet, header=None, nrows=60)
            
            # Print with index to locate rows
            for idx, row in df.iterrows():
                # Clean strings for printing
                vals = [str(x).replace('\n', ' ') if pd.notna(x) else '' for x in row]
                # Filter out completely empty rows for brevity
                if any(vals):
                     safe_vals = [v.encode('ascii', 'replace').decode('ascii') for v in vals]
                     print(f"{idx}: {safe_vals}")
        else:
            print("Sheet 'ITC Available' not found.")
            print(f"Available: {xl.sheet_names}")

    except Exception as e:
        print(f"Error: {e}")
