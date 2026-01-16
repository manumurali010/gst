
import sys
import os
import pandas as pd
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.gstr_2a_analyzer import GSTR2AAnalyzer, AmbiguityError

def create_dummy_data():
    file_path = "tests/dummy_semantic_sop.xlsx"
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # SOP-3: ISD
        # Headers: Integrated Tax, Central Tax, State Tax
        # Data: Blanks for 0.0
        df_isd = pd.DataFrame([
            ["GSTIN", "Invoice Number", "Invoice Date", "Integrated Tax", "Central Tax", "State Tax"],
            ["27AAAAA0000A1Z5", "INV001", "01-01-2023", 1000, 500, 500],
            ["27AAAAA0000A1Z5", "INV002", "02-01-2023", None, None, None], # Blank row
            ["27AAAAA0000A1Z5", "INV003", "03-01-2023", 2000, 1000, 1000]
        ])
        df_isd.to_excel(writer, sheet_name='ISD', index=False, header=False)
        
        # SOP-5: TDS
        # Headers: Taxable Value, Tax Deducted
        df_tds = pd.DataFrame([
            ["GSTIN", "Taxable Value", "Tax Deducted"],
            ["27AAAAA0000A1Z5", 50000, 1000]
        ])
        df_tds.to_excel(writer, sheet_name='TDS', index=False, header=False)
        
        # SOP-5: TCS
        # Headers: Net Amount Liable, Tax Collected (Ambiguity Context)
        # We simulate ambiguity by having multiple "Value" like columns
        df_tcs = pd.DataFrame([
            ["GSTIN", "Net Amount Liable", "Some Other Value", "Tax Collected"],
            ["27AAAAA0000A1Z5", 100000, 500, 1000]
        ])
        df_tcs.to_excel(writer, sheet_name='TCS', index=False, header=False)
        
        # SOP-10: IMPG
        # Headers: Integrated Tax Amount (Non-Standard)
        df_impg = pd.DataFrame([
            ["BE Number", "BE Date", "Integrated Tax Amount"],
            ["BE001", "01-01-2023", 5000]
        ])
        df_impg.to_excel(writer, sheet_name='IMPG', index=False, header=False)
        
    return file_path

class TestListener(QObject):
    def handle_ambiguity(self, sop_id, key, options, cache_key):
        print(f"SIGNAL RECEIVED: Ambiguity in {sop_id} for {key}")
        print("Options:")
        for opt in options:
            print(f"  - {opt['label']} (Cat: {opt['category']})")
        
        # Auto-resolve logic for test
        recommended = [o for o in options if o['category'] == 'recommended']
        if recommended:
            print(f"Auto-selecting recommended: {recommended[0]['value']}")
            # Update cache on the analyzer instance (hacky for test)
            # In real app, we update analyzer.cached_selections
            pass

def test_semantic_logic():
    app = QApplication(sys.argv)
    file_path = create_dummy_data()
    print(f"Created dummy file: {file_path}")
    
    analyzer = GSTR2AAnalyzer(file_path)
    listener = TestListener()
    analyzer.ambiguity_detected.connect(listener.handle_ambiguity)
    
    print("\n--- Testing SOP-3 (ISD) ---")
    try:
        res = analyzer.analyze_sop('sop_3')
        print("Result:", res)
        # Expect: IGST=3000 (1000+2000), CGST=1500, SGST=1500. Blank row treated as 0.
        if res['igst'] == 3000.0 and res['cgst'] == 1500.0:
            print("PASS: SOP-3 Semantic Mapping & Blank Handling")
        else:
            print("FAIL: SOP-3 Results mismatch")
    except Exception as e:
        print(f"FAIL: SOP-3 Exception: {e}")

    print("\n--- Testing SOP-10 (IMPG) ---")
    try:
        res = analyzer.analyze_sop('sop_10')
        print("Result:", res)
        # Expect: IGST=5000
        if res['igst'] == 5000.0:
            print("PASS: SOP-10 Semantic Mapping (Integrated Tax Amount -> IGST)")
        else:
            print("FAIL: SOP-10 Results mismatch")
    except Exception as e:
        print(f"FAIL: SOP-10 Exception: {e}")

    print("\n--- Testing SOP-5 (TDS/TCS) ---")
    # Case 1: TDS (Should pass automatically as 'Taxable Value' matches recommended)
    # Case 2: TCS (Net Amount Liable matches recommended)
    try:
        res = analyzer.analyze_sop('sop_5')
        print("Result:", res)
        # Expect TDS=50000, TCS=100000
        tds_ok = res['tds']['status'] == 'pass' and res['tds']['base_value'] == 50000.0
        tcs_ok = res['tcs']['status'] == 'pass' and res['tcs']['base_value'] == 100000.0
        
        if tds_ok and tcs_ok:
             print("PASS: SOP-5 TDS & TCS Semantic Mapping")
        else:
             print(f"FAIL: SOP-5 Results mismatch. TDS_OK={tds_ok}, TCS_OK={tcs_ok}")
    except Exception as e:
        print(f"FAIL: SOP-5 Exception: {e}")
        
    # Clean up
    try:
        # os.remove(file_path)
        pass
    except:
        pass

if __name__ == "__main__":
    test_semantic_logic()
