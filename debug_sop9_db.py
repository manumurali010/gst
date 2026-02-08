
import sqlite3
import json
import os

DB_PATH = os.path.join(os.getcwd(), 'gst_scrutiny.db') # Trying root
if not os.path.exists(DB_PATH):
    # Try src/database/
    DB_PATH = os.path.join(os.getcwd(), 'src', 'database', 'gst_scrutiny.db')

print(f"Checking DB at: {DB_PATH}")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT issue_id, issue_name, category, templates, tables, placeholders FROM issues WHERE issue_id LIKE '%16_4%' OR issue_name LIKE '%16(4)%'")
        rows = cursor.fetchall()
        if not rows:
            print("No SOP-9 record found in DB.")
        else:
            for r in rows:
                print(f"ID: {r[0]}")
                print(f"Name: {r[1]}")
                print(f"Category: {r[2]}")
                print(f"Templates: {r[3]}")
                print(f"Tables: {r[4]}")
                print(f"Placeholders: {r[5]}")
    except Exception as e:
        print(f"Error querying DB: {e}")
    finally:
        conn.close()
else:
    print("DB File not found.")
