import sys
import os
import json
import sqlite3
import re
import hashlib

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.schema import init_db, DB_FILE

def migrate():
    print("Initializing DB...")
    init_db()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT count(*) FROM gst_acts")
    if cursor.fetchone()[0] > 0:
        print("Existing data found. Clearing tables...")
        cursor.execute("DELETE FROM gst_sections")
        cursor.execute("DELETE FROM gst_acts")
        conn.commit()

    print("Migrating data from JSON...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "data", "gst_acts_checkpointed.json")
    
    if not os.path.exists(json_path):
        print(f"JSON file not found at {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for act in data.get('acts', []):
        title = act.get('title', 'Unknown Act')
        # Generate unique act_id using hash to avoid collisions
        act_id = hashlib.md5(title.encode()).hexdigest()[:16]
        
        print(f"Migrating Act: {title}")
        cursor.execute("INSERT INTO gst_acts (act_id, title, year) VALUES (?, ?, ?)", 
                       (act_id, title, 2017))
        
        # Track current chapter as we iterate through sections
        current_chapter_id = None
        current_chapter_name = None
        section_count = 0
        chapter_count = 0
        
        for section in act.get('sections', []):
            sec_title = section.get('section_title', '')
            content = section.get('content', '')
            
            # Extract chapter information from content
            # Pattern: "Chapter II\nAdministration" or "Chapter V\nInput Tax Credit"
            chapter_match = re.search(r'Chapter\s+([IVXLCDM]+)\s*\n\s*([^\n]+)', content)
            if chapter_match:
                current_chapter_id = f"CHAPTER_{chapter_match.group(1)}"
                current_chapter_name = chapter_match.group(2).strip()
                chapter_count += 1
                print(f"  Found Chapter: {current_chapter_id} - {current_chapter_name}")
            
            # Extract section number from content
            # Pattern: "1. Short title..." or "16. Eligibility..."
            match = re.match(r'^(\d+[A-Z]*)\.\s', content.strip())
            sec_num = match.group(1) if match else ""
            
            cursor.execute("""
                INSERT INTO gst_sections (act_id, section_number, title, content, chapter_id, chapter_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (act_id, sec_num, sec_title, content, current_chapter_id, current_chapter_name))
            
            section_count += 1
        
        print(f"  Migrated {section_count} sections across {chapter_count} chapters")

    conn.commit()
    conn.close()
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()
