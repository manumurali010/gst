import pandas as pd
file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"
xl = pd.ExcelFile(file_path)
print(xl.sheet_names)
