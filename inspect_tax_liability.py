import pandas as pd
import openpyxl

file_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\2022-23_32AAMFM4610Q1Z0_Tax liability and ITC comparison.xlsx"

try:
    # 1. List Sheets
    xl = pd.ExcelFile(file_path)
    print("Sheets found:", xl.sheet_names)
    
    # 2. Inspect 'Tax liability' sheet (usually 3rd, index 2)
    # User said "Tax liability (3rd sheet)". Let's find it by name or index.
    sheet_name = xl.sheet_names[2] 
    print(f"\nAnalyzing 3rd sheet: '{sheet_name}'")
    
    # Read first 20 rows to understand header structure
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=20)
    print("\nFirst 20 rows of raw data:")
    print(df.to_string())

    # Check for "Tax Liability" keyword in cells to locate start
except Exception as e:
    print(f"Error: {e}")
