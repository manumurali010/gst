import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    # Check Row 5 (Index 5) for B2B and ISD
    for sheet in ['B2B', 'ISD', 'TDS', 'IMPG']:
        if sheet in xl.sheet_names:
            print(f"\n--- Sheet: {sheet} Sub-headers (Row 5) ---")
            df = xl.parse(sheet, header=5, nrows=1) 
            cols = [str(c).strip() for c in df.columns.tolist()]
            print(cols)

except Exception as e:
    print(f"Error: {e}")
