
import os
import sys
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.pdf_parsers import _extract_numbers_from_text, _clean_amount, parse_gstr3b_pdf_table_4_b_1, parse_gstr3b_pdf_table_3_1_d

def verify_helper():
    print("\n--- Verifying Helper Function ---")
    
    cases = [
        ("1,12,77,521.00", ["1,12,77,521.00"]),
        ("  1,12, 77,521.00  ", ["1,12, 77,521.00"]),
        ("Taxable: 1,12,77,521.00  IGST: 12,000.00", ["1,12,77,521.00", "12,000.00"]),
        ("No numbers here", []),
        ("Partial: 77,521.00 but with prefix 1,12,", ["1,12,77,521.00"]), # Regex should grab it all if properly formed
    ]
    
    for inp, exp in cases:
        got = _extract_numbers_from_text(inp)
        print(f"Input: '{inp}' -> Found: {got}")
        # Clean comparison
        clean_got = [x.strip() for x in got]
        if clean_got != exp:
             # Spaced variations might match differently string-wise but logically same
             # Let's check cleaned values
             clean_floats_got = [_clean_amount(x) for x in got]
             clean_floats_exp = [_clean_amount(x) for x in exp]
             if clean_floats_got == clean_floats_exp:
                 print("PASS (Numeric Equality)")
             else:
                 print(f"FAIL: Expected {exp}, got {got}")
        else:
            print("PASS (Exact Match)")

def verify_integration_yearly():
    print("\n--- Verifying Integration (Yearly PDF) ---")
    file_path = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    # 3.1(d) Check
    res_d = parse_gstr3b_pdf_table_3_1_d(file_path)
    print(f"3.1(d) Result: {res_d}")
    if res_d and res_d.get('taxable_value') == 360.0:
        print("PASS: 3.1(d) extraction success")
    else:
        print("FAIL: 3.1(d) extraction failure")

    # 4(B)(1) Check
    res_b1 = parse_gstr3b_pdf_table_4_b_1(file_path)
    print(f"4(B)(1) Result: {res_b1}")
    if res_b1 and res_b1.get('cgst') == 6124.91:
        print("PASS: 4(B)(1) extraction success")
    else:
        print("FAIL: 4(B)(1) extraction failure")

if __name__ == "__main__":
    verify_helper()
    verify_integration_yearly()
