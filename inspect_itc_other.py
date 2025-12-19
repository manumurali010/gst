import pandas as pd

file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"
sheet = "ITC (Other than IMPG)"

df = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=10)
print(f"Row 5: {df.iloc[4].tolist()}")
print(f"Row 6: {df.iloc[5].tolist()}")
