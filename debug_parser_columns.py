import sys
import os
import pandas as pd
import openpyxl

file_path = "2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"
sheet_keyword = "Tax Liability"

def debug_columns():
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Analyzing {file_path} for '{sheet_keyword}'...")
    
    # 1. Find Sheet
    wb = openpyxl.load_workbook(file_path, data_only=True)
    target_sheet_name = next((s for s in wb.sheetnames if sheet_keyword.lower() in s.lower() and "summary" not in s.lower()), None)
    wb.close()
    
    if not target_sheet_name:
        print("Target sheet not found.")
        return

    print(f"Target Sheet: {target_sheet_name}")

    # 2. Read Headers
    df = pd.read_excel(file_path, sheet_name=target_sheet_name, header=[4, 5])
    
    col_map = {}
    last_valid_l0 = ""
    
    print("\n--- Column Mapping Debug ---")
    print(f"{'Index':<5} | {'Raw L0':<30} | {'Filled L0':<30} | {'Level 1':<15} | {'Source':<10} | {'Head':<10}")
    print("-" * 110)

    for i, col in enumerate(df.columns):
        # col is (Level0, Level1)
        raw_l0 = str(col[0]).strip()
        l0 = raw_l0
        if "Unnamed" in l0 or l0 == "nan":
            l0 = last_valid_l0
        else:
            last_valid_l0 = l0
            
        full = f"{l0} {col[1]}".upper()
        
        # Determine Tax Head
        head = "unknown"
        if "IGST" in full: head = "igst"
        elif "CGST" in full: head = "cgst"
        elif "SGST" in full or "UTGST" in full: head = "sgst"
        elif "CESS" in full: head = "cess"
        
        # Determine Source
        source = "unknown"
        if ("DIFFERENCE" in full or "SHORT" in full) and "CUMULATIVE" not in full:
            source = "diff"
        elif "3B" in full or "DECLARED" in full:
            source = "3b"
        elif "REFERENCE" in full or "GSTR-1" in full or "RCM" in full or "EXPORT" in full or "SEZ" in full or "2B" in full:
            source = "ref"
            
        print(f"{i:<5} | {raw_l0[:28]:<30} | {l0[:28]:<30} | {str(col[1])[:13]:<15} | {source:<10} | {head:<10}")

        if source != "unknown" and head != "unknown":
            if (source, head) not in col_map:
                col_map[(source, head)] = i

    print("\n--- Final Column Map ---")
    print(col_map)
    
    # Check data values for first data row (Row 7 -> Index 0 in df)
    print("\n--- Data Check (First Row) ---")
    if len(df) > 0:
        row = df.iloc[0]
        print("Row Name:", row.iloc[0])
        for (src, head), idx in col_map.items():
            print(f"{src}-{head} (Idx {idx}): {row.iloc[idx]}")

if __name__ == "__main__":
    debug_columns()
