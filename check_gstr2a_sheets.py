import pandas as pd
import os

file_path = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"

if os.path.exists(file_path):
    try:
        xl = pd.ExcelFile(file_path)
        print("SHEETS FOUND:", xl.sheet_names)
    except Exception as e:
        print(f"Error reading file: {e}")
else:
    print("File not found.")
