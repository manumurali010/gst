import sqlite3
import re

conn = sqlite3.connect('data/adjudication.db')
cursor = conn.cursor()

# Get CGST Act 2017
cursor.execute("SELECT act_id, title FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%'")
act = cursor.fetchone()

if act:
    act_id, act_title = act
    print(f"Act: {act_title}")
    print(f"Act ID: {act_id}")
    print("="*80)
    
    # Get all sections for this act
    cursor.execute("""
        SELECT section_number, title, chapter_id, substr(content, 1, 300) 
        FROM gst_sections 
        WHERE act_id = ? 
        ORDER BY id 
        LIMIT 30
    """, (act_id,))
    
    sections = cursor.fetchall()
    
    print(f"\nTotal sections found: {len(sections)}")
    print("\nFirst 30 sections:\n")
    
    for sec_num, title, chapter_id, content in sections:
        print(f"Section {sec_num or 'N/A'}: {title[:60]}")
        print(f"  Chapter ID: {chapter_id or 'None'}")
        
        # Try to extract chapter from content
        chapter_match = re.search(r'Chapter\s+([IVXLCDM]+)\s*\n\s*([^\n]+)', content)
        if chapter_match:
            print(f"  Chapter in content: Chapter {chapter_match.group(1)} - {chapter_match.group(2)}")
        
        print(f"  Content preview: {content[:150].replace(chr(10), ' ')[:100]}...")
        print("-"*80)

conn.close()
