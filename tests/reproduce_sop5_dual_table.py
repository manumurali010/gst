import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import source modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP5DualTable(unittest.TestCase):

    @patch('src.services.gstr_2a_analyzer.GSTR2AAnalyzer')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a') 
    @patch('src.services.scrutiny_parser.os.path.exists')
    def test_sop5_dual_table_logic(self, mock_exists, mock_31a, mock_2a_cls):
        """
        Test SOP-5 Phase 2: Dual Table Layout (TDS/TCS)
        """
        mock_exists.return_value = True
        
        # 1. Mock 3B Data (Table 3.1(a) Taxable Value)
        # Case A: 3B Taxable = 1000
        mock_31a.return_value = {'taxable_value': 1000.0}
        
        # 2. Mock 2A Data (TDS + TCS)
        mock_2a_inst = MagicMock()
        mock_2a_cls.return_value = mock_2a_inst
        
        # Scenario 1: TDS Shortfall (1200 - 1000 = 200), TCS Matched (800 - 1000 = -200 -> 0)
        mock_2a_inst.analyze_sop.return_value = {
            'tds': {'status': 'pass', 'base_value': 1200.0},
            'tcs': {'status': 'pass', 'base_value': 800.0}
        }
        
        # Execution
        parser = ScrutinyParser()
        print("\n--- Running SOP-5 Dual Table Test (Scenario 1) ---")
        
        # Note: parse_file signature requires gstr_2a in extra_files to create gstr2a_analyzer
        result = parser.parse_file(
            file_path="mock_3b.pdf",
            extra_files={'gstr_2a': 'mock_2a.xlsx'},
            gstr2a_analyzer=mock_2a_inst
        )
        issues = result['issues']
        sop5 = next((i for i in issues if i['issue_id'] == 'TDS_TCS_MISMATCH'), None)
        
        self.assertIsNotNone(sop5, "SOP-5 Issue not found")
        self.assertEqual(sop5['status'], 'fail', "SOP-5 should be FAIL due to TDS shortfall")
        
        # Verify Tables
        tables = sop5.get('tables', [])
        self.assertEqual(len(tables), 2, "Should have 2 tables (TDS + TCS)")
        
        # Verify TDS Table
        tds_tbl = tables[0]
        self.assertIn("TDS", tds_tbl['title'])
        rows_tds = tds_tbl['rows']
        # Row 2: Diff (1200 - 1000 = 200)
        self.assertEqual(rows_tds[2]['col1']['value'], 200.0)
        # Row 3: Liab (200)
        self.assertEqual(rows_tds[3]['col1']['value'], 200.0)
        
        # Verify TCS Table
        tcs_tbl = tables[1]
        self.assertIn("TCS", tcs_tbl['title'])
        rows_tcs = tcs_tbl['rows']
        # Row 2: Diff (800 - 1000 = -200)
        self.assertEqual(rows_tcs[2]['col1']['value'], -200.0)
        # Row 3: Liab (0)
        self.assertEqual(rows_tcs[3]['col1']['value'], 0.0)
        
        print("Scenario 1 Check Passed: Dual Tables Created, Liability Logic Correct.")

        # Scenario 2: Partial Data (TDS Missing/Info, TCS Shortfall)
        print("\n--- Running SOP-5 Partial Data Test (Scenario 2) ---")
        mock_2a_inst.analyze_sop.return_value = {
            'tds': {'status': 'info', 'reason': 'Sheet Missing'},
            'tcs': {'status': 'pass', 'base_value': 1500.0} # 1500 - 1000 = 500 Liab
        }
        
        result_2 = parser.parse_file(
            file_path="mock_3b.pdf",
            extra_files={'gstr_2a': 'mock_2a.xlsx'},
            gstr2a_analyzer=mock_2a_inst
        )
        sop5_2 = next((i for i in result_2['issues'] if i['issue_id'] == 'TDS_TCS_MISMATCH'), None)
        
        self.assertEqual(sop5_2['status'], 'fail', "SOP-5 should FAIL due to TCS shortfall")
        tables_2 = sop5_2.get('tables', [])
        self.assertEqual(len(tables_2), 2)
        
        # TDS Table should show Info
        self.assertIn("Data Not Available", tables_2[0]['rows'][0]['col0']['value'])
        
        # TCS Table should show Liab
        self.assertEqual(tables_2[1]['rows'][3]['col1']['value'], 500.0)
        
        print("Scenario 2 Check Passed: Partial Data handled correctly.")

if __name__ == '__main__':
    unittest.main()
