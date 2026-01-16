import os
import sys

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from services.gstr_2b_analyzer import GSTR2BAnalyzer

excel_paths_2b = [
    "062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
    "092022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
    "122022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
    "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
]

EXPECTED_GSTIN = "32AAMFM4610Q1Z0"
# FY might be tricky. The filenames suggest "2022-23" (since ending in 032023).
# Let's try to validate with "2022-23".
EXPECTED_FY = "2022-23"

def verify_validation():
    print("--- Verifying GSTR-2B Validation Logic ---")
    
    for path in excel_paths_2b:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        print(f"\nChecking {path}...")
        try:
            analyzer = GSTR2BAnalyzer(path)
            # simulate calling validate_file
            # Note: GSTR2BAnalyzer.validate_file signature: (expected_gstin, expected_fy)
            
            # We assume the metadata extraction inside validate_file works.
            # Let's see if it raises ValueError.
            
            analyzer.validate_file(EXPECTED_GSTIN, EXPECTED_FY)
            print("VALIDATION SUCCESS")
            
        except Exception as e:
            print(f"VALIDATION FAILED: {e}")

if __name__ == "__main__":
    verify_validation()
