import pandas as pd

file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"

sheets = ["ITC (Other than IMPG)", "ITC (IMPG)", "RCM_LIABILITY_ITC"]

for sheet in sheets:
    print(f"\n--- Sheet: {sheet} ---")
    try:
        df = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=10)
        print(f"Row 5: {df.iloc[4].tolist()}")
        print(f"Row 6: {df.iloc[5].tolist()}")
    except Exception as e:
        print(f"Error reading sheet {sheet}: {e}")
