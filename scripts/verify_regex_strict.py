
import re

def verify_strict_regex():
    # User Mandated Regex
    # ((?:\d{1,3}(?:,\s*\d{2})*,\s*\d{3}|\d+)\.\d{2})
    pattern = r"((?:\d{1,3}(?:,\s*\d{2})*,\s*\d{3}|\d+)\.\d{2})"
    
    test_cases = [
        ("1,12,77,521.00", "1,12,77,521.00"),  # Target Case (Indian Format)
        ("1, 12, 77, 521.00", "1, 12, 77, 521.00"), # Spaced Commas
        ("77,521.00", "77,521.00"),             # Standard
        ("123.45", "123.45"),                   # Small
        ("1,234.56", "1,234.56"),               # Standard thousand
        ("12,34,567.00", "12,34,567.00"),       # Standard Indian
        ("0.00", "0.00"),
    ]

    print(f"Testing Pattern: {pattern}")
    
    all_pass = True
    for input_text, expected in test_cases:
        matches = re.findall(pattern, input_text)
        if not matches:
            print(f"FAIL: '{input_text}' -> No Match")
            all_pass = False
            continue
            
        # Match Selection Logic: Max Length
        selected = max(matches, key=len)
        
        print(f"Input: '{input_text}' -> Matches: {matches} -> Selected: '{selected}'")
        
        # Verify correctness (ignoring spaces for value equality check if needed, but here we expect full capture)
        if selected != expected:
             # Spaced case: matches might contain the spaces, which is fine as long as we clean them later
             if input_text == "1, 12, 77, 521.00" and selected == "1, 12, 77, 521.00":
                 pass
             else:
                print(f"FAIL: Expected '{expected}', got '{selected}'")
                all_pass = False

    if all_pass:
        print("\nSUCCESS: Regex passed all strict test cases.")
    else:
        print("\nFAILURE: Regex failed some test cases.")

if __name__ == "__main__":
    verify_strict_regex()
