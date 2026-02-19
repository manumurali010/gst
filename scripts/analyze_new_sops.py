import pandas as pd
import openpyxl

EXCEL_FILE = "new sops.xlsx"

def analyze_excel():
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        print(f"Sheets found: {xl.sheet_names}")
        
        for sheet in xl.sheet_names:
            print(f"\n--- Analyzing Sheet: {sheet} ---")
            df = pd.read_excel(xl, sheet_name=sheet)
            print("Columns:", list(df.columns))
            print("First 5 rows:")
            print(df.head().to_string())
            print("-" * 30)
            
    except Exception as e:
        print(f"Error reading Excel file: {e}")

if __name__ == "__main__":
    analyze_excel()
