import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def inject_dummy_reference():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Pick the first SOP- candidate to block
    cursor.execute("SELECT issue_id FROM issues_master WHERE issue_id LIKE 'SOP-%' LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("No candidates found to test blocking.")
        return

    issue_id = row[0]
    print(f"Injecting dummy reference for {issue_id} in case_issues...")
    
    # Insert dummy case_issue
    try:
        cursor.execute("""
            INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json, origin)
            VALUES (?, ?, ?, ?, ?)
        """, ("DUMMY_PROC_ID", issue_id, "DRC-01A", "{}", "SCRUTINY"))
        conn.commit()
        print("Injection successful.")
    except Exception as e:
        print(f"Injection failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_dummy_reference()
