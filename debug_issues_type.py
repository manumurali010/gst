
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
from src.services.scrutiny_parser import ScrutinyParser

def debug_types():
    parser = ScrutinyParser()
    extra_files = {
        'gstr3b_m1': 'GSTR3B_32AADFW8764E1Z1_042022.pdf'
    }
    
    print("Running parse_file...")
    try:
        issues = parser.parse_file("fakedoc.xlsx", extra_files, configs={"gstr3b_freq": "Monthly"}, gstr2a_analyzer=None)
        print(f"Returned {len(issues)} issues.")
        
        for i, issue in enumerate(issues):
            print(f"ISSUE[{i}] TYPE: {type(issue)}")
            if not isinstance(issue, dict):
                print(f"  -> VALUE: {repr(issue)}")
            else:
                 print(f"  -> ID: {issue.get('issue_id', 'UNKNOWN')}")
                 
    except Exception as e:
        print(f"Crash during parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_types()
