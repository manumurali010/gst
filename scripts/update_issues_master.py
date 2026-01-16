import sqlite3
import json
import sys
import os

sys.path.append(os.getcwd())
from src.utils.initialize_scrutiny_master import issues

DB_PATH = 'data/adjudication.db'

def update_master():
    print("--- Updating Issues Master with SOP Points ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists, if not create it?
    # Actually, issues_master usually stores JSON blobs or specific cols.
    # Let's check table schema first.
    cursor.execute("PRAGMA table_info(issues_master)")
    cols = [r[1] for r in cursor.fetchall()]
    
    if 'sop_point' not in cols:
        print("Adding 'sop_point' column...")
        try:
            cursor.execute("ALTER TABLE issues_master ADD COLUMN sop_point INTEGER")
        except Exception as e:
            print(f"Error adding column: {e}")
            
    # Update records
    for issue in issues:
        iid = issue['issue_id']
        sop = issue.get('sop_point')
        
        if sop:
             print(f"Updating {iid} -> SOP Point {sop}")
             cursor.execute("UPDATE issues_master SET sop_point = ? WHERE issue_id = ?", (sop, iid))
             
             # Also update the 'grid_data' and 'issue_name' in case they changed (e.g. Import ITC name fix)
             # Serializing grid_data
             grid_json = json.dumps(issue.get('grid_data'))
             name = issue.get('issue_name')
             cursor.execute("UPDATE issues_master SET grid_data = ?, issue_name = ? WHERE issue_id = ?", (grid_json, name, iid))

    conn.commit()
    print("Update Complete.")
    conn.close()

if __name__ == "__main__":
    update_master()
