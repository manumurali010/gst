import sqlite3
import json
import os

DB_PATH = r"D:\gst\data\adjudication.db"

def inspect_issues(proceeding_id):
    print(f"--- Inspecting Proceeding: {proceeding_id} ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get Source Scrutiny ID
    cursor.execute("SELECT additional_details FROM proceedings WHERE id = ?", (proceeding_id,))
    row = cursor.fetchone()
    
    source_scrutiny_id = None
    if row:
        try:
            details = json.loads(row[0])
            source_scrutiny_id = details.get('source_scrutiny_id')
            print(f"Found Source Scrutiny ID: {source_scrutiny_id}")
        except:
            print("Could not parse additional_details")
    else:
        # Try adjudication_cases table if not in proceedings (though ID suggests it is)
        cursor.execute("SELECT source_scrutiny_id FROM adjudication_cases WHERE id = ?", (proceeding_id,))
        row_adj = cursor.fetchone()
        if row_adj:
            source_scrutiny_id = row_adj[0]
            print(f"Found Source Scrutiny ID (Adj Table): {source_scrutiny_id}")
        else:
            print("Proceeding not found in DB")
            return

    # 2. Check SCN Draft Issues (Current State)
    print(f"\n[SCN Draft] Issues for Proceeding {proceeding_id} (stage='SCN'):")
    cursor.execute("SELECT issue_id, origin, stage FROM case_issues WHERE proceeding_id = ? AND stage = 'SCN'", (proceeding_id,))
    scn_rows = cursor.fetchall()
    for r in scn_rows:
        print(f" - {r}")
    if not scn_rows:
        print(" -> NO ISSUES FOUND")

    # 3. Check Source ASMT-10 Issues (Source State)
    if source_scrutiny_id:
        print(f"\n[ASMT-10 Source] Issues for Scrutiny {source_scrutiny_id} (stage='DRC-01A'):")
        cursor.execute("SELECT issue_id, origin, stage, data_json FROM case_issues WHERE proceeding_id = ? AND stage = 'DRC-01A'", (source_scrutiny_id,))
        asmt_rows = cursor.fetchall()
        for r in asmt_rows:
            # Check for shortfall in data
            data = {}
            shortfall = "N/A"
            try:
                data = json.loads(r[3])
                shortfall = data.get('total_shortfall', 0)
            except: pass
            print(f" - ID: {r[0]}, Origin: {r[1]}, Shortfall: {shortfall}")
        
        if not asmt_rows:
            print(" -> NO ISSUES FOUND")
            
            # Check if maybe they are saved under stage='ASMT-10'?
            print(f"\n[ASMT-10 Check] Issues for Scrutiny {source_scrutiny_id} (stage='ASMT-10' ??):")
            cursor.execute("SELECT issue_id, origin, stage FROM case_issues WHERE proceeding_id = ?", (source_scrutiny_id,))
            all_source_rows = cursor.fetchall()
            for r in all_source_rows:
                print(f" - {r}")

    conn.close()

if __name__ == "__main__":
    inspect_issues("1fca6526-b15d-426b-9c9c-cb6c65d99753")
