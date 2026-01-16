import sqlite3
import os
import json

db_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT issue_json FROM issues_data WHERE issue_id = 'SOP-76CB395D'")
row = cursor.fetchone()
if row:
    data = json.loads(row[0])
    print(json.dumps(data, indent=2))
else:
    print("Not found")
conn.close()
