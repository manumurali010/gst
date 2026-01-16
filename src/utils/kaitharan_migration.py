import sqlite3
import json
import os

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(BASE_DIR, 'data', 'adjudication.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Get current state
print("--- MIGRATION: Kaitharan ---")
c.execute("SELECT id, legal_name, selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
row = c.fetchone()
if not row:
    print("No Kaitharan case found.")
    exit()

pid, name, selected_json = row
issues = json.loads(selected_json) if selected_json else []
print(f"Found {len(issues)} issues in selected_issues.")

# 2. Filter for active issues (shortfall > 0)
active_issues = [i for i in issues if float(i.get('total_shortfall', 0)) > 0]
print(f"Active issues identified: {len(active_issues)}")

# 3. Migrate to case_issues (DRC-01A)
# Delete existing DRC-01A for this proceeding to be clean
c.execute("DELETE FROM case_issues WHERE proceeding_id=? AND stage='DRC-01A'", (pid,))

for item in active_issues:
    issue_id = item.get('sop_point_id') or item.get('category', 'unknown_issue')
    data_json = json.dumps(item)
    category = item.get('category')
    description = item.get('description')
    amount = float(item.get('total_shortfall', 0))
    
    c.execute("""
        INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json, category, description, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (pid, issue_id, 'DRC-01A', data_json, category, description, amount))

conn.commit()
print("Migration successful. case_issues (DRC-01A) populated.")

# 4. Verify count
c.execute("SELECT COUNT(*) FROM case_issues WHERE proceeding_id=? AND stage='DRC-01A'", (pid,))
count = c.fetchone()[0]
print(f"Verified count in DRC-01A: {count}")

conn.close()
