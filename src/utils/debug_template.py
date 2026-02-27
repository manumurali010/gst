import sqlite3
import json

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(BASE_DIR, 'data', 'adjudication.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Fetch from issues_master and reconstruct JSON for debug viewing
c.execute("SELECT * FROM issues_master WHERE issue_id='IMPORT_ITC_MISMATCH'")
row = c.fetchone()
if row:
    # Mimic the reconstruction helper
    columns = [col[0] for col in c.description]
    d = dict(zip(columns, row))
    
    def safe_json(val):
        try: return json.loads(val) if val else {}
        except: return {}
        
    data = {
        "issue_id": d.get('issue_id'),
        "issue_name": d.get('issue_name'),
        "templates": safe_json(d.get('templates')),
        "grid_data": safe_json(d.get('grid_data')),
        "table_definition": safe_json(d.get('table_definition')),
        "analysis_type": d.get('analysis_type')
    }
    print(json.dumps(data, indent=2))
else:
    print("ITC_MISMATCH not found in issues_master")

conn.close()
