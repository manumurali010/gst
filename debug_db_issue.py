
import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = r"c:\Users\manum\.gemini\antigravity\gst\data\adjudication.db"

def check_issue():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    issue_id = "IMPORT_ITC_MISMATCH"
    c.execute("SELECT grid_data, templates FROM issues_master WHERE issue_id = ?", (issue_id,))
    row = c.fetchone()
    
    if row:
        grid_raw = row[0]
        templates_raw = row[1]
        print(f"--- ISSUE: {issue_id} ---")
        print(f"Raw Grid Data Type: {type(grid_raw)}")
        print(f"Raw Grid Data Length: {len(grid_raw) if grid_raw else 0}")
        print(f"Raw Grid Data Content (First 100 chars): {str(grid_raw)[:100]}")
        
        try:
            grid_json = json.loads(grid_raw) if grid_raw else None
            print(f"Parsed Grid Data Type: {type(grid_json)}")
            print(f"Parsed Grid Keys: {grid_json.keys() if isinstance(grid_json, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            
    else:
        print(f"Issue {issue_id} NOT FOUND in issues_master")
        
    conn.close()

if __name__ == "__main__":
    check_issue()
