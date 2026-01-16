
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP11Logic(unittest.TestCase):
    
    def setUp(self):
        self.parser = ScrutinyParser()
        
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_b')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_c')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_e')
    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_b_1')
    def test_sop11_fail_scenario(self, mock_4b1, mock_meta, mock_31e, mock_31c, mock_31b, mock_31a):
        """
        Scenario A: Fail
        Exempt = 50 (c) + 50 (e) = 100
        Taxable = 400 (a) + 0 (b) = 400
        Total Turnover = 500.
        Ratio = 100/500 = 0.20 (20%)
        Total ITC = 1000.
        Required Reversal = 200.
        Actual Reversal = 150.
        Liability = 50 -> Fail.
        """
        extra_files = {'gstr3b_Apr.pdf': 'dummy.pdf'}
        
        # Mock 3.1
        mock_31a.return_value = {'taxable_value': 400.0}
        mock_31b.return_value = {'taxable_value': 0.0}
        mock_31c.return_value = {'taxable_value': 50.0}
        mock_31e.return_value = {'taxable_value': 50.0}
        
        # Mock Meta (ITC)
        # Sum = 1000.
        mock_meta.return_value = {'itc': {'igst': 500, 'cgst': 250, 'sgst': 250, 'cess': 0}}
        
        # Mock Actual Reversal
        mock_4b1.return_value = {'igst': 75, 'cgst': 37.5, 'sgst': 37.5, 'cess': 0} # Sum = 150
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop11 = next(i for i in result['issues'] if i['issue_id'] == 'RULE_42_43_VIOLATION')
        
        print("\n=== Scenario A: Fail ===")
        print(f"Status: {sop11['status']}")
        print(f"Liability: {sop11['total_shortfall']}")
        
        # Assertions
        self.assertEqual(sop11['status'], 'fail')
        self.assertEqual(sop11['total_shortfall'], 50.0)
        
        # Check Table Values
        rows = sop11['summary_table']['rows']
        # Row 0: Exempt -> 100.00
        self.assertEqual(rows[0]['col1']['value'], "100.00")
        # Row 1: Total -> 500.00
        self.assertEqual(rows[1]['col1']['value'], "500.00")
        # Row 2: Ratio -> 20.00%
        self.assertEqual(rows[2]['col1']['value'], "20.00%")
        # Row 3: Total ITC -> 1000.00
        self.assertEqual(rows[3]['col1']['value'], "1000.00")
        # Row 4: Required -> 200.00
        self.assertEqual(rows[4]['col1']['value'], "200.00")
        # Row 5: Actual -> 150.00
        self.assertEqual(rows[5]['col1']['value'], "150.00")
        # Row 7: Liability -> 50.00
        self.assertEqual(rows[7]['col1']['value'], "50.00")

    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_b')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_c')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_e')
    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_b_1')
    def test_sop11_pass_scenario(self, mock_4b1, mock_meta, mock_31e, mock_31c, mock_31b, mock_31a):
        """
        Scenario B: Pass
        Ratio = 20%
        Required = 200.
        Actual = 250.
        Liability = 0.
        """
        extra_files = {'gstr3b_Apr.pdf': 'dummy.pdf'}
        mock_31a.return_value = {'taxable_value': 400.0}
        mock_31b.return_value = {'taxable_value': 0.0}
        mock_31c.return_value = {'taxable_value': 50.0}
        mock_31e.return_value = {'taxable_value': 50.0}
        mock_meta.return_value = {'itc': {'igst': 500, 'cgst': 250, 'sgst': 250, 'cess': 0}} # 1000
        mock_4b1.return_value = {'igst': 125, 'cgst': 62.5, 'sgst': 62.5, 'cess': 0} # 250
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop11 = next(i for i in result['issues'] if i['issue_id'] == 'RULE_42_43_VIOLATION')
        
        print("\n=== Scenario B: Pass ===")
        print(f"Status: {sop11['status']}")
        self.assertEqual(sop11['status'], 'pass')
        self.assertEqual(sop11['total_shortfall'], 0.0)

    def test_sop11_missing_data(self):
        """
        Scenario C: Missing Data
        """
        extra_files = {} 
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop11 = next(i for i in result['issues'] if i['issue_id'] == 'RULE_42_43_VIOLATION')
        
        print("\n=== Scenario C: Missing Data ===")
        self.assertEqual(sop11['status'], 'info')

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSOP11Logic)
    unittest.TextTestRunner(verbosity=2).run(suite)
