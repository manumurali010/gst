import sqlite3

conn = sqlite3.connect('data/adjudication.db')
cursor = conn.cursor()

# Get CGST Act 2017
cursor.execute("SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%'")
act = cursor.fetchone()

if act:
    act_id = act[0]
    
    # Get unique chapters
    cursor.execute("""
        SELECT DISTINCT chapter_id, chapter_name 
        FROM gst_sections 
        WHERE act_id = ? AND chapter_id IS NOT NULL
        ORDER BY chapter_id
    """, (act_id,))
    
    chapters = cursor.fetchall()
    
    print(f"Total Chapters: {len(chapters)}\n")
    print("="*80)
    
    for chapter_id, chapter_name in chapters:
        # Count sections in this chapter
        cursor.execute("""
            SELECT COUNT(*) 
            FROM gst_sections 
            WHERE act_id = ? AND chapter_id = ?
        """, (act_id, chapter_id))
        
        section_count = cursor.fetchone()[0]
        
        print(f"{chapter_id}: {chapter_name}")
        print(f"  Sections: {section_count}")
        print("-"*80)

conn.close()
