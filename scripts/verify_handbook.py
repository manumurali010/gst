import json
import re
import os

def load_and_parse_sections():
    file_path = r"C:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System\gst_acts_checkpointed.json"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find the Principal Act
    principal_act = None
    for act in data.get('acts', []):
        if "Central Goods and Services Tax Act, 2017" in act.get('title', ''):
            principal_act = act
            break
    
    if not principal_act:
        print("Principal Act not found!")
        return

    print(f"Found Act: {principal_act['title']}")
    
    for section in principal_act.get('sections', [])[:20]: # Check first 20
        title = section.get('section_title', 'Unknown')
        content = section.get('content', '')
        
        # Try to extract section number from content
        # Pattern: Look for start of line, digits, optional letters, dot, space
        # But content often has preamble.
        # Let's look at the first few lines of content.
        
        lines = content.split('\n')
        section_no = None
        
        for line in lines:
            line = line.strip()
            # Match "1. Title" or "43A. Title"
            match = re.match(r'^(\d+[A-Z]*)\.\s', line)
            if match:
                section_no = match.group(1)
                break
        
        if section_no:
            print(f"Parsed: Section {section_no} - {title}")
        else:
            print(f"FAILED to parse: {title}")
            # print(f"Content snippet: {content[:100]}...")

if __name__ == "__main__":
    load_and_parse_sections()
