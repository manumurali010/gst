import re

# Exact text from the PDF dump (Step 1918)
# Including potential newlines/spaces
text_block = """
4. Eligible ITC
Details
Integrated Tax(₹) Central Tax(₹)
State/UT Tax(₹) Cess(₹)
A. ITC Available(Whether in Full or Part)
11,90,488.21 1,01,90,419.82
1,01,90,419.82
0.00
(1) Import of goods
0.00
0.00
0.00
0.00
(2) Import of services
0.00
0.00
0.00
0.00
(3) Inward supplies liable to reverse charge (other than 1 & 2 above)
0.00
9.00
9.00
0.00
(4) Inward supplies from ISD
0.00
0.00
0.00
0.00
(5) All other ITC
11,90,488.21
1,01,90,410.82
1,01,90,410.82
0.00
B. ITC Reversed
"""

def test_regex():
    print("Testing Regex Patterns...")
    
    # 1. The Multi-line pattern I just applied
    pattern_multiline = r"All\s*other\s*ITC\s*([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
    match1 = re.search(pattern_multiline, text_block, re.IGNORECASE)
    print(f"Pattern 1 (Multiline): {bool(match1)}")
    if match1:
        print(f"Groups: {match1.groups()}")
        
    # 2. Comparison with the "Inline" pattern (failed originally?)
    pattern_inline = r"\(5\)\s*All\s*other\s*ITC.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
    match2 = re.search(pattern_inline, text_block, re.IGNORECASE | re.DOTALL)
    print(f"Pattern 2 (Inline+DotAll): {bool(match2)}")
    if match2:
        print(f"Groups: {match2.groups()}")

    # 3. Super Loose Pattern (Proposed Backup)
    # Match "All other ITC", then any junk, then 4 numbers separated by newlines
    pattern_loose = r"All\s*other\s*ITC(?:.|\n)*?([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
    match3 = re.search(pattern_loose, text_block, re.IGNORECASE | re.DOTALL)
    print(f"Pattern 3 (Loose): {bool(match3)}")
    if match3:
        print(f"Groups: {match3.groups()}")

if __name__ == "__main__":
    test_regex()
