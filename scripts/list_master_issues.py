import sqlite3
import os

db_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT issue_id, issue_name FROM issues_master")
    rows = cursor.fetchall()
    print("Issue ID | Issue Name")
    print("-" * 50)
    for row in rows:
        print(f"{row[0]} | {row[1]}")
    conn.close()
