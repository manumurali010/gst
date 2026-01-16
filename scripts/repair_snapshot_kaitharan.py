import sqlite3
import json
import os
import sys

DB_PATH = 'data/adjudication.db'

def repair_snapshots():
    print("--- Repairing Snapshots for Kaitharan ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
    row = cursor.fetchone()
    
    if not row:
        print("Kaitharan case not found.")
        conn.close()
        return

    pid, issues_json = row
    if not issues_json:
        print("No issues data.")
        conn.close()
        return

    try:
        issues = json.loads(issues_json)  
        if isinstance(issues, dict): issues = issues.get('issues', [])
    except:
        print("JSON decode error")
        conn.close()
        return

    updated_count = 0
    for issue in issues:
        # Check if we have table data but no snapshot (or check if we can enhance it)
        table = issue.get('issue_table_data', {})
        rows = table.get('rows', [])
        
        if not rows:
            print(f"Skipping {issue.get('issue_id')}: No table rows.")
            continue
            
        print(f"Repairing {issue.get('issue_id')} ({len(rows)} rows)...")
        
        snapshot = issue.get('snapshot', {})
        
        # Map rows to rowX_colY
        # Schema assumes Col 1=IGST, 2=CGST, 3=SGST, 4=Cess
        # Table rows in issue_table_data are:
        # {col0: Desc, col1: IGST, col2: CGST...}
        
        for i, r in enumerate(rows):
            row_idx = i + 1
            # Check keys col1..col4
            for c_idx in range(1, 5): # 1 to 4
                key = f"col{c_idx}"
                val = r.get(key, 0)
                
                # Map to var names: row{i}_igst, _cgst, _sgst, _cess
                # Col 1 -> igst, 2 -> cgst, 3 -> sgst, 4 -> cess
                suffix = ["", "igst", "cgst", "sgst", "cess"][c_idx]
                var_name = f"row{row_idx}_{suffix}"
                
                snapshot[var_name] = val
                
        issue['snapshot'] = snapshot
        updated_count += 1

    # Save back
    new_json = json.dumps({"issues": issues}) # Wrap in dict as per standard
    cursor.execute("UPDATE proceedings SET selected_issues = ? WHERE proceeding_id = ?", (new_json, pid))
    conn.commit()
    conn.close()
    
    print(f"Repaired {updated_count} issues. DB Updated.")

if __name__ == "__main__":
    repair_snapshots()
