
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.getcwd())

from src.services.scrutiny_parser import ScrutinyParser

def test_sop2_logic():
    print(">>> Starting SOP-2 Logic Verification")
    
    parser = ScrutinyParser()
    
    # Mock the PDF parsers to return controlled values
    # Scenario 1: Excess ITC (Violation)
    # RCM = 100, ITC = 120 -> Diff = 20, Liability SHOULD BE 20
    mock_rcm_1 = {"cgst": 100.0, "sgst": 100.0, "igst": 100.0, "cess": 0.0}
    mock_itc_1 = {"cgst": 120.0, "sgst": 120.0, "igst": 120.0, "cess": 0.0}
    
    # Scenario 2: Equal (Pass)
    mock_rcm_2 = {"cgst": 100.0, "sgst": 100.0, "igst": 100.0, "cess": 0.0}
    mock_itc_2 = {"cgst": 100.0, "sgst": 100.0, "igst": 100.0, "cess": 0.0}
    
    # Scenario 3: Under Claim (Pass - Govt Safe)
    # RCM = 120, ITC = 100 -> Diff = -20, Liability SHOULD BE 0
    mock_rcm_3 = {"cgst": 120.0, "sgst": 120.0, "igst": 120.0, "cess": 0.0}
    mock_itc_3 = {"cgst": 100.0, "sgst": 100.0, "igst": 100.0, "cess": 0.0}

    with patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d') as mock_rcm_parser, \
         patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3') as mock_itc_parser, \
         patch('os.path.exists', return_value=True):
        
        # --- TEST 1: Excess ITC ---
        print("\n[TEST 1] Excess ITC (ITC=120, RCM=100)")
        mock_rcm_parser.return_value = mock_rcm_1
        mock_itc_parser.return_value = mock_itc_1
        
        res1 = parser._parse_rcm_liability("dummy.xlsx", gstr3b_pdf_paths=["dummy.pdf"])
        
        status1 = res1.get('status')
        liab1 = res1.get('total_shortfall')
        print(f"Status: {status1}")
        print(f"Total Liability: {liab1}")
        
        # We expect a mismatch here currently (Pass/0 instead of Fail/60) 
        # (20 * 3 heads = 60)
        
        # --- TEST 2: Equal ---
        print("\n[TEST 2] Equal (ITC=100, RCM=100)")
        mock_rcm_parser.return_value = mock_rcm_2
        mock_itc_parser.return_value = mock_itc_2
        
        res2 = parser._parse_rcm_liability("dummy.xlsx", gstr3b_pdf_paths=["dummy.pdf"])
        print(f"Status: {res2.get('status')}")
        print(f"Total Liability: {res2.get('total_shortfall')}")

        # --- TEST 3: Under Claim ---
        print("\n[TEST 3] Under Claim (ITC=100, RCM=120)")
        mock_rcm_parser.return_value = mock_rcm_3
        mock_itc_parser.return_value = mock_itc_3
        
        res3 = parser._parse_rcm_liability("dummy.xlsx", gstr3b_pdf_paths=["dummy.pdf"])
        print(f"Status: {res3.get('status')}")
        print(f"Total Liability: {res3.get('total_shortfall')}")

if __name__ == "__main__":
    test_sop2_logic()
