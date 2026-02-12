import sqlite3
import json
import os

DB_PATH = r"data\adjudication.db"

def inspect_proceedings():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the most recent proceeding
    try:
        cursor.execute("SELECT id, taxpayer_details FROM proceedings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            print(f"Propceeding ID: {row[0]}")
            tp_details = row[1]
            print(f"Raw Taxpayer Details: {tp_details}")
            
            if tp_details:
                try:
                    tp = json.loads(tp_details)
                    print(f"Parsed Taxpayer Details: {json.dumps(tp, indent=2)}")
                    print(f"Constitution of Business: {tp.get('Constitution of Business', 'NOT FOUND')}")
                except json.JSONDecodeError:
                    print("Failed to parse taxpayer_details JSON")
        else:
            print("No proceedings found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_proceedings()
