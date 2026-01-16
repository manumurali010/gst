
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP9Logic(unittest.TestCase):
    
    def setUp(self):
        self.parser = ScrutinyParser()
        
    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    def test_sop9_fail_scenario(self, mock_parse):
        """
        Apr-2022: Late Filing (Dec 2023), ITC > 0 -> FAIL
        May-2022: On Time -> PASS
        Expected: Overall FAIL
        """
        extra_files = {
            'gstr3b_monthly_Apr': 'dummy_apr.pdf',
            'gstr3b_monthly_May': 'dummy_may.pdf'
        }
        
        def side_effect(path):
            if 'apr' in path: 
                # Cutoff for Apr 2022 is 30 Nov 2023. 
                # We file on 1 Dec 2023 (Late)
                return {
                    'return_period': 'April 2022',
                    'filing_date': '01/12/2023',
                    'itc': {'igst': 100.0, 'cgst': 50.0, 'sgst': 50.0, 'cess': 0.0}
                }
            if 'may' in path:
                return {
                    'return_period': 'May 2022',
                    'filing_date': '20/06/2022',
                    'itc': {'igst': 100.0, 'cgst': 50.0, 'sgst': 50.0, 'cess': 0.0}
                }
            return {}
            
        mock_parse.side_effect = side_effect
        
        result = self.parser.parse_file("dummy.xlsx", extra_files, configs={'gstr3b_freq': 'Monthly'})
        issues = result['issues']
        sop9 = next(i for i in issues if i['issue_id'] == 'SEC_16_4_VIOLATION')
        
        print("\n=== Scenario A: Fail ===")
        print(f"Status: {sop9['status']}")
        print(f"Total Shortfall: {sop9['total_shortfall']}")
        
        self.assertEqual(sop9['status'], 'fail')
        self.assertGreater(sop9['total_shortfall'], 0)
        # Inadmissible = 100+50+50 = 200
        self.assertAlmostEqual(sop9['total_shortfall'], 200.0)
        
        # Check Rows
        rows = sop9['summary_table']['rows']
        # Row 0 (Apr), Row 1 (May), Row 2 (Total)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]['col0']['value'], 'TOTAL')
        self.assertEqual(float(rows[-1]['col8']['value']), 200.0)

    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    def test_sop9_pass_zero_itc(self, mock_parse):
        """
        Apr-2022: Late Filing, ITC = 0 -> PASS
        """
        extra_files = {'gstr3b_monthly_Apr': 'dummy_apr.pdf'}
        
        def side_effect(path):
            return {
                'return_period': 'April 2022',
                'filing_date': '01/12/2023', # Late
                'itc': {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
            }
        mock_parse.side_effect = side_effect
        
        result = self.parser.parse_file("dummy.xlsx", extra_files, configs={'gstr3b_freq': 'Monthly'})
        sop9 = next(i for i in result['issues'] if i['issue_id'] == 'SEC_16_4_VIOLATION')
        
        print("\n=== Scenario B: Pass (Zero ITC) ===")
        print(f"Status: {sop9['status']}")
        self.assertEqual(sop9['status'], 'pass')
        self.assertEqual(sop9['total_shortfall'], 0)

    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    def test_sop9_mixed_pass_info(self, mock_parse):
        """
        Apr-2022: On Time -> PASS
        May-2022: Parse Error -> INFO
        Expected: PASS (Because not ALL info, and no FAIL)
        """
        extra_files = {'gstr3b_monthly_Apr': 'dummy_apr.pdf', 'gstr3b_monthly_May': 'dummy_may.pdf'}
        
        def side_effect(path):
            if 'apr' in path:
                return {
                    'return_period': 'April 2022',
                    'filing_date': '20/05/2022', 
                    'itc': {'igst': 100.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
                }
            return {'return_period': None} # Fail
            
        mock_parse.side_effect = side_effect
        
        result = self.parser.parse_file("dummy.xlsx", extra_files, configs={'gstr3b_freq': 'Monthly'})
        sop9 = next(i for i in result['issues'] if i['issue_id'] == 'SEC_16_4_VIOLATION')
        
        print("\n=== Scenario C: Mixed Pass/Info ===")
        print(f"Status: {sop9['status']}")
        self.assertEqual(sop9['status'], 'pass')

    @patch('src.services.scrutiny_parser.parse_gstr3b_metadata')
    def test_sop9_all_info(self, mock_parse):
        """
        All Parsing Failed -> INFO
        """
        extra_files = {'gstr3b_monthly_Apr': 'dummy_apr.pdf'}
        mock_parse.return_value = {} # Empty
        
        result = self.parser.parse_file("dummy.xlsx", extra_files, configs={'gstr3b_freq': 'Monthly'})
        sop9 = next(i for i in result['issues'] if i['issue_id'] == 'SEC_16_4_VIOLATION')
        
        print("\n=== Scenario D: All Info ===")
        print(f"Status: {sop9['status']}")
        self.assertEqual(sop9['status'], 'info')

if __name__ == '__main__':
    unittest.main()
