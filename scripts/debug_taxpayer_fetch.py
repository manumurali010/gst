import pandas as pd
import sqlite3

# Mock Database Manager Logic
class MockDB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_taxpayer(self, gstin):
        if not gstin: return None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM taxpayers WHERE gstin = ?", (gstin,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"DB Error: {e}")
            return None

# Setup
DB_PATH = "gst_adjudication.db"

# List Tables
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:", [t[0] for t in tables])
    conn.close()
except Exception as e:
    print(f"Schema Check Error: {e}")

db = MockDB(DB_PATH)

# File Name Parsing Logic (from ScrutinyParser/Tab)
def extract_gstin_from_filename(filename):
    # e.g., "2022-23_32AFWPD9794D1Z0_Tax liability..."
    parts = filename.split("_")
    for p in parts:
        if len(p) == 15 and p.isalnum():
            return p
    return None

filename = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison (1).xlsx"
gstin = extract_gstin_from_filename(filename)

print(f"Extracted GSTIN: '{gstin}'")

if gstin:
    taxpayer = db.get_taxpayer(gstin)
    print(f"Taxpayer Result: {taxpayer}")
    if taxpayer:
        print(f"Legal Name: {taxpayer.get('legal_name')}")
else:
    print("Could not extract GSTIN from filename.")
