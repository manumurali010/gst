import pandas as pd
file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"
sheet = "ITC (Other than IMPG)"

df = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=10)
for r in [4, 5]: # Row 5 and 6
    print(f"\nROW {r+1}:")
    for c in range(15):
        val = df.iloc[r, c]
        print(f"  Col {c}: {val}")
