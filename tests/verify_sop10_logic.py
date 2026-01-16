
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP10Logic(unittest.TestCase):
    
    def setUp(self):
        self.parser = ScrutinyParser()
        
    @patch('src.services.scrutiny_parser.GSTR2BAnalyzer')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_1')
    def test_sop10_fail_scenario(self, mock_parse_3b, MockAnalyzer):
        """
        Scenario A: Fail
        3B IGST = 100
        2B IGST = 80
        Liability = 20 -> Fail
        """
        extra_files = {
            'gstr3b_monthly_Apr.pdf': 'dummy_3b.pdf',
            'gstr2b_monthly_Apr.xlsx': 'dummy_2b.xlsx'
        }
        
        # Mock 3B
        mock_parse_3b.return_value = {'igst': 100.0, 'cgst': 0, 'sgst': 0, 'cess': 0}
        
        # Mock 2B
        mock_instance = MagicMock()
        MockAnalyzer.return_value = mock_instance
        mock_instance.analyze_sop_10.return_value = {'status': 'pass', 'igst': 80.0}
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop10 = next(i for i in result['issues'] if i['issue_id'] == 'IMPORT_ITC_MISMATCH')
        
        print("\n=== Scenario A: Fail ===")
        print(f"Status: {sop10['status']}")
        print(f"Total Shortfall: {sop10['total_shortfall']}")
        
        self.assertEqual(sop10['status'], 'fail')
        self.assertEqual(sop10['total_shortfall'], 20.0)
        
        # Check Table
        rows = sop10['summary_table']['rows']
        self.assertEqual(rows[0]['col1']['value'], "100.00") # 3B
        self.assertEqual(rows[1]['col1']['value'], "80.00")  # 2B
        self.assertEqual(rows[2]['col1']['value'], "20.00")  # Diff
        self.assertEqual(rows[3]['col1']['value'], "20.00")  # Liability

    @patch('src.services.scrutiny_parser.GSTR2BAnalyzer')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_1')
    def test_sop10_pass_scenario(self, mock_parse_3b, MockAnalyzer):
        """
        Scenario B: Pass
        3B IGST = 80
        2B IGST = 100
        Liability = 0 -> Pass
        """
        extra_files = {
            'gstr3b_monthly_Apr.pdf': 'dummy_3b.pdf',
            'gstr2b_monthly_Apr.xlsx': 'dummy_2b.xlsx'
        }
        
        mock_parse_3b.return_value = {'igst': 80.0}
        
        mock_instance = MagicMock()
        MockAnalyzer.return_value = mock_instance
        mock_instance.analyze_sop_10.return_value = {'status': 'pass', 'igst': 100.0}
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop10 = next(i for i in result['issues'] if i['issue_id'] == 'IMPORT_ITC_MISMATCH')
        
        print("\n=== Scenario B: Pass ===")
        print(f"Status: {sop10['status']}")
        
        self.assertEqual(sop10['status'], 'pass')
        self.assertEqual(sop10['total_shortfall'], 0.0)

    @patch('src.services.scrutiny_parser.GSTR2BAnalyzer')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_1')
    def test_sop10_aggregation(self, mock_parse_3b, MockAnalyzer):
        """
        Scenario C: Aggregation
        2 3B Files -> 50 + 50 = 100
        2 2B Files -> 40 + 40 = 80
        Result: 100 - 80 = 20 Fail
        """
        extra_files = {
            'gstr3b_1.pdf': 'path1.pdf',
            'gstr3b_2.pdf': 'path2.pdf',
            'gstr2b_1.xlsx': 'path1.xlsx',
            'gstr2b_2.xlsx': 'path2.xlsx'
        }
        
        mock_parse_3b.return_value = {'igst': 50.0}
        
        mock_instance = MagicMock()
        MockAnalyzer.return_value = mock_instance
        mock_instance.analyze_sop_10.return_value = {'status': 'pass', 'igst': 40.0}
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop10 = next(i for i in result['issues'] if i['issue_id'] == 'IMPORT_ITC_MISMATCH')
        
        print("\n=== Scenario C: Aggregation ===")
        # 3B called twice?
        # 2B instantiated twice?
        
        # Check values in table
        rows = sop10['summary_table']['rows']
        v_3b = float(rows[0]['col1']['value'])
        v_2b = float(rows[1]['col1']['value'])
        
        print(f"3B Aggregated: {v_3b}")
        print(f"2B Aggregated: {v_2b}")
        
        self.assertEqual(v_3b, 100.0)
        self.assertEqual(v_2b, 80.0)
        self.assertEqual(sop10['status'], 'fail')

    def test_sop10_missing_data(self):
        """
        Scenario D: Missing Data -> Info
        """
        extra_files = {} # Empty
        
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        sop10 = next(i for i in result['issues'] if i['issue_id'] == 'IMPORT_ITC_MISMATCH')
        
        print("\n=== Scenario D: Missing Data ===")
        print(f"Status: {sop10['status']}")
        self.assertEqual(sop10['status'], 'info')

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSOP10Logic)
    unittest.TextTestRunner(verbosity=2).run(suite)
