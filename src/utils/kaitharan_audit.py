import sqlite3
import json
import os

db_path = 'C:/Users/manum/.gemini/antigravity/scratch/gst/data/adjudication.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("\n--- SEARCH: Kaitharan (Join Audit) ---")
# Join proceedings with adjudication_cases to get source_scrutiny_id
query = """
SELECT p.id, p.legal_name, p.asmt10_status, a.source_scrutiny_id, a.id as adj_id
FROM proceedings p
LEFT JOIN adjudication_cases a ON p.adjudication_case_id = a.id
WHERE p.legal_name LIKE '%Kaitharan%'
"""
c.execute(query)
rows = c.fetchall()

if not rows:
    print("No Kaitharan case found.")
else:
    for row in rows:
        pid, name, status, ssid, adj_id = row
        print(f"Proceeding ID: {pid}, Name: {name}, Status: {status}")
        print(f"  Adjudication Case ID: {adj_id}")
        print(f"  Source Scrutiny ID: {ssid}")
        
        # Check source issues
        if ssid:
            print(f"  Checking case_issues for source_scrutiny_id: {ssid}")
            c.execute("SELECT issue_id, stage, data_json FROM case_issues WHERE proceeding_id=? AND stage='DRC-01A'", (ssid,))
            issues = c.fetchall()
            print(f"  Found {len(issues)} issues in DRC-01A stage for SOURCE.")
            for i_id, stage, data_json in issues:
                data = json.loads(data_json)
                print(f"    - ID: {i_id}, Shortfall: {data.get('total_shortfall')}, Desc: {data.get('description')}")
        
        # Check own issues
        print(f"  Checking case_issues for own proceeding_id: {pid}")
        c.execute("SELECT issue_id, stage, data_json FROM case_issues WHERE proceeding_id=?", (pid,))
        own_issues = c.fetchall()
        for i_id, stage, data_json in own_issues:
             print(f"    - Stage: {stage}, ID: {i_id}")

conn.close()
