import pandas as pd

file_path = r"2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    rc_sheet = next((s for s in xl.sheet_names if "reverse charge" in s.lower()), None)
    if rc_sheet:
        print(f"Sheet: {rc_sheet}")
        # Load with 3 levels of headers to be safe
        df = pd.read_excel(file_path, sheet_name=rc_sheet, header=[4, 5])
        
        print("\nColumn Index -> Multi-Index Header:")
        for i, col in enumerate(df.columns):
            print(f"{i}: {col}")
            
except Exception as e:
    print(f"Error: {e}")
