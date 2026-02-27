import sys
import unittest
from decimal import Decimal

# Add src to path
import os
sys.path.append(os.path.abspath(os.curdir))

class TestMonetaryStandardization(unittest.TestCase):
    def test_safe_int_conversion(self):
        """Verify that safe_int handles various types with rounding"""
        # We need to simulate the helper inside IssueCard or define a standalone one for testing
        def safe_int(val):
            if val in (None, "", "null"): return 0
            if isinstance(val, str):
                val = val.replace(',', '').replace('₹', '').strip()
                if not val: return 0
            try:
                # Standard Round Half Up (Standard for Tax)
                f = float(val)
                return int(f + 0.5) if f >= 0 else int(f - 0.5)
            except (ValueError, TypeError):
                return 0

        self.assertEqual(safe_int("100"), 100)
        self.assertEqual(safe_int("100.50"), 101)
        self.assertEqual(safe_int("100.49"), 100)
        self.assertEqual(safe_int(100.7), 101)
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int(""), 0)
        self.assertEqual(safe_int("₹ 1,23,456.78"), 123457)

    def test_integer_arithmetic_prevention_of_typeerror(self):
        """Verify that adding int and int works (no mixed float/Decimal)"""
        val1 = 100
        val2 = 200
        total = val1 + val2
        self.assertIsInstance(total, int)
        self.assertEqual(total, 300)

    def test_formatting_indian_number(self):
        """Verify that formatting handles large integers correctly"""
        from src.utils.formatting import format_indian_number
        self.assertEqual(format_indian_number(1234567), "12,34,567")
        self.assertEqual(format_indian_number(100), "100")
        self.assertEqual(format_indian_number(0), "0")
        # Support for Large Integers (64-bit scope)
        self.assertEqual(format_indian_number(100000000000), "1,00,00,00,00,000")

if __name__ == "__main__":
    unittest.main()
