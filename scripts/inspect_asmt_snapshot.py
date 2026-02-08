import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\gst\data\adjudication.db'
if not os.path.exists(db_path):
    print(f"Error: DB file not found at {db_path}")
    import sys
    sys.exit(1)

def inspect_db():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Search for the case in the screenshot (OC 3/2026)
        cursor.execute("SELECT id, gstin, asmt10_snapshot, selected_issues FROM proceedings WHERE oc_number LIKE '%3/2026%'")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} cases matching OC 3/2026")
        
        for row in rows:
            print("-" * 50)
            print(f"ID: {row[0]}")
            print(f"GSTIN: {row[1]}")
            
            snapshot_json = row[2]
            if snapshot_json:
                print("Snapshot found in DB.")
                try:
                    snapshot = json.loads(snapshot_json)
                    print(f"Snapshot Version: {snapshot.get('version')}")
                    print(f"Case Data Keys: {list(snapshot.get('case_data', {}).keys())}")
                    issues = snapshot.get('issues', [])
                    print(f"Number of Issues in Snapshot: {len(issues)}")
                    if issues:
                        print("First Issue Keys:", list(issues[0].keys()))
                        print("First Issue Sample Data:", json.dumps(issues[0], indent=2)[:500])
                except Exception as e:
                    print(f"Snapshot JSON load failure: {e}")
            else:
                print("Snapshot NOT found in DB.")
                
            selected_issues_json = row[3]
            if selected_issues_json:
                try:
                    selected = json.loads(selected_issues_json)
                    print(f"Legacy selected_issues count: {len(selected)}")
                except:
                    print("Legacy selected_issues load failure.")
                    
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    inspect_db()
