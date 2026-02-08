
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP9Applicability(unittest.TestCase):
    
    @patch('src.utils.pdf_parsers.parse_gstr3b_sop9_identifiers')
    def test_yearly_file_rejection(self, mock_parser):
        # Setup specific return for "Yearly" simulation
        mock_parser.return_value = {
            "fy": "2022-23", 
            "month": None, 
            "filing_date": None, 
            "frequency": "Yearly", 
            "error": None
        }
        
        parser = ScrutinyParser()
        # Mock file path
        pdf_path = "dummy_annual.pdf"
        
        # Create a dummy file to pass os.path.exists check
        with open(pdf_path, 'w') as f: f.write("dummy")
            
        try:
            # Execute
            result = parser._parse_sop_9([pdf_path])
            
            # Verify
            print("Status:", result['status'])
            print("Message:", result['status_msg'])
            
            self.assertEqual(result['status'], 'info')
            self.assertIn("Monthly GSTR-3B PDFs are required", result['status_msg'])
            # self.assertIn("Yearly", result['status_msg']) # REMOVED: Requirement is generic message
            print(">>> SUCCESS: Yearly file correctly rejected with proper message.")
            
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    @patch('src.utils.pdf_parsers.parse_gstr3b_sop9_identifiers')
    def test_monthly_file_acceptance(self, mock_parser):
        # Setup specific return for "Monthly" simulation
        mock_parser.return_value = {
            "fy": "2022-23", 
            "month": "February", 
            "filing_date": "20/03/2023", 
            "frequency": "Monthly", 
            "error": None
        }
        
        parser = ScrutinyParser()
        pdf_path = "dummy_monthly.pdf"
        with open(pdf_path, 'w') as f: f.write("dummy")

        try:
            # We also need to mock table parsers since they will be called if it proceeds
            with patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_1', return_value={}), \
                 patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_2_3', return_value={}), \
                 patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_4', return_value={}), \
                 patch('src.services.scrutiny_parser.parse_gstr3b_pdf_table_4_a_5', return_value={}):
                 
                result = parser._parse_sop_9([pdf_path])
                
                print("Status:", result['status'])
                self.assertNotEqual(result['status'], 'info') # Should be pass/fail
                print(">>> SUCCESS: Monthly file accepted for processing.")
                
        finally:
             if os.path.exists(pdf_path):
                os.remove(pdf_path)

if __name__ == '__main__':
    unittest.main()
