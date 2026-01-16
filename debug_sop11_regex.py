
import fitz
import re
import os
import glob

def debug_sop11(file_path):
    print(f"--- Diagnosing {file_path} ---")
    if not os.path.exists(file_path):
        print("File not found.")
        return

    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
    
    print(f"Total Text Length: {len(full_text)}")
    
    # Regex Patterns
    patterns = {
        "3.1(c)": r"\(c\)\s*Other\s*outward\s*supplies\s*\(Nil\s*rated,\s*exempted\)",
        "3.1(e)": r"\(e\)\s*Non-GST\s*outward\s*supplies"
    }
    
    for label, regex in patterns.items():
        print(f"\nTesting {label} with regex: {regex}")
        match = re.search(regex, full_text, re.IGNORECASE)
        if match:
            print(f"  [MATCH FOUND] at index {match.start()}")
            print(f"  Matched Text: '{match.group(0)}'")
            
            # Simulate _parse_3_1_row logic
            post_text = full_text[match.end():]
            snippet = post_text[:250]
            print(f"  Post-Match Snippet (250 chars):\n  '{snippet}'")
            
            # Check number extraction
            # Code uses: re.findall(r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})", post_text[:250])
            nums = re.findall(r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})", snippet)
            print(f"  Extracted Numbers (Strict .dd format): {nums}")
            
            # Alternative Check (Flexible)
            nums_flex = re.findall(r"[\d,]+\.?\d*", snippet)
            print(f"  Raw Number Token Check: {nums_flex[:10]}")
            
        else:
            print("  [NO MATCH FOUND]")
            # Dump nearby text if possible?
            # Search for literal substrings to see if regex is slightly off
            if "Non-GST" in full_text:
                idx = full_text.find("Non-GST")
                print(f"  'Non-GST' found literally at {idx}. Context: '{full_text[idx-20:idx+50]}'")

if __name__ == "__main__":
    # Find PDF
    pdfs = glob.glob("*.pdf")
    target = None
    for p in pdfs:
        if "GSTR3B" in p and "042022" in p:
             target = p
             break
    
    if target:
        debug_sop11(target)
    else:
        print("Target PDF not found in current dir.")
