import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.services.scrutiny_parser import ScrutinyParser
except ImportError:
    # Handle running from root vs inside src?
    sys.path.append(os.getcwd())
    from src.services.scrutiny_parser import ScrutinyParser

def diagnostic_sop2():
    print("=== SOP-2 Diagnostic Tool ===")
    
    # mimic what we think the UI sends
    extra_files = {
        # Using a key that starts with 'gstr3b_monthly'
        "gstr3b_monthly_april": "C:/fake/path/GSTR3B_April.pdf",
        "gstr3b_monthly_may": "C:/fake/path/GSTR3B_May.pdf"
    }
    
    # Also test valid PDF mock (can't really mock file existence without touching disk)
    # So we'll trace if it ENTERs the function.
    
    parser = ScrutinyParser()
    
    # We want to see if 'gstr3b_pdf_list' gets populated.
    # We can inspect internal state if possible, or just run parse and catch errors (since files don't exist)
    
    print("\nRunning parser with keys: ", list(extra_files.keys()))
    try:
        # This will fail on file open, but we check logs/prints
        parser.parse_file("fakedoc.xlsx", extra_files, configs={"gstr3b_freq": "Monthly"}, gstr2a_analyzer=None) 
    except Exception as e:
        print(f"Parser validation crash (Expected): {e}")

    # VARIANT 2: Actual UI Keys (Confirmed via Code Analysis)
    # Using real provided file: GSTR3B_32AADFW8764E1Z1_042022.pdf
    real_pdf_path = os.path.join(os.getcwd(), 'GSTR3B_32AADFW8764E1Z1_042022.pdf')
    if not os.path.exists(real_pdf_path):
        print(f"WARNING: Real PDF not found at {real_pdf_path}. Using fake.")
        real_pdf_path = 'C:/fake/path/GSTR3B_April.pdf'
    else:
        print(f"SUCCESS: Found real PDF at {real_pdf_path}")

    extra_files_ui = {
        'gstr3b_m1': real_pdf_path, 
        # 'gstr3b_m2': 'C:/fake/path/GSTR3B_May.pdf' # Keep it simple with one valid file
    }
    
    print("\n--- TEST: Running parser with ACTUAL UI keys: ", list(extra_files_ui.keys()), " ---")
    try:
         res_ui = parser.parse_file("fakedoc.xlsx", extra_files_ui, configs={"gstr3b_freq": "Monthly"}, gstr2a_analyzer=None)
         issues_ui = res_ui['issues'] if isinstance(res_ui, dict) and 'issues' in res_ui else res_ui
         
         # Analyze results
         sop2 = next((i for i in issues_ui if i['issue_id'] == 'RCM_LIABILITY_ITC'), {})
         sop4 = next((i for i in issues_ui if i['issue_id'] == 'ITC_3B_2B_OTHER'), {})
         # SOP-11 issue ID is RULE_42_43_VIOLATION
         sop11 = next((i for i in issues_ui if i['issue_id'] == 'RULE_42_43_VIOLATION'), {})
         sop5 = next((i for i in issues_ui if i['issue_id'] == 'TDS_TCS_MISMATCH'), {})
         sop10 = next((i for i in issues_ui if i['issue_id'] == 'IMPORT_ITC_MISMATCH'), {})
         
         print(f"\n[SOP-2 Result] Status: {sop2.get('status')} | Msg: {sop2.get('status_msg')}")
         print(f"[SOP-4 Result] Status: {sop4.get('status')} | Msg: {sop4.get('status_msg')}")
         print(f"[SOP-5 Result] Status: {sop5.get('status')} | Msg: {sop5.get('status_msg')}")
         print(f"[SOP-10 Result] Status: {sop10.get('status')} | Msg: {sop10.get('status_msg')}")
         print(f"[SOP-11 Result] Status: {sop11.get('status')} | Msg: {sop11.get('status_msg')}")
         
    except Exception as e:
         print(f"Parser crash (Unexpected): {e}")

    # TEST 3: Parser Reachability
    print("\n--- TEST: Parser Function Reachability ---")
    try:
        from src.services.pdf_parsers import parse_gstr3b_pdf_table_3_1_d
        # We pass a fake path, it should fail with FileNotFoundError, NOT ImportError or AttributeError
        try:
            parse_gstr3b_pdf_table_3_1_d('C:/fake/path.pdf')
        except FileNotFoundError:
            print("Accessible: YES (FileNotFoundError)")
        except Exception as e:
            msg = str(e)
            if "No such file" in msg:
                 print("Accessible: YES (os error)")
            else:
                 print(f"Accessible: ERROR ({e})")
    except ImportError:
        print("Accessible: NO (ImportError)")

if __name__ == "__main__":
    diagnostic_sop2()
