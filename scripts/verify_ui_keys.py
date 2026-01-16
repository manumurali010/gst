import sys
import os
sys.path.append(os.getcwd())

sys.stdout.reconfigure(encoding='utf-8')

from src.services.scrutiny_parser import ScrutinyParser

# Hardcoded keys from ComplianceDashboard (src/ui/scrutiny_tab.py)
UI_KEYS = [
    (1, "Outward Liability (GSTR 3B vs GSTR 1)"),
    (2, "RCM (GSTR 3B vs GSTR 2B)"),
    (3, "ISD Credit (GSTR 3B vs GSTR 2B)"),
    (4, "All Other ITC (GSTR 3B vs GSTR 2B)"),
    (5, "TDS/TCS (GSTR 3B vs GSTR 2B)"),
    (6, "E-Waybill Comparison (GSTR 3B vs E-Waybill)"),
    (7, "ITC passed on by Cancelled TPs"),
    (8, "ITC passed on by Suppliers who have not filed GSTR 3B"),
    (9, "Ineligible Availment of ITC [Violation of Section 16(4)]"),
    (10, "Import of Goods (3B vs ICEGATE)"),
    (11, "Rule 42 & 43 ITC Reversals"),
    (12, "GSTR 3B vs 2B (discrepancy identified from GSTR 9)")
]

def verify_keys():
    print("--- Verifying Scrutiny Keys ---")
    parser = ScrutinyParser()
    
    # Mock os.path.exists to allow dummy file
    original_exists = os.path.exists
    os.path.exists = lambda x: True
    
    # Generate dummy issues
    results = parser.parse_file("dummy.xlsx", extra_files={'gstr9_yearly': 'dummy.pdf'})
    
    # Restore
    os.path.exists = original_exists
    
    parser_map = {}
    if "error" in results:
        print("Parser Error:", results)
        return

    # Extract categories from parser output
    for item in results.get('scrutiny_issues', []): # parser returns list directly or dict?
         pass 

    # Look at how parser.parse_file returns. It returns a dict `{"issues": ...}` or list? 
    # Actually checking recent changes, it returns `{"metadata":..., "issues": [...]}` or just list if resume_case handles it?
    # Let's check the code. The `parse_file` method returns a Dict with `issues` key usually. 
    # Wait, in the recent View it was returning a Dict or List depending on implementation.
    # Let's just create a dummy "parse" by instantiating the objects directly or using the methods.
    
    print("\nComparison:\n")
    print(f"{'UI Expected Key':<60} | {'Parser Output Key':<60} | {'Match?'}")
    print("-" * 130)
    
    # We will manually invoke the private methods or just check the source code strings? 
    # Better to instantiate and run to see runtime values.
    # Since we can't easily run full parse without files, let's just use the STRINGS we know we put in the parser code 
    # vs the STRINGS we extracted from UI code.
    
    # I will just grep/read them effectively. 
    # Actually, running the parser with None usually returns the "Data not available" objects with the categories. 
    # Let's try that.
    
    issues_list = parser.parse_file(None)["issues"] if isinstance(parser.parse_file(None), dict) else parser.parse_file(None)
    
    # Map by approximate name or just list 
    for i, (num, ui_key) in enumerate(UI_KEYS):
        # Find matching parser issue by some heuristic or index (they are ordered usually)
        # 12 points. UI_KEYS has 12. Parser logic has 12 blocks.
        if i < len(issues_list):
            p_issue = issues_list[i]
            p_key = p_issue.get('category', 'UNKNOWN')
            
            match = (ui_key == p_key)
            match_mark = "✅" if match else "❌"
            
            print(f"{ui_key:<60} | {p_key:<60} | {match_mark}")
            
            if not match:
                print(f"   >>> LEN: UI({len(ui_key)}) vs Parser({len(p_key)})")
                print(f"   >>> UI Bytes: {[ord(c) for c in ui_key]}")
                print(f"   >>> P  Bytes: {[ord(c) for c in p_key]}")

if __name__ == "__main__":
    verify_keys()
