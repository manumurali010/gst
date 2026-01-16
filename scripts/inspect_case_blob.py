import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Inspecting adjudication_cases ---")
# Get latest case
c.execute("SELECT id, legal_name, selected_issues FROM adjudication_cases ORDER BY created_at DESC LIMIT 1")
row = c.fetchone()

if row:
    print(f"Case ID: {row[0]}")
    print(f"Legal Name: {row[1]}")
    sel_issues = row[2]
    if sel_issues:
        try:
            issues = json.loads(sel_issues)
            print(f"Found {len(issues)} issues in selected_issues.")
            for iss in issues:
                iid = iss.get('issue_id')
                print(f"- {iid}")
                if iid == 'ITC_3B_2B_OTHER':
                    print("  MATCH FOUND!")
                    if 'grid_data' in iss:
                        print("  Has grid_data")
                    if 'summary_table' in iss:
                        print("  Has summary_table")
                        # Print first row of summary table to confirm structure
                        rows = iss['summary_table'].get('rows', [])
                        print(f"  Rows count: {len(rows)}")
                        if rows:
                            print(f"  Row 0: {rows[0]}")
        except Exception as e:
            print(f"JSON Error: {e}")
    else:
        print("selected_issues is NULL")
else:
    print("No cases found.")

conn.close()
