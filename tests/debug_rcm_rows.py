
import sys
import os
sys.path.append(os.getcwd())
from src.utils.xlsx_light import XLSXLight

def inspect_rows(file_path):
    print(f"\n--- Investigating File: {os.path.basename(file_path)} ---")
    rows = XLSXLight.read_sheet(file_path, "ITC Available")
    
    print("\n--- Rows containing 'Reverse' and 'Inward' ---")
    matches = 0
    for idx, row in enumerate(rows):
        if not row: continue
        row_text = " ".join([str(x).lower().strip() for x in row if x]).replace(",", "")
        
        if "reverse" in row_text and "inward" in row_text:
            print(f"Row {idx}: {row_text[:100]}... | Values: {row[3:7]} (approx)")
            matches += 1
            
    if matches == 0:
        print("No matching rows found.")
    else:
        print(f"Total matching rows: {matches}")

if __name__ == "__main__":
    target = "D:/gst/032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
    if len(sys.argv) > 1:
        target = sys.argv[1]
        
    if os.path.exists(target):
         inspect_rows(target)
    else:
         print(f"File not found: {target}")
