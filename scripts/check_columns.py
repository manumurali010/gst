import pandas as pd
import os

EXCEL_FILE = "TAX PAYERS DETAILS PARAVUR RANGE.xlsx"

if os.path.exists(EXCEL_FILE):
    df = pd.read_excel(EXCEL_FILE)
    print("Columns in Excel:")
    for col in df.columns:
        print(col)
else:
    print(f"{EXCEL_FILE} not found.")
