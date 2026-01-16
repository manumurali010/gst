import sqlite3
import json
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'
TARGET_ISSUE = 'ITC_3B_2B_OTHER'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print(f"--- NUKING {TARGET_ISSUE} FROM ALL BLOBS ---")

# 1. Clean case_issues (Already did, but verify)
c.execute("UPDATE case_issues SET data_json='{}' WHERE issue_id=?", (TARGET_ISSUE,))
print(f"Cleared case_issues rows matching {TARGET_ISSUE} directly.")

# 2. Clean adjudication_cases.selected_issues
c.execute("SELECT id, selected_issues FROM adjudication_cases WHERE selected_issues LIKE ?", (f'%{TARGET_ISSUE}%',))
rows = c.fetchall()
count = 0
for r in rows:
    cid = r[0]
    blob = r[1]
    try:
        issues = json.loads(blob)
        new_issues = []
        modified = False
        for iss in issues:
            if iss.get('issue_id') == TARGET_ISSUE:
                # Remove grid_data and summary_table if present
                if 'grid_data' in iss: 
                    del iss['grid_data']
                    modified = True
                if 'summary_table' in iss:
                    del iss['summary_table']
                    modified = True
                new_issues.append(iss)
            else:
                new_issues.append(iss)
        
        if modified:
            c.execute("UPDATE adjudication_cases SET selected_issues=? WHERE id=?", (json.dumps(new_issues), cid))
            count += 1
            print(f"Cleaned Case {cid}")
            
    except: pass

print(f"Cleaned {count} cases in adjudication_cases.")
conn.commit()
conn.close()
