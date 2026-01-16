import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

class TestSOP3Logic(unittest.TestCase):
    
    def test_sop3_summary_structure_parsing(self):
        """Test the robust parsing of ITC Available summary sheet"""
        # Create a mock DataFrame mimicking the summary sheet
        data = [
            ["ITC Available for Distribution", "", "", "", ""],
            ["Details", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"],
            ["Part A", "", "", "", ""],
            ["Inward Supplies from ISD", 1000, 500, 500, 100],
            ["Part B", "", "", "", ""],
            ["ISD - Credit Notes", 100, 50, 50, 10],
            ["ISD - Credit Notes (Amendment)", 50, 0, 0, 0], # Net should be 1000 - 100 - 50 = 850
        ]
        df = pd.DataFrame(data)
        
        # Mock Analyzer
        analyzer = GSTR2AAnalyzer("dummy.xlsx")
        analyzer.xl_file = MagicMock()
        analyzer.xl_file.parse.return_value = df
        analyzer.xl_file.sheet_names = ["ITC Available"]
        
        # We need to test _analyze_sop_3_summary_structure directly or via _compute_sop_3
        # Since _analyze_sop_3_summary_structure is internal, we call _compute_sop_3
        # But _compute_sop_3 checks sheet names.
        
        res = analyzer._compute_sop_3()
        print(f"SOP-3 Compute Result: {res}")
        
        self.assertEqual(res['igst'], 850.0)
        self.assertEqual(res['cgst'], 450.0)
        self.assertEqual(res['sgst'], 450.0)
        self.assertEqual(res['cess'], 90.0)
        self.assertEqual(res['status'], 'pass')

    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_4')
    def test_sop3_phase2_logic(self, mock_pdf_parser):
        """Test ScrutinyParser Phase 2 dispatch and logic"""
        parser = ScrutinyParser()
        
        # Mock GSTR2AAnalyzer result
        analyzer = MagicMock()
        analyzer.analyze_sop.return_value = {
            'status': 'pass',
            'igst': 850.0, 'cgst': 450.0, 'sgst': 450.0, 'cess': 90.0
        }
        
        # 1. Test with PDF (Higher Claim) -> Shortfall
        # 3B Claim: 2000 total. 2B Available: 1840 total.
        mock_pdf_parser.return_value = {'igst': 1000, 'cgst': 500, 'sgst': 500, 'cess': 0}
        
        res = parser._parse_isd_credit_phase2("dummy.xlsx", analyzer, gstr3b_pdf_paths=["dummy.pdf"])
        print(f"\nScenario 1 (Shortfall): {res['status_msg']}")
        
        self.assertEqual(res['status'], 'fail')
        self.assertGreater(res['total_shortfall'], 0)
        self.assertEqual(res['total_shortfall'], 2000 - 1840)
        
        # 2. Test with PDF (Lower Claim) -> Match
        # 3B Claim: 1000. 2B Available: 1840.
        mock_pdf_parser.return_value = {'igst': 500, 'cgst': 250, 'sgst': 250, 'cess': 0}
        
        res = parser._parse_isd_credit_phase2("dummy.xlsx", analyzer, gstr3b_pdf_paths=["dummy.pdf"])
        print(f"Scenario 2 (Match): {res['status_msg']}")
        
        self.assertEqual(res['status'], 'pass')
        self.assertEqual(res['total_shortfall'], 0)
        
        # [SOP-3 FIX Verify]
        self.assertIn('summary_table', res)
        self.assertEqual(len(res['summary_table']['rows']), 4)
        print(f"Verified Summary Table Rows: {[r['col0']['value'] for r in res['summary_table']['rows']]}")

        # 3. Test PDF Failure -> Fallback to Legacy -> Fallback Fail -> 0 Claim
        mock_pdf_parser.return_value = None # Parser fail
        # Legacy excel read will fail (no file)
        
        res = parser._parse_isd_credit_phase2("dummy.xlsx", analyzer, gstr3b_pdf_paths=["dummy.pdf"])
        print(f"Scenario 3 (PDF Fail -> 0 Claim): {res['status_msg']}")
        
        # Should be NO mismatch because Claim 0 < Available 1840
        self.assertEqual(res['status'], 'match') 
        self.assertIn("No Mismatch", res['status_msg'])

if __name__ == '__main__':
    unittest.main()
