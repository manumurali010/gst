import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT id, data_json FROM case_issues WHERE issue_id='ITC_3B_2B_OTHER'")
rows = c.fetchall()
print(f"Found {len(rows)} matching case_issues rows.")

updates_count = 0
for row in rows:
    rid = row[0]
    try:
        data = json.loads(row[1])
        modified = False
        
        if 'grid_data' in data:
             print(f"Row {rid}: Removing grid_data")
             del data['grid_data']
             modified = True
             
        if 'summary_table' in data:
             print(f"Row {rid}: Removing summary_table")
             del data['summary_table']
             modified = True
             
        if modified:
             new_json = json.dumps(data)
             c.execute("UPDATE case_issues SET data_json=? WHERE id=?", (new_json, rid))
             updates_count += 1
    except json.JSONDecodeError:
        print(f"Row {rid}: Invalid JSON")

conn.commit()
print(f"Updated {updates_count} rows.")
conn.close()
