
import unittest
from unittest.mock import patch, MagicMock
from src.services.file_validation_service import FileValidationService

class TestFYExtraction(unittest.TestCase):

    @patch('fitz.open')
    def test_derive_fy_from_month_name(self, mock_open):
        print("\n[TEST] Derive FY from Month Name (April 2018)")
        mock_doc = MagicMock()
        mock_page = MagicMock()
        # Text with Month Year but no explicit FY
        mock_page.get_text.return_value = "GSTIN: 29ABCDE1234F1Z5\nReturn for April 2018"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # Expected: April 2018 -> 2018-19
        res = FileValidationService._extract_pdf_metadata("dummy.pdf", "GSTR3B")
        print(f"Result: {res}")
        self.assertEqual(res['fy'], "2018-19")

    @patch('fitz.open')
    def test_derive_fy_from_numeric_period(self, mock_open):
        print("\n[TEST] Derive FY from Numeric Period (02-2019)")
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "GSTIN: 29ABCDE1234F1Z5\nPeriod: 02-2019"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # Expected: Feb 2019 -> 2018-19
        res = FileValidationService._extract_pdf_metadata("dummy.pdf", "GSTR3B")
        print(f"Result: {res}")
        self.assertEqual(res['fy'], "2018-19")

    @patch('fitz.open')
    def test_derive_fy_mismatch_warn(self, mock_open):
        print("\n[TEST] Validation Warn on Mismatch")
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "GSTIN: 29ABCDE1234F1Z5\nReturn for April 2018"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        # Case FY is 2024-25. Extracted is 2018-19.
        # Should result in WARNING with specific message
        is_valid, level, payload = FileValidationService.validate_file("dummy.pdf", "gstr3b", "29ABCDE1234F1Z5", "2024-25")
        
        print(f"Valid: {is_valid}, Level: {level}, Warns: {payload}")
        self.assertEqual(level, "WARNING")
        # Check that it's a MISMATCH warning, not MISSING
        self.assertEqual(payload[0]['url_type'], "FY_MISMATCH") # Wait, warning_type key
        self.assertEqual(payload[0]['warning_type'], "FY_MISMATCH")
        self.assertEqual(payload[0]['extracted_value'], "2018-19")

if __name__ == '__main__':
    unittest.main()
