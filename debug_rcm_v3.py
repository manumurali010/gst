import pandas as pd

file_path = r"2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"

try:
    df = pd.read_excel(file_path, sheet_name="Reverse Charge", header=[4, 5])
    print("\nHeader mapping (0 to 18):")
    for i in range(19):
        print(f"{i}: {df.columns[i]}")
except Exception as e:
    print(f"Error: {e}")
