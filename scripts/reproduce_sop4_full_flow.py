import os
import sys

BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from services.scrutiny_parser import ScrutinyParser

def reproduce_full_flow():
    print("--- Reproducing SOP-4 Full Flow ---")
    
    # 1. Setup Paths
    excel_paths_2b = [
        "062022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "092022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "122022_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx",
        "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"
    ]
    pdf_path_3b = "GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    # Verify existence
    params = {'gstr_2b': [], 'gstr3b_pdf': []}
    for p in excel_paths_2b:
        if os.path.exists(p): 
            params['gstr_2b'].append(os.path.abspath(p))
        else: print(f"Missing: {p}")
        
    if os.path.exists(pdf_path_3b):
         params['gstr3b_pdf'].append(os.path.abspath(pdf_path_3b))
    else: print(f"Missing: {pdf_path_3b}")

    # 2. Run Parser
    # Dummy Main File (using one of the 2Bs as a dummy excel to satisfy signature, 
    # though parser usually expects Tax Liability excel as main. 
    # Let's use the legacy Tax Liability file as main to be realistic)
    main_file = "2022-23_32AAMFM4610Q1Z0_Tax liability and ITC comparison.xlsx"
    if not os.path.exists(main_file):
        print("Main file missing, using dummy")
        main_file = excel_paths_2b[0] # Fallback
    
    print(f"Main File: {main_file}")
    print(f"Extra Files: {params}")

    parser = ScrutinyParser()
    res = parser.parse_file(os.path.abspath(main_file), extra_files=params)
    
    # 3. Inspect Result
    issues = res.get('issues', [])
    sop4 = next((i for i in issues if i.get('issue_id') == "ITC_3B_2B_OTHER"), None)
    
    if sop4:
        print(f"\nSOP-4 Result:")
        print(f"Status: {sop4.get('status')}")
        print(f"Msg: {sop4.get('status_msg')}")
        print(f"Shortfall: {sop4.get('total_shortfall')}")
        if sop4.get('status') == 'info':
            print("FAILURE REPRODUCED: Analysis Incomplete.")
        else:
            print("SUCCESS: Issue detected correctly.")
    else:
        print("SOP-4 Issue NOT FOUND in results.")

if __name__ == "__main__":
    reproduce_full_flow()
