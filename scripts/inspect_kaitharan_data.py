import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def inspect_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Inspecting Proceedings ---")
    cursor.execute("SELECT id, selected_issues, additional_details FROM proceedings WHERE legal_name LIKE '%KAITHARAN%'")
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"ID: {row['id']}")
        val = row['selected_issues']
        print(f"Type in Python: {type(val)}")
        print(f"Raw Value (first 200 chars): {val[:200] if val else 'None'}")
        
        try:
            parsed = json.loads(val)
            print(f"Parsed Type: {type(parsed)}")
            if isinstance(parsed, list) and len(parsed) > 0:
                print(f"Item 0 Type: {type(parsed[0])}")
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            
    print("\n--- Inspecting Adjudication Cases ---")
    try:
        cursor.execute("SELECT id, selected_issues FROM adjudication_cases WHERE legal_name LIKE '%KAITHARAN%'")
        adj_rows = cursor.fetchall()
        if not adj_rows:
            print("No Adjudication Case found for Kaitharan.")
        for row in adj_rows:
            print(f"Adj ID: {row['id']}")
            val = row['selected_issues']
            print(f"Type in Python: {type(val)}")
            print(f"Raw Value (first 200 chars): {val[:200] if val else 'None'}")
            try:
                parsed = json.loads(val)
                print(f"Parsed Type: {type(parsed)}")
                if isinstance(parsed, list) and len(parsed) > 0:
                    print(f"Item 0 Type: {type(parsed[0])}")
            except Exception as e:
                print(f"JSON Parse Error: {e}")

    except Exception as e:
        print(f"Error checking adjudication table: {e}")

    conn.close()

if __name__ == "__main__":
    inspect_data()
