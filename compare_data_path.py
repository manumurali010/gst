
import sqlite3
import json
import os

DB_PATHS = ["data/adjudication.db"]

def compare_data_path():
    db_path = None
    for p in DB_PATHS:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        print("ERROR: DB not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- Finding Overlapping Issues ---")
    cursor.execute("""
        SELECT issue_id, COUNT(*) as cnt 
        FROM case_issues 
        WHERE stage IN ('DRC-01A', 'SCN')
        GROUP BY issue_id 
        HAVING cnt > 1
        LIMIT 5
    """)
    overlaps = cursor.fetchall()
    
    if not overlaps:
        print("No overlapping issues found between stages.")
        # Fallback: Just dump Rule 42/43 if exists
        targets = ['RULE_42_43_VIOLATION']
    else:
        targets = [row['issue_id'] for row in overlaps]
        print(f"Comparing Issues: {targets}")

    for tid in targets:
        print(f"\n=== COMPARING ISSUE: {tid} ===")
        cursor.execute("SELECT id, stage, data_json FROM case_issues WHERE issue_id = ? ORDER BY id DESC", (tid,))
        rows = cursor.fetchall()
        
        for row in rows:
            print(f"\n[RowID {row['id']}] Stage: {row['stage']}")
            try:
                data = json.loads(row['data_json'])
                keys = list(data.keys())
                print(f"Keys: {keys}")
                
                # Check for Baked Indicators
                baked_grid = False
                if 'summary_table' in data and data['summary_table']:
                     rows_st = data['summary_table'].get('rows', [])
                     if rows_st and isinstance(rows_st[0], dict) and 'col0' in rows_st[0]:
                          val = rows_st[0]['col0'].get('value')
                          print(f"SummaryTable Row0 Col0 Value: {val}")
                          baked_grid = True
                
                print(f"Baked/Frozen Structure: {baked_grid}")
                
                if 'brief_facts' in data:
                     print(f"Brief Facts (Top Level): {str(data['brief_facts'])[:40]}...")
            except Exception as e:
                print(f"JSON Error: {e}")

    conn.close()

if __name__ == "__main__":
    compare_data_path()
