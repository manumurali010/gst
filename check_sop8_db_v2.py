import sqlite3
import os

# Updated path based on list_dir result
DB_PATH = "gst_adjudication.db" 

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    print(f"Checking DB at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT issue_id, issue_name, sop_point FROM issues_master WHERE issue_id = 'NON_FILER_SUPPLIERS'")
        row = cursor.fetchone()
        if row:
            print(f"Found: {row}")
        else:
            print("Issue 'NON_FILER_SUPPLIERS' NOT FOUND in issues_master.")
            
        # Also list all issues to be sure
        print("\nAll Issues:")
        cursor.execute("SELECT issue_id, sop_point FROM issues_master")
        for r in cursor.fetchall():
            print(r)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
