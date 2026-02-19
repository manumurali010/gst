
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.services.gstr_2b_analyzer import GSTR2BAnalyzer

file_path = r"c:\Users\manum\.gemini\antigravity\gst\032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

print(f"Testing GSTR2BAnalyzer with file: {file_path}")

try:
    analyzer = GSTR2BAnalyzer(file_path)
    print(f"Analyzer initialized. Using Light Parser: {analyzer.use_light_parser}")
    
    print("\n--- Testing RCM Inward Supplies ---")
    rcm_inward = analyzer.get_rcm_inward_supplies()
    print(f"Result: {rcm_inward}")
    
    print("\n--- Testing RCM Credit Notes ---")
    rcm_cn = analyzer.get_rcm_credit_notes()
    print(f"Result: {rcm_cn}")
    
    if rcm_inward:
        print("\nSUCCESS: RCM Inward Data Extracted")
    else:
        print("\nFAILURE: RCM Inward Data Missing")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
