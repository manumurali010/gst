import pandas as pd
import os

file_path = "ISSUE DB.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    with open("inspection_output_utf8.txt", "w", encoding="utf-8") as f:
        f.write(f"SHEET_NAMES: {xl.sheet_names}\n")
        
        df = pd.read_excel(file_path, sheet_name=0, header=None, nrows=15)
        f.write("\nFIRST_SHEET_CONTENT:\n")
        f.write(str(df.values.tolist()))
        
except Exception as e:
    with open("inspection_output_utf8.txt", "w", encoding="utf-8") as f:
        f.write(f"Error: {e}")
