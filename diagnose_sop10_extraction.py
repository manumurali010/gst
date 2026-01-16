
import sys
import os
import logging

# Setup path
sys.path.append(os.getcwd())

from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

def run_diagnosis(file_path):
    print(f"\n--- RUNNING SOP-10 DIAGNOSIS ON: {os.path.basename(file_path)} ---")
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return

    analyzer = GSTR2AAnalyzer(file_path)
    if not analyzer.load_file():
        print("ERROR: Failed to load Excel file.")
        return
        
    print(f"Sheet Names: {analyzer.xl_file.sheet_names}")
    
    try:
        result = analyzer.analyze_sop(10)
        print(f"\nSOP-10 Final Result: {result}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Target the GSTR-2B file found in directory
    target_file = os.path.abspath("032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx")
    run_diagnosis(target_file)
