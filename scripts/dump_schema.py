import sqlite3
import os

db_path = 'c:/Users/manum/.gemini/antigravity/scratch/gst/data/adjudication.db'

if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for name, sql in cur.fetchall():
        print(f"--- Table: {name} ---")
        print(sql)
    conn.close()
