import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Inspecting issues_data ---")
try:
    c.execute("SELECT issue_id, issue_json FROM issues_data WHERE issue_id='ITC_3B_2B_OTHER'")
    row = c.fetchone()
    if row:
        print("Found matching row in issues_data.")
        try:
            data = json.loads(row[1])
            if 'grid_data' in data:
                 print("Has grid_data in issue_json")
                 print(str(data['grid_data'])[:100])
        except:
            print("Invalid JSON in issues_data")
    else:
        print("No row in issues_data")
except Exception as e:
    print(f"Error inspecting issues_data: {e}")

print("\n--- Finding active cases with issues ---")
c.execute("SELECT id, legal_name FROM adjudication_cases WHERE selected_issues IS NOT NULL LIMIT 5")
rows = c.fetchall()
for r in rows:
    print(f"Case {r[0]}: {r[1]}")

conn.close()
