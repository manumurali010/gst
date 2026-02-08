
import re

def test_regex():
    # Scenario: Number broken by space after comma
    text = "1,12, 77,521.00"
    
    # Current Regex in pdf_parsers.py
    # re.findall(r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})", post_text[:250])
    pattern = r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})"
    
    matches = re.findall(pattern, text)
    print(f"Input: '{text}'")
    print(f"Pattern: {pattern}")
    print(f"Matches: {matches}")
    
    # Proposed Fix: Allow whitespace around commas? 
    # Or pre-process: remove spaces that are between digit and comma?
    
    # Trying improved regex
    # Allow (,\s*\d{3})
    pattern_new = r"((?:\d{1,3}(?:,\s*\d{3})*|\d+)\.\d{2})"
    matches_new = re.findall(pattern_new, text)
    print(f"New Pattern: {pattern_new}")
    print(f"New Matches: {matches_new}")

if __name__ == "__main__":
    test_regex()
