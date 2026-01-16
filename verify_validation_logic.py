
import unittest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from src.services.file_validation_service import FileValidationService

class TestValidationLogic(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.case_gstin = "29ABCDE1234F1Z5"
        cls.case_fy = "2024-25"
        
        # Create Excel Sample 1: Valid
        cls.valid_xls = "valid_gstr2b.xlsx"
        with pd.ExcelWriter(cls.valid_xls) as writer:
            df = pd.DataFrame([["GSTIN: 29ABCDE1234F1Z5", "FY: 2024-25"]])
            df.to_excel(writer, sheet_name="READ ME", header=False, index=False)
            
        # Create Excel Sample 2: Missing ReadMe
        cls.missing_readme_xls = "bad_sheet_gstr2b.xlsx"
        with pd.ExcelWriter(cls.missing_readme_xls) as writer:
            df = pd.DataFrame([["Data"]])
            df.to_excel(writer, sheet_name="Sheet1", header=False, index=False)
            
        # Create Excel Sample 3: GSTIN Mismatch
        cls.mismatch_xls = "mismatch_gstr2b.xlsx"
        with pd.ExcelWriter(cls.mismatch_xls) as writer:
            df = pd.DataFrame([["GSTIN: 33AAAAA0000A1Z5", "FY: 2024-25"]])
            df.to_excel(writer, sheet_name="READ ME", header=False, index=False)
            
        # Create Dummy PDF for existence check
        with open("dummy.pdf", "wb") as f:
            f.write(b"%PDF-1.4 empty")

        # Create Excel Sample 4: GSTIN with Spaces (Normalization Check)
        cls.spaced_gstin_xls = "spaced_gstin_gstr2b.xlsx"
        with pd.ExcelWriter(cls.spaced_gstin_xls) as writer:
            # "GSTIN : 29 ABCDE..."
            df = pd.DataFrame([["GSTIN", "29 ABCDE 1234 F 1 Z 5"], ["FY", "2024-25"]])
            df.to_excel(writer, sheet_name="READ ME", header=False, index=False)
            
        # Create Excel Sample 5: Gap/Range Scan
        cls.gap_xls = "gap_gstr2b.xlsx"
        with pd.ExcelWriter(cls.gap_xls) as writer:
            # A1="GSTIN", B1="", C1="29...", D1="FY", E1="", F1="2024-25"
            df = pd.DataFrame([
                ["GSTIN", "", cls.case_gstin, "FY", "", cls.case_fy]
            ])
            df.to_excel(writer, sheet_name="READ ME", header=False, index=False)

    @classmethod
    def tearDownClass(cls):
        for f in [cls.valid_xls, cls.missing_readme_xls, cls.mismatch_xls, cls.spaced_gstin_xls, cls.gap_xls, "dummy.pdf"]:
            if os.path.exists(f): 
                os.remove(f)

    # --- Excel Tests (Strict) ---

    def test_excel_valid_strict(self):
        print("\n[TEST] Excel Valid Strict")
        res, level, msg = FileValidationService.validate_file(
            self.valid_xls, "gstr2b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}")
        self.assertTrue(res)
        self.assertEqual(level, "SUCCESS")
        
    def test_excel_spaced_gstin(self):
        print("\n[TEST] Excel Spaced GSTIN (Normalization)")
        res, level, msg = FileValidationService.validate_file(
            self.spaced_gstin_xls, "gstr2b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}")
        self.assertTrue(res)
        self.assertEqual(level, "SUCCESS")

    def test_excel_gap_scanning(self):
        print("\n[TEST] Excel Gap Scanning (Range Check)")
        res, level, msg = FileValidationService.validate_file(
            self.gap_xls, "gstr2b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}")
        self.assertTrue(res)
        self.assertEqual(level, "SUCCESS")

    def test_excel_missing_readme(self):
        print("\n[TEST] Excel Missing READ ME (Strict Block)")
        res, level, msg = FileValidationService.validate_file(
            self.missing_readme_xls, "gstr2b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Msg: {msg}")
        self.assertFalse(res)
        # Should now be specific error
        self.assertIn("Mandatory 'READ ME' sheet not found", str(msg))

    def test_excel_mismatch(self):
        print("\n[TEST] Excel Mismatch (Strict Block)")
        res, level, msg = FileValidationService.validate_file(
            self.mismatch_xls, "gstr2b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Msg: {msg}")
        self.assertFalse(res)
        self.assertEqual(level, "CRITICAL")
        self.assertIn("GSTIN Mismatch", str(msg))

    # --- Tax Liability Tests (Semi-Strict) ---
    
    def test_tax_liability_missing_meta(self):
        print("\n[TEST] Tax Liability Missing Meta (Block)")
        res, level, msg = FileValidationService.validate_file(
            self.missing_readme_xls, "tax_liability_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Msg: {msg}")
        self.assertFalse(res)
        self.assertEqual(level, "CRITICAL")

    # --- PDF Tests (Mocked) ---

    @patch('fitz.open')
    def test_pdf_valid(self, mock_open):
        print("\n[TEST] PDF Valid (GSTR-3B)")
        # Mock Valid PDF Content
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = f"GSTIN: {self.case_gstin}\nFinancial Year {self.case_fy}"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        res, level, msg = FileValidationService.validate_file(
            "dummy.pdf", "gstr3b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Msg: {msg}")
        self.assertTrue(res)

    @patch('fitz.open')
    def test_pdf_block_gstin_mismatch(self, mock_open):
        print("\n[TEST] PDF GSTIN Mismatch (Block)")
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = f"GSTIN: 99XXXXX9999X1Z1\nFinancial Year {self.case_fy}"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        res, level, msg = FileValidationService.validate_file(
            "dummy.pdf", "gstr3b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Msg: {msg}")
        self.assertFalse(res)
        self.assertEqual(level, "CRITICAL")

    @patch('fitz.open')
    def test_pdf_warn_fy_mismatch(self, mock_open):
        print("\n[TEST] PDF FY Mismatch (Warn)")
        mock_doc = MagicMock()
        mock_page = MagicMock()
        # Different FY
        mock_page.get_text.return_value = f"GSTIN: {self.case_gstin}\nFinancial Year 2017-18"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        res, level, payload = FileValidationService.validate_file(
            "dummy.pdf", "gstr3b_yearly", self.case_gstin, self.case_fy
        )
        print(f"Result: {res}, Level: {level}, Warns: {payload}")
        self.assertFalse(res)
        self.assertEqual(level, "WARNING") # Soft Warn
        self.assertEqual(payload[0]['warning_type'], "FY_MISMATCH")

if __name__ == '__main__':
    unittest.main()
