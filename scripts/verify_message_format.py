
import unittest
import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestMessageFormat(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()
    
    def test_fail_format(self):
        """FAIL/ALERT must be strictly 'Rs. <Amount>'"""
        # Test Case 1: Fail with amount
        msg = self.parser._format_status_msg("fail", 123456)
        print(f"FAIL Message: '{msg}'")
        self.assertTrue(msg.startswith("Rs. "))
        self.assertRegex(msg, r"^Rs\. [\d,]+$") # Only Rs., digits, commas
        self.assertNotIn("Shortfall", msg)
        
        # Test Case 2: Alert with amount
        msg = self.parser._format_status_msg("alert", 500)
        print(f"ALERT Message: '{msg}'")
        self.assertTrue(msg.startswith("Rs. "))
        self.assertRegex(msg, r"^Rs\. [\d,]+$")
        
    def test_info_format(self):
        """INFO must be strictly mapped from REASON_MAP"""
        # Test 1: Valid Key
        msg = self.parser._format_status_msg("info", 0, "GSTR3B_MISSING")
        print(f"INFO (Valid Key): '{msg}'")
        self.assertEqual(msg, "GSTR-3B PDF Missing")
        
        # Test 2: Invalid Key (Hard Gate)
        msg = self.parser._format_status_msg("info", 0, "RANDOM_DEBUG_STRING")
        print(f"INFO (Invalid Key): '{msg}'")
        self.assertEqual(msg, "Data Not Available")
        
        # Test 3: None Key
        msg = self.parser._format_status_msg("info", 0, None)
        self.assertEqual(msg, "Data Not Available")

    def test_pass_format(self):
        """PASS must return empty string (UI overrides)"""
        msg = self.parser._format_status_msg("pass", 0)
        print(f"PASS Message: '{msg}'")
        self.assertEqual(msg, "")

if __name__ == '__main__':
    unittest.main()
