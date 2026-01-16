import sqlite3
import json
import os

DB_FILE = os.path.join('data', 'adjudication.db')

def inspect_issue(issue_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM issues_master WHERE issue_id = ?", (issue_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        d = dict(row)
        print(f"ISSUE: {issue_id}")
        for k, v in d.items():
            if k in ['grid_data', 'table_definition', 'templates']:
                print(f"{k}: {v[:200] if v else 'None'}...")
        
        # Check for strings in grid_data
        if d.get('grid_data'):
            try:
                grid = json.loads(d['grid_data'])
                if isinstance(grid, list):
                    for r_idx, row in enumerate(grid):
                        for c_idx, cell in enumerate(row):
                            if isinstance(cell, str):
                                print(f"ALERT: String found in grid_data at Row {r_idx}, Col {c_idx}: {cell}")
            except Exception as e:
                print(f"Error parsing grid_data: {e}")

if __name__ == "__main__":
    inspect_issue('ISD_CREDIT_MISMATCH')
    inspect_issue('LIABILITY_3B_R1')
