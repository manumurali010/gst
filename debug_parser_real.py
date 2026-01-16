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
            tt = issue.get('template_type', 'none')
            print(f"\nIssue #{i+1}: {cat} (Template: {tt})")
            print(f"  [Value on Right Side of Card]: {shortfall:,.0f}")
            
            if 'summary_table' in issue:
                print("  [Summary Table Found]")
                # print(json.dumps(issue['summary_table'], indent=2))
                for r in issue['summary_table']['rows']:
                    h_list = issue['summary_table']['headers']
                    row_vals = ", ".join([f"{h_list[j+1]}={r.get(f'col{j+1}', 0)}" for j in range(len(h_list)-1)])
                    print(f"    - {r['col0'][:40]}...: {row_vals}")
            
            if 'rows' in issue and issue['rows']:
                print(f"  [Monthly Rows: {len(issue['rows'])}]")
                r0 = issue['rows'][0]
                print(f"    First row ({r0['period']}): 3B IGST={r0['3b']['igst']}, 2B IGST={r0['ref']['igst']}")
            else:
                print("  [No Monthly Rows]")
    else:
        print("No 'issues' key in result.")

if __name__ == "__main__":
    debug_run()
