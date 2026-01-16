import sys
import os
import pandas as pd

# Mock PyQt6 if not available
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    print("PyQt6 not found. Using Mock.")
    class pyqtSignal:
        def __init__(self, *args): self.slots = []
        def connect(self, func): self.slots.append(func)
        def emit(self, *args): 
            for s in self.slots: s(*args)
            
    class QObject:
        def __init__(self): pass

    import types
    m = types.ModuleType("PyQt6.QtCore")
    m.QObject = QObject
    m.pyqtSignal = pyqtSignal
    sys.modules["PyQt6.QtCore"] = m
    sys.modules["PyQt6"] = types.ModuleType("PyQt6")
    sys.modules["PyQt6"].QtCore = m

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

class TestListener(QObject):
    def __init__(self):
        super().__init__()
        self.ambiguity_events = []

    def handle_ambiguity(self, sop_id, key, options, cache_key):
        print(f"Ambiguity Detected! SOP={sop_id}, Key={key}, Options count={len(options)}")
        for i, opt in enumerate(options):
            # Sanitize for Windows Console
            safe_opt = str(opt).encode('ascii', 'replace').decode()
            print(f"  Opt {i}: {safe_opt}")
        self.ambiguity_events.append({
            "sop_id": sop_id,
            "key": key,
            "options": options,
            "cache_key": cache_key
        })

def run_tests():
    # --- Part 1: Standard & Identical Headers ---
    file1 = os.path.abspath("tests/dummy_gstr2a_std.xlsx")
    with pd.ExcelWriter(file1) as writer:
        # SOP 5 TDS
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["GSTIN", "Taxable Value"], 
            ["of Ded", "(Rs)"], 
            ["A", 1000], ["B", 2000]
        ]).to_excel(writer, sheet_name="TDS", index=False, header=False)
        
        # SOP 3 ISD (Duplicate)
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["GSTIN", "Integrated Tax", "Integrated Tax"],
            ["", "(Input)", "(Distributed)"],
            ["C", 100, 200]
        ]).to_excel(writer, sheet_name="ISD Credit", index=False, header=False)
        
        # SOP 10 (Identical)
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["BOE", "IGST", "IGST"],
            ["", "", ""],
            ["B1", 50, 60]
        ]).to_excel(writer, sheet_name="IMPG", index=False, header=False)

        # SOP 8 Non-Filers (Mixed Status)
        # GSTIN, Filing Status, IGST, IGST (Ambiguous)
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["GSTIN", "GSTR-3B Filing Status", "IGST", "IGST"],
            ["", "", "(Paid)", "(Credit)"],
            ["A", "Y", 100, 200], # Filed - Should be ignored
            ["B", "N", 300, 400]  # Not Filed - Should trigger Ambiguity on IGST
        ]).to_excel(writer, sheet_name="B2B", index=False, header=False)

        # SOP 5 Fallback (TCS Sheet with Ambiguous TDS - Should Fail)
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["GSTIN", "Amount Paid", "Amount Paid"], 
            ["", "(Rs)", "(Duplicate)"], 
            ["X", 500, 600] 
        ]).to_excel(writer, sheet_name="TCS", index=False, header=False)
    
    print(f"\n=== Test Suite 1: {file1} ===")
    analyzer = GSTR2AAnalyzer(file1)
    listener = TestListener()
    analyzer.ambiguity_detected.connect(listener.handle_ambiguity)
    
    # Test SOP 5 (Priority + Fallback Strictness)
    # TDS: 3000 (Taxable Value priority - valid)
    # TCS: Ambiguous 'Amount Paid' -> Should FAIL silently (return None) -> 0 contribution.
    # Total = 3000
    res = analyzer.analyze_sop(5)
    if res.get('taxable_value') == 3000: print("PASS: SOP 5 Correct (Priority Valid / Fallback Ambiguous Ignored)")
    else: print(f"FAIL: SOP 5 {res}")
    
    # Verify NO Ambiguity Event for SOP 5 (Strict Fallback should NOT emit signal)
    sop5_events = [e for e in listener.ambiguity_events if e['sop_id'] == 'sop_5' or e['sop_id'] == 5]
    if not sop5_events:
        print("PASS: SOP 5 Strict Fallback (No Dialog for Ambiguous Fallback)")
    else:
        print(f"FAIL: SOP 5 Triggered Ambiguity Dialog: {sop5_events}")
    
    # Test SOP 8 (Filing Status + Ambiguity)
    # Should resolve Status='N', filter, then hit Ambiguity on 'IGST'
    listener.ambiguity_events = []
    analyzer.cached_selections = {}
    res = analyzer.analyze_sop(8)
    
    # Check if Ambiguity was detected for key='igst' (NOT filing_status)
    amb_keys = [e['key'] for e in listener.ambiguity_events]
    if 'igst' in amb_keys and 'filing_status' not in amb_keys:
        print("PASS: SOP 8 Logic (Status Resolved -> Tax Ambiguity)")
    else:
        print(f"FAIL: SOP 8 Events: {amb_keys}")
        
    if 'error' in res and "Ambiguity detected" in str(res['error']):
         print("PASS: SOP 8 Blocked Correctly")
    else:
         print(f"FAIL: SOP 8 did not block. {res}")

    # Test SOP 3
    listener.ambiguity_events = []
    analyzer.cached_selections = {}
    res = analyzer.analyze_sop(3)
    if 'error' in res and "Ambiguity detected" in str(res['error']):
        print("PASS: SOP 3 Blocking Error")
    else:
        print(f"FAIL: SOP 3 did not block. {res}")
        
    # Resolve SOP 3
    cache_key = 'sop_3:igst'
    analyzer.cached_selections[cache_key] = 'integratedtaxinput'
    res = analyzer.analyze_sop(3)
    if res.get('igst') == 100: print("PASS: SOP 3 Resolved Correctly")
    
    # Test SOP 10 Identical
    listener.ambiguity_events = []
    res = analyzer.analyze_sop(10)
    if 'error' in res and "Ambiguity detected" in str(res['error']):
        print("PASS: SOP 10 Identical Blocking Error")
    else:
        print(f"FAIL: SOP 10 Identical did not block. {res}")
        
    # --- Part 2: Semantic Ambiguity ---
    file2 = os.path.abspath("tests/dummy_gstr2a_sem.xlsx")
    with pd.ExcelWriter(file2) as writer:
        # SOP 10 Semantic
        pd.DataFrame([
            ["Info"], ["Header"], ["Header"], ["Header"],
            ["BOE", "IGST Paid", "Integrated Tax"],
            ["", "", ""],
            ["B2", 70, 80]
        ]).to_excel(writer, sheet_name="Input Tax Credit (Imports)", index=False, header=False)
        
    print(f"\n=== Test Suite 2: {file2} ===")
    analyzer2 = GSTR2AAnalyzer(file2)
    listener2 = TestListener()
    analyzer2.ambiguity_detected.connect(listener2.handle_ambiguity)
    
    res = analyzer2.analyze_sop(10)
    if 'error' in res and "Ambiguity detected" in str(res['error']):
        print("PASS: SOP 10 Semantic Blocking Error")
        if len(listener2.ambiguity_events) > 0:
            opts = listener2.ambiguity_events[0]['options']
            # Check structure
            if not isinstance(opts[0], dict):
                print(f"FAIL: Options are not dicts: {opts}")
            else:
                for opt in opts:
                    cat = opt.get('category')
                    lbl = opt.get('label')
                    val = opt.get('value')
                    
                    if 'paid' in val or 'tax' in val:
                        if cat == 'recommended':
                            print(f"PASS: '{val}' categorized as Recommended")
                        else:
                            print(f"FAIL: '{val}' should be Recommended, got {cat}")
                    
                    if 'gstin' in val: # If we had metadata cols in test
                        if cat == 'other':
                             print(f"PASS: Metadata '{val}' categorized as Other")
                        else:
                             print(f"FAIL: Metadata '{val}' check failed")
                
                # Check Labels
                labels = [o['label'] for o in opts]
                if any("✅ Tax Amount" in l for l in labels):
                     print("PASS: Defensive Labels detected (Recommended)")
                else:
                     print(f"FAIL: Labels missing '✅ Tax Amount': {labels}")
                     
                if any("❌" in l for l in labels):
                     print("PASS: Defensive Labels detected (Others)")
                else:
                     # This might fail if test case only has recommended cols, but sem file has mixed
                     pass
    else:
        print(f"FAIL: SOP 10 Semantic did not block. {res}")

    # --- Part 3: Atomic Failure (Missing CGST) ---
    file3 = os.path.abspath("tests/dummy_gstr2a_atomic.xlsx")
    with pd.ExcelWriter(file3) as writer:
        # SOP 3 sheet with IGST and SGST but NO CGST
        pd.DataFrame([
            ["GSTIN", "Integrated Tax", "State Tax"],
            ["C", 100, 200]
        ]).to_excel(writer, sheet_name="ISD Credit", index=False, header=True)
        
    print(f"\n=== Test Suite 3: {file3} (Atomic Check) ===")
    analyzer3 = GSTR2AAnalyzer(file3)
    res = analyzer3.analyze_sop(3)
    if 'error' in res and "Atomic Failure" in res['error']:
        print("PASS: SOP 3 Atomic Failure Detected (Missing CGST)")
    else:
        print(f"FAIL: SOP 3 did not detect atomic failure. {res}")

if __name__ == "__main__":
    run_tests()
