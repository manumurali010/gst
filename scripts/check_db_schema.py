import sqlite3
import sys

# Connect to database
conn = sqlite3.connect('data/adjudication.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== Database Tables ===")
for table in tables:
    print(f"\n{table[0]}")
    
    # Get schema for each table
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"  Total rows: {count}")

# Check specifically for GST Acts and Sections
print("\n\n=== GST Acts Data ===")
cursor.execute("SELECT * FROM gst_acts LIMIT 3")
acts = cursor.fetchall()
for act in acts:
    print(act)

print("\n\n=== GST Sections Sample ===")
cursor.execute("SELECT act_id, section_number, title FROM gst_sections LIMIT 5")
sections = cursor.fetchall()
for section in sections:
    print(section)

conn.close()
