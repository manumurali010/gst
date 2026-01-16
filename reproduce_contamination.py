
import sys
import os
import json
import logging
import hashlib

# Setup path
sys.path.append(os.getcwd())

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QListWidget
from src.services.scrutiny_parser import ScrutinyParser
from src.ui.issue_card import IssueCard
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer
from src.utils.pdf_parsers import parse_gstr3b_pdf_table_3_1_c, parse_gstr3b_pdf_table_3_1_e

print("Starting Targeted Diagnostics...")

def _safe_hash(d):
     try:
         s = json.dumps(d, sort_keys=True, default=str)
         return hashlib.sha1(s.encode()).hexdigest()
     except: return "HASH_ERR"

def run():
    app = QApplication(sys.argv) # Needed for IssueCard
    
    excel_path = os.path.abspath("repro_sop10.xlsx")
    pdf_path = os.path.abspath("GSTR3B_32AAMFM4610Q1Z0_032023.pdf")
    
    if os.path.exists("repro_sop10_strict.xlsx"):
        excel_path = os.path.abspath("repro_sop10_strict.xlsx")

    parser = ScrutinyParser()
    
    # --- PHASE 2: SOP-11 DIAGNOSTICS ---
    print("\n[PHASE 2] SOP-11 Data Extraction")
    if os.path.exists(pdf_path):
        print(f"Testing PDF: {pdf_path}")
        # Trigger instrumented calls
        print("Calling 3.1(c)...")
        res_c = parse_gstr3b_pdf_table_3_1_c(pdf_path)
        print(f"Result 3.1(c): {res_c}")
        
        print("Calling 3.1(e)...")
        res_e = parse_gstr3b_pdf_table_3_1_e(pdf_path)
        print(f"Result 3.1(e): {res_e}")
    else:
        print("PDF not found, skipping SOP-11 check.")
        
    # --- PHASE 1: SOP-10 UI CONTAMINATION ---
    print("\n[PHASE 1] SOP-10 UI Contamination")
    
    # 1. Simulate SOP-2 (RCM) Execution to potentially pollute shared state
    # We need to successfully parse something for SOP-2.
    # _parse_rcm_liability uses parse_gstr3b_pdf_table_3_1_d
    print("Simulating SOP-2 (RCM) execution...")
    try:
        # Mocking 2A analyzer for SOP-2 if needed, or just let it run
        # It needs 'gstr2a_analyzer' for Phase 2 logic
        # We'll just define a dummy return if possible or try calling it
        # parser._parse_rcm_liability(excel_path, gstr2a_analyzer=mock_2a...)
        pass
    except: pass
    
    # 2. Execute SOP-10 (Import ITC)
    # We need to mock GSTR2AAnalyzer to ensure val_2a > 0
    # And we pass pdf_path to ensure val_3b is parsed (or simulated)
    
    class MockAnalyzer:
        def analyze_sop(self, i):
            if i == 10:
                # Return data that causes Shortfall > 0 (val_2a < val_3b) or vice versa?
                # Shortfall if 3B > 2A?
                # SOP-10: 3B is CLAIM, 2A is AVAILABLE.
                # If 3B > 2A => Excess Claim => Shortfall (Liability)
                # Let's set 2A = 100, 3B (from PDF) = ?
                return {'error': None, 'igst': 100.0}
            return {}
            
    # Check PDF content for 3B Table 4(A)(1)
    # If PDF parsing works, it returns some value. Let's assume it returns > 100.
    # Or we can just inspect the log even if Pass.
    
    print("Executing SOP-10 Parser...")
    # NOTE: _parse_import_itc_phase2 signature: (file_path, gstr2a_analyzer, gstr3b_pdf_paths=None)
    sop10_payload = parser._parse_import_itc_phase2(
        file_path=excel_path, # Dummy use
        gstr2a_analyzer=MockAnalyzer(),
        gstr3b_pdf_paths=[pdf_path] if os.path.exists(pdf_path) else None
    )
    
    # Verify [SOP-10 CREATE] triggered
    print(f"SOP-10 Payload Status: {sop10_payload.get('status')}")
    
    if sop10_payload.get('issue_id') == 'IMPORT_ITC_MISMATCH':
        # [SOP-10 PRE-UI] Manual Check
        print(f"\n[SOP-10 PRE-UI (SIMULATED)] Hash: {_safe_hash(sop10_payload)}")
        
        # 3. Create IssueCard (Simulate UI Expansion)
        print("Creating IssueCard...")
        try:
             # We need to simulate 'init_grid_ui' being called.
             # IssueCard calls init_grid_ui if conditions met.
             # BUT as found, it checks 'grid_data' or 'tables'.
             # SOP-10 payload has 'summary_table'.
             # Does IssueCard use 'summary_table'?
             # Note: If IssueCard code does NOT check 'summary_table', then 'init_grid_ui' is NOT called.
             # We should check if my hypothesis is correct.
             
             # I will forcibly call init_grid_ui to simulate what *should* happen or to trigger the log
             # OR I rely on IssueCard __init__ behavior.
             
             card = IssueCard(sop10_payload)
             
             # If log [SOP-10 EXPAND] appears here, then __init__ called it.
             # If not, it supports "Renderer misrouting" (i.e. it didn't render the correct table, maybe fell back to old data?)
             
             # Force expansion check
             # If card table is missing, maybe that's the issue?
             
        except Exception as e:
             print(f"IssueCard Crash: {e}")
             import traceback
             traceback.print_exc()
             
    else:
        print("SOP-10 Parser returned early/failed.")
        print(sop10_payload)

if __name__ == "__main__":
    run()
