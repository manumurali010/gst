import pandas as pd
import sys

# Set explicit encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"

def find_header_row(df):
    for i in range(10):  # Check first 10 rows
        row_values = df.iloc[i].astype(str).str.lower().tolist()
        if any('gstin' in x for x in row_values) or \
           any('invoice' in x for x in row_values) or \
           any('port code' in x for x in row_values) or \
           any('rate' in x for x in row_values):
            return i
    return 0

try:
    xl = pd.ExcelFile(file_path)
    sheets_to_check = ['B2B', 'ISD', 'TDS', 'TCS', 'IMPG']
    
    for sheet in sheets_to_check:
        if sheet in xl.sheet_names:
            print(f"\n--- Sheet: {sheet} ---")
            df_preview = xl.parse(sheet, header=None, nrows=10)
            header_idx = find_header_row(df_preview)
            print(f"Detected Header Row Index: {header_idx}")
            
            df = xl.parse(sheet, header=header_idx, nrows=2)
            cols = [str(c).strip() for c in df.columns.tolist()]
            print("Columns found:")
            print(cols)
        else:
            print(f"\n--- Sheet: {sheet} NOT FOUND ---")

except Exception as e:
    print(f"Error: {e}")
