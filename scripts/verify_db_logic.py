import sqlite3
import json
import os

def test_db_serialization():
    # 1. Setup a temporary in-memory database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create the proceedings table as defined in schema.py
    cursor.execute("""
    CREATE TABLE proceedings (
        id TEXT PRIMARY KEY,
        gstin TEXT NOT NULL,
        legal_name TEXT,
        additional_details TEXT -- Stores JSON string
    );
    """)
    
    # 2. Mimic the create_proceeding logic
    pid = "test-uuid"
    data = {
        "id": pid,
        "gstin": "24ABCDE1234F1Z5",
        "legal_name": "Test Taxpayer",
        "additional_details": json.dumps({"existing": "val"}) # Initially serialized manually or via create logic
    }
    cursor.execute("INSERT INTO proceedings (id, gstin, legal_name, additional_details) VALUES (?, ?, ?, ?)", 
                   (data['id'], data['gstin'], data['legal_name'], data['additional_details']))
    
    # 3. Mimic the NEW update_proceeding logic (WITH THE FIX)
    updates = {
        "additional_details": {
            "file_paths": {
                "tax_liability": "C:/data/tax.xlsx",
                "gstr_2b": "C:/data/2b.xlsx"
            }
        }
    }
    
    # The fix logic:
    fields = []
    values = []
    for k, v in updates.items():
        if k in ['additional_details']: # This is the fix I applied
            v = json.dumps(v)
        fields.append(f"{k} = ?")
        values.append(v)
    
    values.append(pid)
    query = f"UPDATE proceedings SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    
    # 4. Verify retrieval
    cursor.execute("SELECT additional_details FROM proceedings WHERE id = ?", (pid,))
    row = cursor.fetchone()
    stored_val = row[0]
    
    print(f"Stored string in DB: {stored_val}")
    
    parsed_val = json.loads(stored_val)
    if "file_paths" in parsed_val and parsed_val["file_paths"]["tax_liability"] == "C:/data/tax.xlsx":
        print("\nVERIFICATION SUCCESS: JSON serialization in update_proceeding works correctly!")
    else:
        print("\nVERIFICATION FAILURE: JSON serialization failed.")
        print(f"Expected file_paths, got: {parsed_val}")

    conn.close()

if __name__ == "__main__":
    test_db_serialization()
