
import sqlite3
import json
import os

DB_PATH = os.path.join("data", "adjudication.db")

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("--- Inspecting case_issues ---")
    try:
        c.execute("SELECT id, issue_id, data_json FROM case_issues LIMIT 5")
        rows = c.fetchall()
        if not rows:
            print("No case_issues found.")
        else:
            for r in rows:
                cid, iid, djson = r
                print(f"ID: {cid}, IssueID: {iid}")
                if djson:
                    try:
                        data = json.loads(djson)
                        # Check if 'issue_name' or similar is stored in the blob
                        keys_with_name = [k for k in data.keys() if 'name' in k.lower()]
                        print(f"  Keys with 'name': {keys_with_name}")
                        if 'issue_name' in data:
                             print(f"  [WARNING] 'issue_name' found in blob: {data['issue_name']}")
                    except:
                        print("  [ERROR] Invalid JSON")
    except Exception as e:
        print(f"Error querying case_issues: {e}")

    conn.close()

if __name__ == "__main__":
    check_db()
