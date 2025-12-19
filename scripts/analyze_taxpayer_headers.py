import pandas as pd
import os

BASE_DIR = r"C:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System"
FILES = [
    "List_of_Cancelled_Taxpayer.xlsx",
    "List_of_Active_Taxpayer.xlsx",
    "List_of_Suspended_Taxpayer.xlsx"
]

print("--- ANALYZING TAXPAYER FILES ---")

for fname in FILES:
    fpath = os.path.join(BASE_DIR, fname)
    print(f"\nScanning: {fname}")
    if not os.path.exists(fpath):
        # Try without extension or with .xls
        if os.path.exists(os.path.join(BASE_DIR, fname.split('.')[0])):
             fpath = os.path.join(BASE_DIR, fname.split('.')[0])
        elif os.path.exists(os.path.join(BASE_DIR, fname.replace('.xlsx', '.xls'))):
             fpath = os.path.join(BASE_DIR, fname.replace('.xlsx', '.xls'))
        else:
            print(f"ERROR: File not found: {fpath}")
            continue
            
    try:
        df = pd.read_excel(fpath, header=None, nrows=5)
        print("ROW 0:", df.iloc[0].tolist())
        print("ROW 1:", df.iloc[1].tolist())
        print("ROW 2:", df.iloc[2].tolist())
        print("ROW 3:", df.iloc[3].tolist())
    except Exception as e:
        print(f"Error reading file: {e}")
