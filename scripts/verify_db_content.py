import sqlite3
import json
import os
import sys

# DB Path from schema.py logic
DB_PATH = r"d:\gst\data\adjudication.db"

def check_sop1_schema():
    print(f"Connecting to DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB file not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        issue_id = "LIABILITY_3B_R1"
        cursor.execute("SELECT table_definition, active, updated_at FROM issues_master WHERE issue_id = ?", (issue_id,))
        row = cursor.fetchone()

        if not row:
            print(f"ERROR: Issue {issue_id} not found in issues_master.")
            return

        print(f"--- Issue: {issue_id} ---")
        print(f"Active: {row['active']}")
        print(f"Updated At: {row['updated_at']}")
        
        table_def_json = row['table_definition']
        print(f"Table Definition Raw Length: {len(table_def_json) if table_def_json else 0}")

        if table_def_json:
            try:
                table_def = json.loads(table_def_json)
                print("\nParsed Table Definition:")
                
                rows = table_def.get('rows', [])
                print(f"Total Rows: {len(rows)}")
                
                print("\nRow Labels:")
                for i, r in enumerate(rows):
                    print(f"Row {i}: {r.get('label', 'N/A')}")
                    
                # Specific check for the new row
                labels = [r.get('label', '') for r in rows]
                if "Liability (Positive Only)" in labels:
                    print("\n[SUCCESS] 'Liability (Positive Only)' row found!")
                else:
                    print("\n[FAILURE] 'Liability (Positive Only)' row NOT found.")

            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse JSON table_definition: {e}")
        else:
            print("ERROR: table_definition is empty or NULL")

        conn.close()

    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    check_sop1_schema()
