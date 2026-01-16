import sys
import os
import json
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager
import sqlite3

DB_PATH = 'data/adjudication.db'

def inspect_values():
    print("--- Inspecting Snapshot vs Master Schema ---")
    
    # 1. Get Persisted Snapshot (Parser Output)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        print("No Kaitharan data")
        return
        
    data = json.loads(row[0])
    if isinstance(data, list):
        issues = data
    else:
        issues = data.get('issues', [])
    
    # Look for LIABILITY_3B_R1 (Point 1)
    target_issue = next((i for i in issues if i.get('issue_id') == 'LIABILITY_3B_R1'), None)
    
    if not target_issue:
        print("LIABILITY_3B_R1 not found in case data.")
    else:
        print("\n[Parser Output] Snapshot Keys/Values:")
        snapshot = target_issue.get('snapshot', {})
        for k, v in snapshot.items():
            print(f"  {k}: {v}")
            
    # 2. Get Master Grid Schema (Expected Vars)
    db = DatabaseManager()
    master = db.get_issue("LIABILITY_3B_R1")
    
    if not master:
        print("Master issue not found.")
        return
        
    print("\n[Master Schema] Grid Data Vars:")
    grid = master.get('grid_data', [])
    if isinstance(grid, list):
        for r_idx, row in enumerate(grid):
            for c_idx, cell in enumerate(row):
                if 'var' in cell:
                    print(f"  Row {r_idx} Col {c_idx}: var='{cell['var']}' (Default: {cell.get('value')})")
    
if __name__ == "__main__":
    inspect_values()
