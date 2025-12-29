import sys
import os
import pandas as pd
import json

# Add src to path
sys.path.append(os.path.abspath('.'))

from src.services.scrutiny_parser import ScrutinyParser

def debug_run():
    parser = ScrutinyParser()
    file_path = "2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Analyzing {file_path}...")
    
    # Run Valid Parser
    res = parser.parse_file(file_path)
    
    print("\n--- Parsed Issues ---")
    if 'issues' in res:
        for i, issue in enumerate(res['issues']):
            cat = issue.get('category', 'Unknown')
            shortfall = issue.get('total_shortfall', 0)
            print(f"\nIssue #{i+1}: {cat} (Shortfall: {shortfall})")
            
            if 'summary_table' in issue:
                print("  [Summary Table Found]")
                print(json.dumps(issue['summary_table'], indent=2))
            else:
                print("  [No Summary Table]")
    else:
        print("No 'issues' key in result.")

if __name__ == "__main__":
    debug_run()
