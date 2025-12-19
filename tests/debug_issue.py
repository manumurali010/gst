import sqlite3
import json

conn = sqlite3.connect(r'c:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System\data\adjudication.db')
c = conn.cursor()

c.execute("""
    SELECT m.issue_id, m.issue_name, d.issue_json 
    FROM issues_master m
    JOIN issues_data d ON m.issue_id = d.issue_id
    WHERE m.issue_name LIKE '%GSTR 1%'
""")
rows = c.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]}")
    data = json.loads(row[2])
    print(f"Keys: {list(data.keys())}")
    
    if 'grid_data' in data:
        print("Structure: grid_data")
        grid = data['grid_data']
        if len(grid) > 2:
           print("Row 2 data:")
           print(json.dumps(grid[2], indent=2))
            
    elif 'tables' in data:
        print("Structure: tables (dict)")
        print(json.dumps(data['tables'], indent=2))
    elif 'table' in data:
        print("Structure: table (legacy)")
        
conn.close()
