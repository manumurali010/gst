import sqlite3
import os

DB_PATH = os.path.join("data", "adjudication.db")

def fix_legacy_issue():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        print(f"--- Fixing {DB_PATH} ---")

        # Deactivate and set description
        c.execute("""
            UPDATE issues_master 
            SET description = 'Legacy generic issue for backward compatibility.', active = 0 
            WHERE issue_id = 'LEGACY_GENERIC'
        """)
        
        if c.rowcount > 0:
            print(f"[SUCCESS] Updated {c.rowcount} row(s) for LEGACY_GENERIC.")
        else:
            print("[WARNING] LEGACY_GENERIC not found or no changes made.")

        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Fix failed: {e}")

if __name__ == "__main__":
    fix_legacy_issue()
