import sqlite3
import os

db_path = 'data/adjudication.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n--- Listing First 5 Sections Content of CGST Act ---")
# Find CGST Act ID first
cursor.execute("SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%' LIMIT 1")
row = cursor.fetchone()
if row:
    act_id = row['act_id']
    cursor.execute("SELECT id, title, content FROM gst_sections WHERE act_id = ? ORDER BY id LIMIT 5", (act_id,))
    for row in cursor.fetchall():
        print(f"ID: {row['id']}, Title: '{row['title']}'")
        print(f"Content Start: {row['content'][:50]}...")
        print("-" * 20)

conn.close()
