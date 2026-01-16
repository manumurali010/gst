import pandas as pd
import os

file_path = '2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx'

def debug_values():
    sheet_name = 'ITC (Other than IMPG)'
    print(f"Reading {sheet_name} with header=[4, 5, 6]...")
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=[4, 5, 6])
    
    print("\n--- Column Mapping Check ---")
    for i, col in enumerate(df.columns[:15]):
        print(f"Index {i}: {col}")
        
    print("\n--- Row 0 (First Month) ---")
    if not df.empty:
        row = df.iloc[0]
        print(f"Period: {row.iloc[0]}")
        # Let's print IGST for 3B, 2B, and Diff
        # Based on index 1, 5, 9 from previous inspection
        print(f"3B IGST (Index 1): {row.iloc[1]}")
        print(f"2B IGST (Index 5): {row.iloc[5]}")
        print(f"Diff IGST (Index 9): {row.iloc[9]}")
        
        calc = row.iloc[1] - row.iloc[5]
        print(f"Calculated (3B - 2B): {calc}")
    else:
        print("DataFrame is empty!")

if __name__ == "__main__":
    debug_values()
