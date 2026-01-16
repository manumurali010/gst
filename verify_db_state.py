
import sqlite3
import os
import sys
import json

# Adjust path to import src
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.database.db_manager import DatabaseManager
    # db_mgr = DatabaseManager() # Don't need instance if we know path
    # Path is usually available or we can guess. schema.py says: ../../../data/adjudication.db
    # relative to src/database/schema.py
    
    db_path = os.path.join(os.getcwd(), 'data', 'adjudication.db')
    conn = sqlite3.connect(db_path)
    
    cursor = conn.cursor()

    print("=== Verification Report ===")

    # 1. Verify Issue Count and SOP-* IDs
    cursor.execute("SELECT issue_id, issue_name, active FROM issues_master")
    rows = cursor.fetchall()
    print(f"1. Total Issue Records: {len(rows)}")
    
    sop_issues = [r for r in rows if r[0].startswith("SOP-")]
    print(f"2. SOP-* Issue IDs: {len(sop_issues)}")
    
    if len(rows) == 12 and len(sop_issues) == 12:
        print("   [OK] Start with SOP-* and count is 12.")
    else:
        print("   [FAIL] Mismatch in count or ID format.")

    # 3. Check for leftover Legacy IDs
    legacy_issues = [r for r in rows if not r[0].startswith("SOP-")]
    if len(legacy_issues) == 0:
        print("3. No legacy IDs found: [OK]")
    else:
        print(f"   [FAIL] Found remaining legacy IDs: {[r[0] for r in legacy_issues]}")

    # 4. Check Linked Tables for Orphans
    # issues_data (FK: issue_id -> issues_master.issue_id)
    cursor.execute("""
        SELECT count(*) FROM issues_data 
        WHERE issue_id NOT IN (SELECT issue_id FROM issues_master)
    """)
    orphan_data = cursor.fetchone()[0]
    print(f"4. Orphaned 'issues_data' records: {orphan_data}")
    
    # case_issues (Logical Link: issue_id -> issues_master.issue_id)
    # Note: case_issues might have historical data so we just report it, 
    # but strictly speaking if we deleted the master, these might be broken.
    cursor.execute("""
        SELECT issue_id, count(*) FROM case_issues 
        WHERE issue_id NOT IN (SELECT issue_id FROM issues_master)
        GROUP BY issue_id
    """)
    orphan_cases = cursor.fetchall()
    
    if orphan_cases:
        print(f"   [WARNING] 'case_issues' contains references to deleted IDs (Historical Data):")
        for issue_id, count in orphan_cases:
            print(f"      - {issue_id}: {count} records")
    else:
         print("   [OK] No orphaned references in 'case_issues'.")

    conn.close()
    
except Exception as e:
    print(f"Verification Error: {e}")
