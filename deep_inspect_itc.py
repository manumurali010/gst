import pandas as pd

file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"
sheets = ["ITC (Other than IMPG)", "ITC (IMPG)", "RCM_LIABILITY_ITC"]

for sheet in sheets:
    print(f"\n--- Sheet: {sheet} ---")
    try:
        df = pd.read_excel(file_path, sheet_name=sheet, header=None)
        print(f"Row 5 (H1): {df.iloc[4].tolist()}")
        print(f"Row 6 (H2): {df.iloc[5].tolist()}")
        
        # Find Total row
        total_row = None
        for i, row in df.iterrows():
            if "total" in str(row.iloc[0]).lower():
                total_row = row
                print(f"Total Row Index: {i+1}")
                print(f"Total Row Data: {row.tolist()}")
                break
    except Exception as e:
        print(f"Error: {e}")
