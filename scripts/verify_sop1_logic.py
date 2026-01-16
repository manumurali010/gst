import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pandas as pd

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP1Logic(unittest.TestCase):
    
    def setUp(self):
        self.parser = ScrutinyParser()
        
    @patch('src.services.scrutiny_parser.os.path.exists')
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a')
    @patch('src.services.scrutiny_parser.parse_gstr1_pdf_total_liability')
    def test_sop1_pdf_precedence(self, mock_gstr1_parser, mock_gstr3b_parser, mock_exists):
        """Test Case 1: PDF Precedence (PDFs available -> Excel ignored)"""
        print("\n--- Test Case 1: PDF Precedence ---")
        
        # Mock PDF Data (Scenario: Shortfall)
        # GSTR-1 (Declared): 1200
        # GSTR-3B (Reported): 1000
        # Diff: 200 (Liability)
        mock_gstr1_parser.return_value = {'igst': 1200.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
        mock_gstr3b_parser.return_value = {'igst': 1000.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
        mock_exists.return_value = True
        
        # Call parser with both PDF and Excel path
        # Note: In real run, excel presence checked via os.path.exists.
        # We assume file_path "dummy.xlsx" exists for the function call, but we want to verify it DOES NOT read it or use it if PDFs are valid.
        # Actually checking if it reads excel is hard without mocking openpyxl/pd.read_excel.
        # But if the result matches PDF values exactly, we know Excel wasn't used (assuming Excel would have diff values).
        
        res = self.parser._parse_group_a_liability(
            file_path="dummy.xlsx", 
            sheet_keyword="Tax Liability", 
            default_category="Cat", 
            template_type="summary_3x4", 
            target_cols=[], 
            gstr3b_pdf_path="dummy_3b.pdf", 
            gstr1_pdf_path="dummy_1.pdf"
        )
        
        print(f"Result Status: {res['status']}")
        print(f"Result Summary Table: {res.get('summary_table')}")
        
        self.assertEqual(res['total_shortfall'], 200.0)
        self.assertEqual(res['status'], 'fail') # Shortfall > 100
        
        # Verify Summary Table Context
        st = res['summary_table']
        rows = st['rows']
        # Row 0: Declared (GSTR-1)
        self.assertEqual(rows[0]['col3']['value'], 1200.0) # IGST
        # Row 1: Reported (GSTR-3B)
        self.assertEqual(rows[1]['col3']['value'], 1000.0) # IGST
        
    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a')
    @patch('src.services.scrutiny_parser.parse_gstr1_pdf_total_liability')
    def test_sop1_aggregation(self, mock_gstr1_parser, mock_gstr3b_parser):
        """Test Case 2: Aggregation of lists (if supported by caller, but function takes single path arg?)
           Wait, the requirement said 'Iterate over all provided GSTR-1 and GSTR-3B PDFs'.
           But the signature of _parse_group_a_liability has 'gstr3b_pdf_path' (singular).
           I need to CHECK if I should update the signature or if the caller passes a list?
           The current signature is: (..., gstr3b_pdf_path=None, gstr1_pdf_path=None).
           I MUST update it to accept LIST or handle list in singular arg?
           The plan says "Iterate over all provided...".
           So I should likely support list.
        """
        pass 

    @patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_3_1_a')
    def test_sop1_failure_semantics(self, mock_3b):
        """Test Case 3: Partial PDF Failure -> Fallback to Excel (or Fail if strict policy applied to batch)"""
        pass

if __name__ == '__main__':
    unittest.main()
