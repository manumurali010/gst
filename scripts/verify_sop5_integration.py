
import sys
import os
from unittest.mock import MagicMock

# Adjust path to find src
sys.path.append(os.path.abspath("c:\\Users\\manum\\.gemini\\antigravity\\scratch\\gst"))

from src.services.scrutiny_parser import ScrutinyParser

def run_integration_check():
    # Use the real PDF path found earlier
    pdf_path = "c:\\Users\\manum\\.gemini\\antigravity\\scratch\\gst\\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"CRITICAL: Test PDF not found at {pdf_path}")
        return

    parser = ScrutinyParser()
    
    # Mock analyzer to satisfy dependency
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_sop.return_value = {
        'tds': {'status': 'pass', 'base_value': 120000000.0},
        'tcs': {'status': 'pass', 'base_value': 0.0}
    }
    
    print("\n--- Invoking _parse_tds_tcs_phase2 ---")
    result = parser._parse_tds_tcs_phase2(pdf_path, gstr2a_analyzer=mock_analyzer)
    print("--- Invocation Complete ---\n")
    print(f"Status: {result.get('status')}")
    print(f"Msg: {result.get('status_msg')}")

if __name__ == "__main__":
    run_integration_check()
