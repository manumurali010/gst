import sqlite3
import os

DB_PATH = os.path.join("data", "adjudication.db")

def inspect_db():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"--- Inspecting {DB_PATH} ---")

    # Check LEGACY_GENERIC
    c.execute("SELECT * FROM issues_master WHERE issue_id = 'LEGACY_GENERIC'")
    legacy = c.fetchone()
    if legacy:
        print("\n[LEGACY_GENERIC Found]")
        print(f"  Active: {legacy['active']}")
        print(f"  Description: '{legacy['description']}'")
        print(f"  SOP Point: {legacy['sop_point']}")
    else:
        print("\n[LEGACY_GENERIC Not Found]")

    # Check for ANY active issue with empty description
    c.execute("SELECT issue_id, issue_name FROM issues_master WHERE active=1 AND (description IS NULL OR description = '')")
    bad_rows = c.fetchall()
    if bad_rows:
        print("\n[CRITICAL] Active issues with missing descriptions:")
        for row in bad_rows:
            print(f"  - {row['issue_id']}: {row['issue_name']}")
    else:
        print("\n[OK] No active issues with missing descriptions.")

    conn.close()

if __name__ == "__main__":
    inspect_db()
