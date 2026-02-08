import unittest
from src.utils.date_utils import normalize_financial_year, get_fy_end_year, validate_gstin_format

class TestDateUtils(unittest.TestCase):
    
    def test_fy_normalization(self):
        # 2-digit end year
        self.assertEqual(normalize_financial_year("2022-23"), "2022-23")
        self.assertEqual(normalize_financial_year("22-23"), "2022-23")
        
        # 4-digit end year
        self.assertEqual(normalize_financial_year("2022-2023"), "2022-23")
        
        # Spaces
        self.assertEqual(normalize_financial_year(" 2022 - 23 "), "2022-23")
        
        # Edge/Error cases (The "202023" bug prevention)
        # If someone passed "2022-23" and we blindly add "20", we get "202023"
        # Our get_fy_end_year should handle it.
        self.assertEqual(get_fy_end_year("2022-23"), 2023)
        self.assertEqual(get_fy_end_year("22-23"), 2023)
        
    def test_gstin_validation(self):
        # Valid
        self.assertTrue(validate_gstin_format("29AAAAA0000A1Z5"))
        self.assertTrue(validate_gstin_format("27ABCDE1234F1Z1"))
        
        # Invalid
        self.assertFalse(validate_gstin_format("1234567890")) # Too short
        self.assertFalse(validate_gstin_format("29AAAAA0000A1X5")) # Invalid Z place (X instead of Z)

if __name__ == '__main__':
    unittest.main()
