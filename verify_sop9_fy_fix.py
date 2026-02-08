
import sys
import os
import unittest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP9FYNormalization(unittest.TestCase):
    
    def test_fy_normalization(self):
        parser = ScrutinyParser()
        
        # Case 1: Standard YYYY-YY
        res1 = parser._get_section_16_4_cutoff("2022-23")
        self.assertEqual(res1, datetime(2023, 11, 30))
        print("PASS: 2022-23 -> 2023")
        
        # Case 2: Full YYYY-YYYY (The Bug Fix)
        res2 = parser._get_section_16_4_cutoff("2022-2023")
        self.assertEqual(res2, datetime(2023, 11, 30))
        print("PASS: 2022-2023 -> 2023")
        
        # Case 3: Edge Case YYYY-YYYY numeric
        res3 = parser._get_section_16_4_cutoff("2023-2024")
        self.assertEqual(res3, datetime(2024, 11, 30))
        print("PASS: 2023-2024 -> 2024")

        # Case 4: Invalid Format (Safety)
        res4 = parser._get_section_16_4_cutoff("Invalid")
        self.assertIsNone(res4)
        print("PASS: Invalid -> None")

if __name__ == '__main__':
    unittest.main()
