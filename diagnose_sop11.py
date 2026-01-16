
import sys
import os
import logging

# Ensure src is in path
sys.path.append(os.getcwd())

from src.services.scrutiny_parser import ScrutinyParser

# Configure logging to stdout to capture our tags
logging.basicConfig(level=logging.WARNING, format='%(message)s')

def diagnose_strict():
    print("--- SOP-11 HARD PROOF DIAGNOSTIC ---")
    
    target_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    
    if not os.path.exists(target_pdf):
        print(f"CRITICAL: Target PDF not found at {target_pdf}")
        # Try finding it in current dir just in case
        local_path = os.path.join(os.getcwd(), "GSTR3B_32AADFW8764E1Z1_022023.pdf")
        if os.path.exists(local_path):
             target_pdf = local_path
             print(f"Found at {target_pdf}")
        else:
             return

    # Mock Inputs
    file_paths = {
        "gstr3b_feb_2023": target_pdf
    }
    
    configs = {
        "gstin": "32AADFW8764E1Z1"
    }
    
    parser = ScrutinyParser()
    
    print(f"Targeting PDF: {target_pdf}")
    print("Invoking ScrutinyParser...")
    
    # We pass None for main_file as we only care about the extra_files iteration for SOP-11
    try:
        results = parser.parse_file(None, file_paths, configs)
    except Exception as e:
        print(f"Parser Crash: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_strict()
