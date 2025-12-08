import sqlite3

conn = sqlite3.connect('data/adjudication.db')
cursor = conn.cursor()

# Get CGST Act 2017
cursor.execute("SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%'")
act = cursor.fetchone()

if act:
    act_id = act[0]
    
    # Get a few sections to check for footnotes
    cursor.execute("""
        SELECT section_number, title, content 
        FROM gst_sections 
        WHERE act_id = ? AND section_number IN ('10', '16', '17')
        ORDER BY id
    """, (act_id,))
    
    sections = cursor.fetchall()
    
    print("Checking for footnotes in CGST Act sections:\n")
    print("="*80)
    
    for sec_num, title, content in sections:
        print(f"\nSection {sec_num}: {title}")
        print("-"*80)
        
        # Check if content contains footnote markers
        if any(marker in content for marker in ['1.', '2.', '3.', '4.', '5.']) and \
           any(keyword in content.lower() for keyword in ['subs.', 'ins.', 'omitted', 'act', 'ibid']):
            print("✅ FOOTNOTES FOUND!")
            
            # Extract and show footnotes
            lines = content.split('\n')
            in_footnote = False
            footnotes = []
            
            for line in lines:
                # Look for footnote patterns
                if any(pattern in line for pattern in ['1. Subs.', '2. Subs.', '1. Ins.', '2. Ins.', 
                                                        '3. Subs.', '4. Subs.', '5. Subs.',
                                                        '1. The word', '2. The word']):
                    in_footnote = True
                    footnotes.append(line)
                elif in_footnote and (line.strip().startswith(tuple('123456789')) or 
                                     'Act' in line or 'ibid' in line or 'w.e.f' in line):
                    footnotes.append(line)
                elif in_footnote and line.strip() == '':
                    in_footnote = False
            
            if footnotes:
                print("\nFootnote content:")
                for fn in footnotes[:10]:  # Show first 10 lines
                    print(f"  {fn}")
                if len(footnotes) > 10:
                    print(f"  ... and {len(footnotes) - 10} more lines")
        else:
            print("❌ No footnotes detected")
        
        print()

conn.close()
