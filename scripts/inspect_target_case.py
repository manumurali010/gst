import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'
target_case_id = '60fed7b8-1cb6-41da-ba86-29ab865a1c3f'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print(f"--- Inspecting Case {target_case_id} ---")
c.execute("SELECT id, legal_name, selected_issues FROM adjudication_cases WHERE id=?", (target_case_id,))
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
                if iss.get('issue_id') == 'ITC_3B_2B_OTHER':
                    print("  MATCH FOUND: ITC_3B_2B_OTHER")
                    if 'summary_table' in iss:
                        print("  Has summary_table")
                        rows = iss['summary_table'].get('rows', [])
                        print(f"  Rows count: {len(rows)}")
                        if len(rows) > 0:
                            print(f"  Row 0: {rows[0]}")
                            
            # If found, wipe it?
            # Better to confirm first.
        except Exception as e:
            print(f"JSON Error: {e}")
    else:
        print("selected_issues is NULL")
else:
    print("Case not found.")

conn.close()
