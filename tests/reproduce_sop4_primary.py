import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import source modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP4PrimaryLayout(unittest.TestCase):

    @patch('src.services.scrutiny_parser.GSTR2BAnalyzer')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_5')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_d') 
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_4')
    @patch('src.services.scrutiny_parser.os.path.exists') # Mock os.path.exists to pass file check
    def test_sop4_primary_path_structure(self, mock_exists, mock_4a4, mock_4a23, mock_31d, mock_4a5, mock_2b_cls):
        """
        Test that SOP-4 Primary Path (3B PDF + 2B Analyzer) generates a 4-row table.
        Rows: Claimed, Available, Difference (Raw), Liability (Positive)
        """
        mock_exists.return_value = True
        
        # 1. Setup Data for SOP-4
        # Claimed (3B) = 100
        mock_4a5.return_value = {'igst': 100.0, 'cgst': 100.0, 'sgst': 100.0, 'cess': 0.0}
        
        # Test POSITIVE Liability first (3B > 2B)
        # 3B=100, 2B=80. Diff = 20. Liability = 20.
        mock_2b_inst = MagicMock()
        mock_2b_inst.get_all_other_itc_raw_data.return_value = {'igst': 80.0, 'cgst': 80.0, 'sgst': 80.0, 'cess': 0.0}
        
        # We need the constructor to return our instance
        mock_2b_cls.return_value = mock_2b_inst

        # 2. Mock other SOPS to avoid noise or crashes
        mock_31d.return_value = {} 
        mock_4a23.return_value = {} 
        mock_4a4.return_value = {}

        # 3. Execution
        parser = ScrutinyParser()
        
        print("Running parse_file with mocks...")
        result = parser.parse_file(
            file_path="mock_3b.pdf",
            extra_files={'gstr_2b': 'mock_2b.json', 'gstr3b_pdf': 'mock_3b.pdf'}
        )
        issues = result['issues']
        
        print(f"DEBUG: Issues list contains {len(issues)} items")
        for idx, item in enumerate(issues):
            print(f"Item {idx}: type={type(item)} val={item}")
            
        sop4 = next((i for i in issues if isinstance(i, dict) and i.get('issue_id') == 'ITC_3B_2B_OTHER'), None)
        self.assertIsNotNone(sop4, "SOP-4 Issue not found in result")
        
        print(f"SOP-4 Status: {sop4.get('status')}")
        print(f"SOP-4 Msg: {sop4.get('status_msg')}")
        
        summary_rows = sop4.get('summary_table', {}).get('rows', [])
        print("\nGenerated SOP-4 Table Rows:")
        for r in summary_rows:
            print(r)
            
        # 5. Assertions
        self.assertEqual(len(summary_rows), 4, f"Expected 4 rows, got {len(summary_rows)}")
        
        # Row 2: Difference (3B - 2B) -> 100 - 80 = 20
        self.assertIn("Difference (GSTR 3B - GSTR 2B)", summary_rows[2]['col0']['value'])
        self.assertEqual(summary_rows[2]['col1']['value'], 20.0)
        
        # Row 3: Liability -> 20
        self.assertIn("Liability", summary_rows[3]['col0']['value'])
        self.assertEqual(summary_rows[3]['col1']['value'], 20.0)

        # 6. Test NEGATIVE Difference (3B < 2B)
        # 3B=100, 2B=150. Diff = -50. Liability = 0.
        mock_2b_inst.get_all_other_itc_raw_data.return_value = {'igst': 150.0, 'cgst': 150.0, 'sgst': 150.0, 'cess': 0.0}
        
        result_neg = parser.parse_file(
            file_path="mock_3b.pdf",
            extra_files={'gstr_2b': 'mock_2b.json', 'gstr3b_pdf': 'mock_3b.pdf'}
        )
        issues_neg = result_neg['issues']
        sop4_neg = next((i for i in issues_neg if i['issue_id'] == 'ITC_3B_2B_OTHER'), None)
        neg_rows = sop4_neg['summary_table']['rows']
        
        print("\nNegative Case Rows:")
        for r in neg_rows: print(r)
        
        # Difference should be -50
        self.assertEqual(neg_rows[2]['col1']['value'], -50.0)
        # Liability should be 0
        self.assertEqual(neg_rows[3]['col1']['value'], 0.0)

if __name__ == '__main__':
    unittest.main()
