
import os
import sys

# Ensure src module is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from src.database.db_manager import DatabaseManager

def cleanup_stale_entries():
    print("--- Starting Cleanup of Stale Register Entries ---")
    db = DatabaseManager()
    db.init_sqlite()
    
    try:
        conn = db._get_conn()
        cursor = conn.cursor()
        
        # 1. Clean OC Register
        print("\nChecking OC Register...")
        cursor.execute("SELECT COUNT(*) FROM oc_register")
        total_oc = cursor.fetchone()[0]
        
        # Delete entries where case_id is not in proceedings
        cursor.execute("""
            DELETE FROM oc_register 
            WHERE case_id NOT IN (SELECT case_id FROM proceedings)
            OR case_id IS NULL
        """)
        deleted_oc = cursor.rowcount
        print(f"Total OC Entries: {total_oc}")
        print(f"Deleted Stale OC Entries: {deleted_oc}")
        
        # 2. Clean ASMT-10 Register
        print("\nChecking ASMT-10 Register...")
        cursor.execute("SELECT COUNT(*) FROM asmt10_register")
        total_asmt = cursor.fetchone()[0]
        
        cursor.execute("""
            DELETE FROM asmt10_register 
            WHERE case_id NOT IN (SELECT case_id FROM proceedings) 
            OR case_id IS NULL
        """)
        deleted_asmt = cursor.rowcount
        print(f"Total ASMT-10 Entries: {total_asmt}")
        print(f"Deleted Stale ASMT-10 Entries: {deleted_asmt}")
        
        conn.commit()
        conn.close()
        print("\n[SUCCESS] Cleanup Complete.")
        
    except Exception as e:
        print(f"\n[ERROR] Cleanup Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_stale_entries()
