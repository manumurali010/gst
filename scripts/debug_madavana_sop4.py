import os
import sys
import pandas as pd

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

import services.scrutiny_parser as sp
from services.gstr_2b_analyzer import GSTR2BAnalyzer
from utils.pdf_parsers import parse_gstr3b_pdf_table_4_a_5

def debug_madavana():
    pdf_path_3b = "GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    excel_paths_2b = [
        "062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "092022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "122022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
    ]
    
    # 1. Test 3B Parsing
    print(f"\n--- Testing 3B Parsing (Single File) ---")
    vals_3b = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
    if os.path.exists(pdf_path_3b):
        res_3b = parse_gstr3b_pdf_table_4_a_5(pdf_path_3b)
        print(f"[{pdf_path_3b}] Result: {res_3b}")
        if res_3b:
            for k in vals_3b: vals_3b[k] += res_3b.get(k, 0.0)
    else:
        print(f"3B File not found: {pdf_path_3b}")
    
    print(f"Total 3B (All Other ITC): {vals_3b}")

    # 2. Test 2B Parsing (Aggregated)
    print(f"\n--- Testing 2B Parsing (Aggregated 4 Files) ---")
    vals_2b = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
    
    for excel_path in excel_paths_2b:
        if os.path.exists(excel_path):
            try:
                analyzer = GSTR2BAnalyzer(excel_path)
                res_2b = analyzer.get_all_other_itc_raw_data()
                print(f"[{excel_path}] Result: {res_2b}")
                
                if res_2b:
                    for k in vals_2b: vals_2b[k] += res_2b.get(k, 0.0)
                else:
                    # Dump row if failed
                    pass 
            except Exception as e:
                print(f"[{excel_path}] Error: {e}")
        else:
             print(f"File not found: {excel_path}")

    print(f"Total 2B (All Other ITC): {vals_2b}")
    
    # 3. Compute Difference
    print("\n--- Computation (3B - 2B) ---")
    diff = {k: vals_3b[k] - vals_2b[k] for k in ["igst", "cgst", "sgst", "cess"]}
    liab = {k: max(0.0, diff[k]) for k in ["igst", "cgst", "sgst", "cess"]}
    total_shortfall = sum(liab.values())
    
    print(f"Difference: {diff}")
    print(f"Liability: {liab}")
    print(f"Total Shortfall: {total_shortfall}")
    
    if total_shortfall == 0:
        print("\nCONCLUSION: Result is PASS because 3B ITC is less than 2B ITC (likely due to missing 3B PDF files).")
    else:
        print("\nCONCLUSION: Result is FAIL (Issue Detected).")

if __name__ == "__main__":
    debug_madavana()
