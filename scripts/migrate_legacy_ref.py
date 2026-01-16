import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def migrate_specific_reference():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    legacy_id = "SOP-1925D69B"
    canonical_id = "LIABILITY_3B_R1"
    
    print(f"Migrating references from {legacy_id} to {canonical_id}...")
    
    try:
        # Check if legacy exists
        cursor.execute("SELECT count(*) FROM case_issues WHERE issue_id = ?", (legacy_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute("UPDATE case_issues SET issue_id = ? WHERE issue_id = ?", (canonical_id, legacy_id))
            conn.commit()
            print(f"Successfully migrated {count} references.")
        else:
            print("No references found to migrate.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_specific_reference()
