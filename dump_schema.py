import sqlite3
import os

db_path = os.path.join("data", "adjudication.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('proceedings', 'officers', 'schema_meta');")
schemas = cursor.fetchall()

print("--- DB Schema Dump ---")
for schema in schemas:
    print(schema[0])
    print("")

conn.close()
