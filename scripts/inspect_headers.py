import pandas as pd
import openpyxl

file_path = '2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx'

def inspect_sheet(sheet_name):
    print(f"\n{'='*20} {sheet_name} {'='*20}")
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=[4, 5, 6])
        for i, col in enumerate(df.columns):
            print(f"{i}: {' | '.join([str(x) for x in col])}")
        
        print("\n--- Rows (last 10) ---")
        print(df.tail(10).iloc[:, 0].to_string()) # Print row labels
    except Exception as e:
        print(f"Error reading {sheet_name}: {e}")

sheets = ['ITC (Other than IMPG)', 'Comparison Summary', 'Reverse charge']
for s in sheets:
    inspect_sheet(s)
