
import sys
import os
sys.path.append(os.getcwd())
try:
    from src.services.gstr_2b_analyzer import GSTR2BAnalyzer
except ImportError:
    # Handle running from root or tests dir
    sys.path.append(os.path.dirname(os.getcwd()))
    from src.services.gstr_2b_analyzer import GSTR2BAnalyzer

import logging

# Configure logging to show INFO level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_rcm(file_path):
    print(f"\n--- Testing File: {os.path.basename(file_path)} ---")
    analyzer = GSTR2BAnalyzer(file_path)
    
    print(f"\n--- Testing Inward Supplies (RCM) ---")
    # This should now pick the LAST row if multiple found
    inward = analyzer.get_rcm_inward_supplies()
    
    if inward:
        print(f"SUCCESS: Found RCM Inward: {inward}")
    else:
        print("FAILURE: Could not find RCM Inward Supplies")
        inward = {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0}

    print(f"\n--- Testing Credit Notes (RCM) ---")
    cn = analyzer.get_rcm_credit_notes()
    if cn:
        print(f"SUCCESS: Found RCM Credit Notes: {cn}")
    else:
        print("FAILURE: Could not find RCM Credit Notes")
        cn = {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0}

    print(f"\n--- SOP 15 Simulation (Net 2B) ---")
    net_2b = {}
    for k in ['igst', 'cgst', 'sgst', 'cess']:
        val_inward = int(inward.get(k, 0))
        val_cn = int(cn.get(k, 0))
        net_2b[k] = val_inward - val_cn
        print(f"  {k.upper()}: {val_inward} (Inward) - {val_cn} (CN) = {net_2b[k]} (Net)")

if __name__ == "__main__":
    target = "D:/gst/032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
    if len(sys.argv) > 1:
        target = sys.argv[1]
        
    if os.path.exists(target):
         test_rcm(target)
    else:
         print(f"File not found: {target}")
