import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def inspect_findings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Inspecting 'selected_issues' column in 'proceedings' table...")
    
    cursor.execute("SELECT id, legal_name, selected_issues FROM proceedings WHERE selected_issues IS NOT NULL")
    rows = cursor.fetchall()
    
    found_sop = False
    
    if not rows:
        print("No rows with non-null 'findings' found.")
    else:
        for r in rows:
            pid = r[0]
            name = r[1]
            findings_str = r[2]
            print(f"Prop ID: {pid} | Name: {name}")
            
            try:
                findings = json.loads(findings_str)
                # findings might be a list of issues or a dict
                print(f"  Findings Type: {type(findings)}")
                
                if isinstance(findings, list):
                    for idx, issue in enumerate(findings):
                        iid = issue.get('issue_id')
                        print(f"    Issue {idx}: {iid}")
                        if idx == 0 and isinstance(issue, dict):
                             print(f"    Sample Keys: {list(issue.keys())}")
                             print(f"    Template Type: {issue.get('template_type')}")
                             # Check for table headers signature
                             if 'issue_table_data' in issue:
                                 print(f"    Table Headers: {issue['issue_table_data'].get('headers')}")
                        
                        if iid and iid.startswith('SOP-'):
                            found_sop = True
                elif isinstance(findings, dict):
                     # Maybe keys are IDs?
                     print(f"    Keys: {list(findings.keys())}")
                     
            except Exception as e:
                print(f"  Error parsing JSON: {e}")
                print(f"  Raw: {findings_str[:100]}...")

    if not found_sop:
        print("\nNo SOP-* IDs found in 'findings' column either.")
        
    conn.close()

if __name__ == "__main__":
    inspect_findings()
