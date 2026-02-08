
import sqlite3
import json
import os
import sys

DB_PATHS = ["data/adjudication.db"]

def audit_data_path():
    db_path = None
    for p in DB_PATHS:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        print(f"ERROR: No database found. Checked: {DB_PATHS}")
        return

    print(f"Using Database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- 1. Listing Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print([t[0] for t in tables])

    print("\n--- 2. Dumping Recent Case Issues (Direct) ---")
    # Fetch most recently added issues to see what is being written
    cursor.execute("SELECT id, stage, issue_id, data_json, proceeding_id FROM case_issues ORDER BY id DESC LIMIT 5")
    issues = cursor.fetchall()
    
    if not issues:
        print("No issues found in case_issues table.")
        return

    for idx, row in enumerate(issues):
        print(f"\n[ISSUE #{idx+1} (RowID: {row['id']})] ID: {row['issue_id']} (Stage: {row['stage']}) ProcID: {row['proceeding_id']}")
        try:
            payload = json.loads(row['data_json'])
            
            # CHECK 1: Nested Structure
            print(f"Keys: {list(payload.keys())}")
            
            # CHECK 2: Frozen Artifact keys
            has_grid = 'grid_data' in payload
            has_facts = 'brief_facts' in payload
            
            print(f"Has grid_data: {has_grid}")
            print(f"Has brief_facts: {has_facts}")
            
            if has_facts:
                print(f"Brief Facts Snippet: {str(payload['brief_facts'])[:50]}...")
            
            if has_grid:
                grid = payload['grid_data']
                if isinstance(grid, dict):
                    print(f"Grid Columns: {len(grid.get('columns', []))}")
                    rows = grid.get('rows', [])
                    print(f"Grid Rows: {len(rows)}")
                    if rows:
                        print(f"Row 0 Raw: {rows[0]}")
                else:
                    print(f"Grid Type: {type(grid)}")

            print(f"\nFULL JSON BLOB (Unformatted):")
            print(row['data_json'])
            
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw Data: {row['data_json']}")

    conn.close()

if __name__ == "__main__":
    audit_data_path()
