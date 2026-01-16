import sys
import os
import json
from unittest.mock import MagicMock, patch

# Path Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from services.scrutiny_parser import ScrutinyParser

def diagnostic_log_sop2():
    parser = ScrutinyParser()
    
    # Mock PDF Parsers to return dummy data
    p1 = patch('services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d', return_value={"igst": 1000, "cgst": 500, "sgst": 500, "cess": 100})
    p2 = patch('services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3', return_value={"igst": 800, "cgst": 400, "sgst": 400, "cess": 50})
    p3 = patch('os.path.exists', return_value=True)
    
    with p1, p2, p3:
        # Simulate parse_file call for SOP-2
        res = parser._parse_rcm_liability("dummy.xlsx", gstr3b_pdf_paths=["mock.pdf"])
        
        # Add the enrichment-style metadata that parse_file adds
        res['category'] = "RCM (GSTR 3B vs GSTR 2B)"
        res['description'] = "Point 2- RCM (GSTR 3B vs GSTR 2B)"
        
        print("\n=== SOP-2 PAYLOAD JSON DUMP ===")
        print(json.dumps(res, indent=2))
        print("===============================\n")

if __name__ == "__main__":
    diagnostic_log_sop2()
