import sqlite3
import os

DB_PATH = 'data/adjudication.db'

def verify():
    print("--- Verifying issues_master SOP Points ---")
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check columns
        cursor.execute("PRAGMA table_info(issues_master)")
        cols = [r[1] for r in cursor.fetchall()]
        print(f"Columns: {cols}")
        
        if 'sop_point' not in cols:
            print("CRITICAL: sop_point column MISSING in schema!")
            return

        cursor.execute("SELECT issue_id, sop_point, issue_name FROM issues_master")
        rows = cursor.fetchall()
        print(f"{'Issue ID':<25} | {'SOP':<4} | {'Name'}")
        print("-" * 60)
        for r in rows:
            print(f"{r[0]:<25} | {r[1] or 'NULL':<4} | {r[2]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify()
