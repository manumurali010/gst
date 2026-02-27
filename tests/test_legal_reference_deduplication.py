import sys
import unittest
import os
import re

# Simulate path environment
sys.path.append(os.path.abspath(os.curdir))

# Mock/Import from the file directly if needed, but here we'll define a testable class 
# to ensure the logic matches what was just written.
from src.ui.proceedings_workspace import LegalReference

class TestLegalReferenceDeduplication(unittest.TestCase):
    def test_basic_deduplication(self):
        r1 = LegalReference("Section 7")
        r2 = LegalReference("Sec 7")
        r3 = LegalReference("u/s 7")
        
        self.assertEqual(r1.canonical_id, r2.canonical_id)
        self.assertEqual(r2.canonical_id, r3.canonical_id)
        self.assertEqual(r1.canonical, "Section 7")

    def test_minor_normalization(self):
        # Spaces should not affect canonical_id but can remain in canonical display
        r1 = LegalReference("Section 7 (1)(a)")
        r2 = LegalReference("Section 7(1) (a)")
        
        self.assertEqual(r1.canonical_id, r2.canonical_id)
        # Display might preserve formatting of the first one found or just be normalized
        self.assertEqual(r1.canonical_id, "Section:Unknown:7:(1)(a)")

    def test_act_isolation(self):
        # References from different acts should not deduplicate
        r1 = LegalReference("Section 7 of CGST Act")
        r2 = LegalReference("Section 7 of SGST Act")
        
        self.assertNotEqual(r1.canonical_id, r2.canonical_id)
        self.assertEqual(r1.act, "CGST Act")
        self.assertEqual(r2.act, "SGST Act")

    def test_unknown_act_consistency(self):
        # If no act is mentioned, they should deduplicate together as "Unknown"
        r1 = LegalReference("Section 16")
        r2 = LegalReference("Sec 16")
        
        self.assertEqual(r1.act, "Unknown")
        self.assertEqual(r1.canonical_id, r2.canonical_id)

    def test_logical_sorting(self):
        refs = [
            LegalReference("Rule 117"),
            LegalReference("Section 7"),
            LegalReference("Section 16"),
            LegalReference("Section 74"),
            LegalReference("Something Else")
        ]
        # Sort by __lt__
        refs.sort()
        
        canonicals = [r.canonical for r in refs]
        expected = ["Section 7", "Section 16", "Section 74", "Rule 117", "Something Else"]
        self.assertEqual(canonicals, expected)

if __name__ == "__main__":
    unittest.main()
