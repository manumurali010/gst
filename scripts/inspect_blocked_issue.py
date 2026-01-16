import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def inspect_reference():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    issue_id = "SOP-1925D69B"
    print(f"Inspecting references for {issue_id}...")
    
    cursor.execute("SELECT * FROM case_issues WHERE issue_id = ?", (issue_id,))
    rows = cursor.fetchall()
    
    with open('blocked_info.txt', 'w') as f:
        if not rows:
            f.write("No references found in case_issues (Strange, script said Blocked).\n")
        else:
            f.write(f"Found {len(rows)} references:\n")
            for row in rows:
                f.write(f"ID: {row[0]} | Proceedings: {row[1]} | Stage: {row[3]}\n")
    
    conn.close()

if __name__ == "__main__":
    inspect_reference()
