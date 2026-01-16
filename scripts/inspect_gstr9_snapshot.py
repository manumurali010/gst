import sys
import os
import json
sys.path.append(os.getcwd())
import sqlite3

DB_PATH = 'data/adjudication.db'

def inspect_gstr9():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        print("No Kaitharan data")
        return
        
    data = json.loads(row[0])
    if isinstance(data, dict):
        issues = data.get('issues', [])
    else:
        issues = data
        
    target_issue = next((i for i in issues if i.get('issue_id') == 'ITC_3B_2B_9X4'), None)
    
    if not target_issue:
        print("Point 12 (ITC_3B_2B_9X4) not found.")
        return
        
    print("Snapshot Keys:")
    snap = target_issue.get('snapshot')
    if not snap:
        print("  Snapshot is Empty or None")
    else:
        for k, v in snap.items():
            print(f"  {k}: {v}")
            
if __name__ == "__main__":
    inspect_gstr9()
