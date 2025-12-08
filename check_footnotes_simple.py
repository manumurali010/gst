import sqlite3

conn = sqlite3.connect('data/adjudication.db')
cursor = conn.cursor()

# Get Section 10 (Composition levy) which should have footnotes
cursor.execute("""
    SELECT content 
    FROM gst_sections 
    WHERE section_number = '10' 
    AND act_id = (SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act, 2017%')
""")

result = cursor.fetchone()

if result:
    content = result[0]
    print("Section 10: Composition levy")
    print("="*80)
    print("\nFull content (last 1000 characters to see footnotes):")
    print(content[-1000:])
    print("\n" + "="*80)
    
    # Check for footnote markers
    footnote_indicators = ['1. Subs.', '2. Subs.', '1. Ins.', '2. Ins.', 
                          'Act', 'ibid', 'w.e.f', 'omitted']
    
    found_footnotes = []
    for indicator in footnote_indicators:
        if indicator in content:
            found_footnotes.append(indicator)
    
    if found_footnotes:
        print(f"\n✅ FOOTNOTES DETECTED! Found markers: {', '.join(found_footnotes)}")
    else:
        print("\n❌ No footnote markers found")

conn.close()
