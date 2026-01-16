import sqlite3
import json
import os

DB_PATH = 'data/adjudication.db'

def inspect_kaitharan():
    print("--- Inspecting Kaitharan Data ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
    row = cursor.fetchone()
    
    if not row:
        print("Kaitharan case not found.")
        return
        
    pid, issues_json = row
    print(f"Case ID: {pid}")
    
    if not issues_json:
        print("No selected_issues data found.")
        return
        
    try:
        data = json.loads(issues_json)
        # Parse output structure: {"metadata": ..., "issues": [...], "summary": ...}
        issues = data.get("issues", [])
        
        print(f"Total Issues: {len(issues)}")
        print("-" * 60)
        
        for i, issue in enumerate(issues):
            print(f"Issue #{i+1}")
            print(f"  ID: {issue.get('issue_id', 'MISSING')}")
            print(f"  Category: {issue.get('category')}")
            print(f"  SOP Point (in data): {issue.get('sop_point', 'Not Present')}")
            # Check for grid/table data
            if 'summary_table' in issue:
                print(f"  Has Summary Table: Yes ({len(issue['summary_table'].get('rows', []))} rows)")
            elif 'grid_data' in issue:
                print("  Has Grid Data: Yes")
            else:
                print("  No Table Data Found")
                
            print("-" * 30)
            
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    inspect_kaitharan()
