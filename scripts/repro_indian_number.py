
import re

def test_indian_regex():
    text = "1,12,77,521.00"
    
    # Current Regex (International 3-digit grouping only)
    # ((?:\d{1,3}(?:,\s*\d{3})*|\d+)\.\d{2})
    pattern_current = r"((?:\d{1,3}(?:,\s*\d{3})*|\d+)\.\d{2})"
    
    matches_current = re.findall(pattern_current, text)
    print(f"Input: '{text}'")
    print(f"Current Pattern: {pattern_current}")
    print(f"Matches: {matches_current}")
    
    if "1,12,77,521.00" in matches_current:
        print("FAIL: Current regex SHOULD have failed but didn't.")
    else:
        print("PASS: Current regex failed as expected on Indian format.")
        
    # Proposed Fix (2 or 3 digit grouping)
    # ((?:\d{1,3}(?:,\s*\d{2,3})*|\d+)\.\d{2})
    pattern_new = r"((?:\d{1,3}(?:,\s*\d{2,3})*|\d+)\.\d{2})"
    
    matches_new = re.findall(pattern_new, text)
    print(f"New Pattern: {pattern_new}")
    print(f"Matches: {matches_new}")
    
    if "1,12,77,521.00" in matches_new[0]:
        print("PASS: New regex captured full Indian format number.")
    else:
        print("FAIL: New regex still failed.")

if __name__ == "__main__":
    test_indian_regex()
