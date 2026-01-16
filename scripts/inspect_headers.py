import pandas as pd
import openpyxl

file_path = '2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx'

def inspect_sheet(sheet_name):
    print(f"\n{'='*20} {sheet_name} {'='*20}")
    try:
        # Try both 2-level and 3-level headers to see which one works better
        for h_count in [[4, 5], [4, 5, 6]]:
            print(f"\n--- Header Indices: {h_count} ---")
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=h_count)
            for i, col in enumerate(df.columns[0:10]): # Show first 10 columns
                col_tuple = col if isinstance(col, tuple) else (col,)
                print(f"{i}: {' | '.join([str(x) for x in col_tuple])}")
    except Exception as e:
        print(f"Error reading {sheet_name}: {e}")

sheets = ['Reverse charge']
for s in sheets:
    inspect_sheet(s)
