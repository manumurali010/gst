import sqlite3
import os

DB_PATH = os.path.join("data", "adjudication.db")

def patch_db():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Applying Patches...")
        
        # 1. Fix SOP-8 (NON_FILER_SUPPLIERS) -> sop_point = 8
        cursor.execute("UPDATE issues_master SET sop_point = 8 WHERE issue_id = 'NON_FILER_SUPPLIERS'")
        if cursor.rowcount > 0:
            print("Fixed SOP-8 (NON_FILER_SUPPLIERS) sop_point = 8")
        else:
            print("SOP-8 Not Found or No Change")

        # 2. Fix SOP-1 (LIABILITY_3B_R1) -> sop_point = 1
        cursor.execute("UPDATE issues_master SET sop_point = 1 WHERE issue_id = 'LIABILITY_3B_R1'")
        if cursor.rowcount > 0:
            print("Fixed SOP-1 (LIABILITY_3B_R1) sop_point = 1")
        else:
            print("SOP-1 Not Found or No Change")
            
        conn.commit()
        
        # Verification
        print("\nVerifying...")
        cursor.execute("SELECT issue_id, sop_point FROM issues_master WHERE issue_id IN ('NON_FILER_SUPPLIERS', 'LIABILITY_3B_R1')")
        for r in cursor.fetchall():
            print(r)

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    patch_db()
