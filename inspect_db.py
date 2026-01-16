import sqlite3
import json

db_path = 'C:/Users/manum/.gemini/antigravity/scratch/gst/data/adjudication.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT issue_json FROM issues_data WHERE issue_id = 'ITC_3B_2B_9X4'")
row = c.fetchone()
if row:
    data = json.loads(row[0])
    print(f"Issue ID: {data.get('issue_id')}")
    print(f"Has grid_data: {'grid_data' in data}")
    if 'grid_data' in data:
        print(f"Grid Data Rows: {len(data['grid_data'])}")
    print(f"Has SCN template: {'scn' in data.get('templates', {})}")
    print(f"SCN Template snippet: {data.get('templates', {}).get('scn')[:50] if data.get('templates', {}).get('scn') else 'None'}")
else:
    print("Not found")
conn.close()
