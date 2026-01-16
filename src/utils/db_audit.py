import sqlite3
import json

db_path = 'C:/Users/manum/.gemini/antigravity/scratch/gst/src/database/gst_scrutiny.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- AUDIT: KAITHARAN AGENCIES ---")
c.execute("SELECT CaseID, source_scrutiny_id FROM proceedings WHERE [Legal Name] LIKE '%Kaitharan%'")
procs = c.fetchall()
for pid, sid in procs:
    print(f"Case: {pid}, Source Scrutiny: {sid}")
    # ASMT-10 Issues
    c.execute("SELECT issue_id FROM case_issues WHERE proceeding_id=? AND stage='DRC-01A'", (sid,))
    asmt_issues = c.fetchall()
    print(f"  Finalized ASMT-10 Issues (Count: {len(asmt_issues)}): {asmt_issues}")
    
    # SCN Issues
    c.execute("SELECT issue_id, data_json FROM case_issues WHERE proceeding_id=? AND stage='SCN'", (pid,))
    scn_issues = c.fetchall()
    asmt_derived = [i for i in scn_issues if json.loads(i[1]).get('origin') == 'ASMT10']
    print(f"  SCN Hydrated ASMT-Derived Issues (Count: {len(asmt_derived)}): {asmt_derived}")

print("\n--- AUDIT: ZERO-ISSUE ENFORCEMENT ---")
# Find a case with no ASMT-10 issues
c.execute("SELECT CaseID, [Legal Name] FROM proceedings WHERE scrutiny_id IS NOT NULL AND status='finalised'")
finalized_scrutiny = c.fetchall()
for sid, name in finalized_scrutiny:
    c.execute("SELECT COUNT(*) FROM case_issues WHERE proceeding_id=? AND stage='DRC-01A'", (sid,))
    count = c.fetchone()[0]
    if count == 0:
        print(f"Scrutiny Case {sid} ({name}) has 0 finalized issues. (Enforcement Check)")

conn.close()
