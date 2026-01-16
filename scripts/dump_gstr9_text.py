import fitz
import json
import sqlite3
import os

import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'data/adjudication.db'

def dump_gstr9_text():
    print("--- Dumping GSTR 9 PDF Text ---")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get File Path from Kaitharan case
    cursor.execute("SELECT additional_details FROM proceedings WHERE legal_name LIKE '%KAITHARAN%'")
    row = cursor.fetchone()
    
    if not row:
        print("Kaitharan case not found.")
        return

    details = json.loads(row['additional_details'])
    if isinstance(details, str): details = json.loads(details)
    
    file_paths = details.get('file_paths', {})
    gstr9_path = file_paths.get('gstr9_yearly')
    
    if not gstr9_path or not os.path.exists(gstr9_path):
        print(f"GSTR 9 PDF not found at: {gstr9_path}")
        return
        
    print(f"Reading: {gstr9_path}")
    
    try:
        doc = fitz.open(gstr9_path)
        full_text = ""
        for i, page in enumerate(doc):
            text = page.get_text()
            print(f"\n--- Page {i+1} ---")
            safe_text = text.encode('utf-8', 'ignore').decode('utf-8')
            print(safe_text[:500] + "..." if len(safe_text) > 500 else safe_text)
            full_text += safe_text
            
        # Specific Table 8 check
        print("\n--- Surrounding Context for 'ITC as per GSTR-2A' ---")
        idx = full_text.find("ITC as per GSTR-2A")
        if idx != -1:
            raw_context = full_text[idx:idx+500]
            print(raw_context.encode('utf-8', 'ignore').decode('utf-8'))
        else:
            print("String 'ITC as per GSTR-2A' NOT FOUND in text.")

    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    dump_gstr9_text()
