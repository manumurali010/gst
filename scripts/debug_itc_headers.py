import pandas as pd
import warnings

warnings.filterwarnings("ignore")

FILE_PATH = "C:\\Users\\manum\\.gemini\\antigravity\\scratch\\GST_Adjudication_System\\2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison (1).xlsx"

try:
    xl = pd.ExcelFile(FILE_PATH)
    target_sheet = "Tax liability"
    if target_sheet in xl.sheet_names:
        print(f"--- DUMPING ROWS 3, 4, 5, 6 for: {target_sheet} ---")
        df = pd.read_excel(FILE_PATH, sheet_name=target_sheet, header=None, nrows=10)
        print("ROW 3:", df.iloc[3].tolist())
        print("ROW 4:", df.iloc[4].tolist())
        print("ROW 5:", df.iloc[5].tolist())
        print("ROW 6:", df.iloc[6].tolist())
    else:
        print("Sheet 'ITC (Other' not found.")

except Exception as e:
    print(f"Error: {e}")
