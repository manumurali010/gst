import pandas as pd
import os

file_path = "ISSUE DB.xlsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheet Names: {xl.sheet_names}")
    
    for sheet in xl.sheet_names[:2]: # Inspect first 2 sheets
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=20)
        print(df.to_string())
        
except Exception as e:
    print(f"Error reading Excel file: {e}")
