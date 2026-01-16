import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.file_validation_service import FileValidationService

class TestGSTINRobustness(unittest.TestCase):
    
    def setUp(self):
        self.sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_042022.pdf"
        self.real_gstin = "32AADFW8764E1Z1"
        self.wrong_gstin = "29ABCDE1234F1Z5"

    def test_tier2_extraction_success(self):
        """Test that the sample PDF extracts the GSTIN correctly (via Tier 1 or Tier 2)."""
        print("\n[Test] Extraction from Real PDF")
        if not os.path.exists(self.sample_pdf):
            print("Skipping real PDF test (file not found)")
            return

        meta = FileValidationService._extract_pdf_metadata(self.sample_pdf)
        print(f"Extracted Metadata: {meta}")
        self.assertEqual(meta.get('gstin'), self.real_gstin)

    def test_validation_success(self):
        """Test validate_file returns SUCCESS when GSTIN matches."""
        print("\n[Test] Validation Success")
        if not os.path.exists(self.sample_pdf): return

        is_valid, level, payload = FileValidationService.validate_file(
            self.sample_pdf, "gstr3b_m4", self.real_gstin, "2022-23", "B"
        )
        self.assertTrue(is_valid)
        self.assertEqual(level, "SUCCESS")

    def test_validation_mismatch_critical(self):
        """Test validate_file returns CRITICAL when GSTIN mismatches (Invariant)."""
        print("\n[Test] Mismatch is Critical")
        if not os.path.exists(self.sample_pdf): return

        is_valid, level, payload = FileValidationService.validate_file(
            self.sample_pdf, "gstr3b_m4", self.wrong_gstin, "2022-23", "B"
        )
        self.assertFalse(is_valid)
        self.assertEqual(level, "CRITICAL")
        self.assertIn("GSTIN Mismatch", payload)

    @patch('src.services.file_validation_service.FileValidationService._extract_pdf_metadata')
    def test_gstr3b_warning_fallback(self, mock_extract):
        """Test validate_file returns WARNING for GSTR-3B PDF when extraction fails."""
        print("\n[Test] GSTR-3B Warning Fallback")
        # Simulate extraction failure
        mock_extract.return_value = {'gstin': None, 'fy': '2022-23'}
        
        # Test with GSTR-3B key
        is_valid, level, payload = FileValidationService.validate_file(
            self.sample_pdf, "gstr3b_m4", self.real_gstin, "2022-23", "B"
        )
        # Should be False (handled by UI confirmation loop) but level WARNING
        self.assertFalse(is_valid) 
        self.assertEqual(level, "WARNING")
        # Verify payload structure
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]['warning_type'], "GSTIN_NOT_VERIFIED")
        self.assertEqual(payload[0]['gstin_verification'], "NOT_VERIFIED")

    @patch('src.services.file_validation_service.FileValidationService._extract_pdf_metadata')
    def test_gstr1_critical_failure(self, mock_extract):
        """Test validate_file returns CRITICAL for GSTR-1 PDF when extraction fails (Status Quo)."""
        print("\n[Test] GSTR-1 Critical Failure")
        mock_extract.return_value = {'gstin': None, 'fy': '2022-23'}
        
        # Test with GSTR-1 key
        is_valid, level, payload = FileValidationService.validate_file(
            self.sample_pdf, "gstr1_m4", self.real_gstin, "2022-23", "B"
        )
        self.assertFalse(is_valid) 
        self.assertEqual(level, "CRITICAL")
        self.assertIn("Could not extract GSTIN", payload)

if __name__ == '__main__':
    unittest.main()
