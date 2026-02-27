import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'adjudication.db')

def list_ids():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT issue_id FROM issues_master LIMIT 5")
    rows = c.fetchall()
    for row in rows:
        print(row[0])
    conn.close()

if __name__ == "__main__":
    list_ids()
