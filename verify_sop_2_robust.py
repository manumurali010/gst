import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Path Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from services.scrutiny_parser import ScrutinyParser

class TestSOP2Robust(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()

    @patch('services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d')
    @patch('services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3')
    @patch('os.path.exists')
    def test_yearly_authoritative(self, mock_exists, mock_itc, mock_rcm):
        mock_exists.return_value = True
        mock_rcm.return_value = {"igst": 100, "cgst": 0, "sgst": 0, "cess": 0}
        mock_itc.return_value = {"igst": 50, "cgst": 0, "sgst": 0, "cess": 0}
        
        extra_files = {
            "gstr3b_yearly": "path/yearly.pdf",
            "gstr3b_monthly_0": "path/monthly.pdf"
        }
        
        # We manually call _parse_rcm_liability via parse_file logic 
        # But let's test the aggregation logic in _parse_rcm_liability directly with path lists
        res = self.parser._parse_rcm_liability(None, gstr3b_pdf_paths=["path/yearly.pdf"])
        
        self.assertEqual(res['total_shortfall'], 50)
        self.assertEqual(res['status'], 'fail')
        self.assertEqual(len(res['summary_table']['rows']), 4)
        print("Passed: Yearly Authoritative")

    @patch('services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d')
    @patch('services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3')
    @patch('os.path.exists')
    def test_monthly_aggregation(self, mock_exists, mock_itc, mock_rcm):
        mock_exists.return_value = True
        # PDF 1
        mock_rcm.side_effect = [{"igst": 100, "cgst": 0, "sgst": 0, "cess": 0}, {"igst": 200, "cgst": 0, "sgst": 0, "cess": 0}]
        mock_itc.side_effect = [{"igst": 50, "cgst": 0, "sgst": 0, "cess": 0}, {"igst": 50, "cgst": 0, "sgst": 0, "cess": 0}]
        
        res = self.parser._parse_rcm_liability(None, gstr3b_pdf_paths=["m1.pdf", "m2.pdf"])
        
        # Total Liab = 100+200 = 300
        # Total ITC = 50+50 = 100
        # Shortfall = 200
        self.assertEqual(res['total_shortfall'], 200)
        
        # Verify Row values
        rows = res['summary_table']['rows']
        self.assertEqual(rows[0]['col3'], 300.0) # IGST Liab
        self.assertEqual(rows[1]['col3'], 100.0) # IGST ITC
        print("Passed: Monthly Aggregation")

    def test_missing_files_unconditional_table(self):
        # Test with no PDF paths
        res = self.parser._parse_rcm_liability(None, gstr3b_pdf_paths=[])
        
        self.assertEqual(res['status'], 'info')
        self.assertEqual(res['total_shortfall'], 0)
        self.assertEqual(len(res['summary_table']['headers']), 5)
        self.assertEqual(len(res['summary_table']['rows']), 4)
        # All numeric values should be 0.0
        self.assertEqual(res['summary_table']['rows'][0]['col1'], 0.0)
        print("Passed: Missing Files Unconditional Table")

    @patch('services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d')
    def test_parse_failure_robustness(self, mock_rcm):
        mock_rcm.side_effect = Exception("Corrupt PDF")
        
        res = self.parser._parse_rcm_liability(None, gstr3b_pdf_paths=["corrupt.pdf"])
        
        self.assertEqual(res['status'], 'info')
        self.assertEqual(res['status_msg'], "GSTR-3B PDF parsing failed")
        self.assertEqual(len(res['summary_table']['rows']), 4) # Still shows table
        print("Passed: Parse Failure Robustness")

    @patch('services.scrutiny_parser.ScrutinyParser._parse_rcm_liability')
    @patch('os.path.exists')
    def test_parse_file_yearly_precedence(self, mock_exists, mock_rcm_method):
        mock_exists.return_value = True
        mock_rcm_method.return_value = {"issue_id": "RCM_LIABILITY_ITC", "status": "pass"}
        
        extra_files = {
            "gstr3b_yearly": "path/yearly.pdf",
            "gstr3b_monthly_0": "path/m0.pdf",
            "gstr3b_monthly_1": "path/m1.pdf"
        }
        
        # We only care that _parse_rcm_liability gets the right list
        try:
            with patch('pandas.read_excel', return_value=MagicMock()):
                self.parser.parse_file("path/excel.xlsx", extra_files=extra_files)
        except:
            pass # We don't care if it fails later in the method
        
        # Verify that _parse_rcm_liability was called with ONLY the yearly path
        found_target_call = False
        for call in mock_rcm_method.call_args_list:
            if call[1].get('gstr3b_pdf_paths') == ["path/yearly.pdf"]:
                found_target_call = True
                break
        
        self.assertTrue(found_target_call, "ScrutinyParser._parse_rcm_liability should be called with yearly PDF only when yearly exists")
        print("Passed: parse_file Yearly Precedence Integration")

if __name__ == "__main__":
    unittest.main()
