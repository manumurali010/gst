import sqlite3
import json

db_path = 'data/adjudication.db'
try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    issue_id = 'd574a307-7a23-432e-824a-a48533279140'
    print(f"--- Inspecting Issue UUID: {issue_id} ---")
    
    # Try issues_data first
    cursor.execute("SELECT issue_json FROM issues_data WHERE issue_id=?", (issue_id,))
    tpl = cursor.fetchone()
    
    if not tpl:
        # Try templates table?
        cursor.execute("SELECT content FROM templates WHERE id=?", (issue_id,))
        tpl = cursor.fetchone()
        if tpl:
             print("Found in 'templates' table.")
             data = json.loads(tpl['content'])
        else:
             print("Template not found in DB.")
             data = None
    else:
        print("Found in 'issues_data' table.")
        data = json.loads(tpl['issue_json'])
        
    if data:
        print(f"Template Keys: {data.keys()}")
        if 'tables' in data:
            print(f"tables metadata: {data['tables']}")
        if 'tax_demand_mapping' in data:
            print(f"tax_demand_mapping: {data['tax_demand_mapping']}")
        else:
            print("tax_demand_mapping: MISSING")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if conn: conn.close()
