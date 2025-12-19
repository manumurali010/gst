import sqlite3
import re

DB_PATH = 'data/adjudication.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get CGST Act ID
    cursor.execute("SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%' LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("CGST Act not found!")
        return
    
    act_id = row['act_id']
    print(f"Found Act ID: {act_id}")
    
    # 2. Get all sections for this Act
    cursor.execute("SELECT id, title, content FROM gst_sections WHERE act_id = ?", (act_id,))
    sections = cursor.fetchall()
    
    updated_count = 0
    
    for section in sections:
        sid = section['id']
        title = section['title']
        content = section['content']
        
        # Regex to find section number
        # Look for "digits. " at start of line
        # Content often starts with header, so we look for it after newlines or at start
        match = re.search(r'(?:^|\n)(\d+)\.\s', content)
        
        if match:
            num = match.group(1)
            # print(f"Found Sec {num} for '{title}'")
            
            cursor.execute("UPDATE gst_sections SET section_number = ? WHERE id = ?", (num, sid))
            updated_count += 1
        else:
            print(f"Could not extract number for: '{title}' (ID: {sid})")
            # print(f"Content start: {content[:100]!r}")

    conn.commit()
    conn.close()
    print(f"Migration complete. Updated {updated_count} sections.")

if __name__ == "__main__":
    migrate()
