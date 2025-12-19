import pandas as pd
import openpyxl

file_path = r"2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print("Sheet Names:", xl.sheet_names)
    
    # Check Reverse Charge sheet
    rc_sheet = next((s for s in xl.sheet_names if "reverse charge" in s.lower()), None)
    if rc_sheet:
        print(f"\nAnalyzing sheet: {rc_sheet}")
        # Load with multiple headers to see structure
        df = pd.read_excel(file_path, sheet_name=rc_sheet, header=[4, 5])
        print("\nColumns found:")
        for i, col in enumerate(df.columns):
            print(f"{i}: {col}")
        
        print("\nFirst few rows:")
        print(df.head(10))
        
        # Check specific columns for IGST/CGST/SGST Difference
        # Based on my previous assumptions, it should be indices 9, 10, 11 (J,K,L)
        # Let's see if there are any negative values there
        for i in range(min(len(df), 15)):
            row = df.iloc[i]
            print(f"Row {i} Period: {row.iloc[0]}")
            # Try to find diff columns dynamically
            diff_indices = [idx for idx, col in enumerate(df.columns) if "DIFFERENCE" in str(col).upper() or "SHORT" in str(col).upper()]
            print(f"  Diff values at {diff_indices}: {[row.iloc[idx] for idx in diff_indices]}")

except Exception as e:
    print(f"Error: {e}")
