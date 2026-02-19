import sqlite3
import os

DB_PATH = 'd:/gst/data/adjudication.db'

def check_sop15():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT issue_id, issue_name, active, sop_point FROM issues_master WHERE issue_id='RCM_ITC_VS_2B'")
        row = c.fetchone()
        if row:
            print(f"FOUND: {row}")
        else:
            print("NOT FOUND: RCM_ITC_VS_2B")
            
        # Also check total count
        c.execute("SELECT COUNT(*) FROM issues_master")
        count = c.fetchone()[0]
        print(f"Total Issues: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_sop15()
