import pandas as pd
import os

file_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")
    
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = xl.parse(sheet, nrows=5)
        print("Columns:")
        for col in df.columns:
            print(f"  - {col}")
except Exception as e:
    print(f"Error reading file: {e}")
