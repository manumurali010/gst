import sqlite3
import json

db_path = 'C:/Users/manum/.gemini/antigravity/scratch/gst/data/adjudication.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT issue_json FROM issues_data WHERE issue_id='ITC_MISMATCH'")
row = c.fetchone()
if row:
    data = json.loads(row[0])
    print(json.dumps(data, indent=2))
else:
    print("ITC_MISMATCH not found")

conn.close()
