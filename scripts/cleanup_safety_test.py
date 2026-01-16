import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def cleanup_dummy_reference():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Cleaning up dummy reference...")
    try:
        cursor.execute("DELETE FROM case_issues WHERE proceeding_id = 'DUMMY_PROC_ID'")
        conn.commit()
        print("Cleanup successful.")
    except Exception as e:
        print(f"Cleanup failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_dummy_reference()
