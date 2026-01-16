import sqlite3
import os
import json

db_path = r'c:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Tables ---")
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(c.fetchall())

print("\n--- Columns in 'case_issues' table ---")
try:
    c.execute("PRAGMA table_info(case_issues)")
    columns = c.fetchall()
    for col in columns:
        print(col)
        
    print("\n--- Content of 'case_issues' ---")
    c.execute("SELECT * FROM case_issues LIMIT 1")
    print(c.fetchone())

    print("\n--- Checking for SOP-4 in case_issues ---")
    # Assuming 'issue_id' column exists
    # c.execute("SELECT id, case_id, issue_id, grid_data_json FROM case_issues WHERE issue_id='ITC_3B_2B_OTHER'")
    # We first need to see the columns to know the names. 
    # But Python script will print them above.
    # To run a specific query blindly might fail.
    # Let's just print columns first, then decided in next step.
    pass

except Exception as e:
    print(f"Error inspecting case_issues: {e}")

print("\n--- Columns in 'adjudication_cases' table ---")
try:
    c.execute("PRAGMA table_info(adjudication_cases)")
    print(c.fetchall())
except: pass

conn.close()
