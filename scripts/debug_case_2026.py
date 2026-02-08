import sys
import os
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager
import json

def inspect_case():
    db = DatabaseManager()
    db.init_sqlite()
    
    print("Searching for Case 2/2026...")
    # Try different fields if strict match fails
    # Looking for OC Number 2/2026 in proceedings
    
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # Check proceedings table columns to be sure
    # cursor.execute("PRAGMA table_info(proceedings)")
    # print(cursor.fetchall())
    
    # Find the case
    cursor.execute("SELECT id, asmt10_snapshot, selected_issues, additional_details, created_at FROM proceedings WHERE oc_number = ?", ('2/2026',))
    rows = cursor.fetchall()
    
    if not rows:
        print("Case with OC Number '2/2026' NOT FOUND.")
        return

    print(f"Found {len(rows)} cases with OC 2/2026.")

    for idx, row in enumerate(rows):
        pid, snapshot_json, selected_issues_json, details, created_at = row
        print(f"\n--- CASE {idx+1} [ID: {pid}] Created: {created_at} ---")
        
        if snapshot_json:
            try:
                snapshot = json.loads(snapshot_json)
                issues = snapshot.get('issues', [])
                print(f"Snapshot Issues Count: {len(issues)}")
                for idx, i in enumerate(issues):
                    print(f"  [Snapshot Issue {idx+1}] ID: {i.get('issue_id')}, Shortfall: {i.get('total_shortfall')}, Category: {i.get('category')}")
            except Exception as e:
                print(f"Snapshot Parse Error: {e}")
    else:
        print("Snapshot is NULL.")

    # 2. Analyze Source (selected_issues)
    if selected_issues_json:
        try:
            # selected_issues might be double serialized?
            if isinstance(selected_issues_json, str):
                s_issues = json.loads(selected_issues_json)
            else:
                s_issues = selected_issues_json
                
            print(f"Source Selected Issues Count: {len(s_issues)}")
            for i in s_issues:
                # mimic logic
                val = i.get('total_shortfall', 0)
                try:
                    if isinstance(val, (int, float)): ts = float(val)
                    else: ts = float(str(val).replace(',', '').strip() or 0)
                except: ts = 0.0
                
                is_inc = i.get('is_included', True)
                print(f"  - Source Issue: {i.get('issue_id')}, Raw Shortfall: {val}, Parsed: {ts}, Included: {is_inc}")
                
        except Exception as e:
            print(f"Source Issues Parse Error: {e}")
    else:
        print("Source selected_issues is NULL.")

if __name__ == "__main__":
    inspect_case()
