import sqlite3
import os

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'

if not os.path.exists(db_path):
    print(f"Error: DB not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Check current value
    c.execute("SELECT grid_data FROM issues_master WHERE issue_id='ITC_3B_2B_OTHER'")
    row = c.fetchone()
    print(f"Current grid_data: {row[0] if row else 'None'}")
    
    # Update to empty dict representation (or null, depending on logic. Parser returns dynamic)
    # asmt10_generator expects grid_data dict or None. If empty list/dict, it might still trigger 'generate_grid_table' but with empty rows.
    # We want it to FALL THROUGH to Priority 2 (summary_table).
    # So we should set it to NULL or empty string?
    # asmt10_generator Line 35: if grid_data and ...
    # So setting it to NULL (None) or empty string "" works.
    
    c.execute("UPDATE issues_master SET grid_data=NULL WHERE issue_id='ITC_3B_2B_OTHER'")
    conn.commit()
    print("Cleared grid_data (Set to NULL)")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
