
import sys
import unittest
from unittest.mock import MagicMock

# Mocking necessary modules before import
sys.modules['src.services.db_manager'] = MagicMock()
sys.modules['src.utils.db_schemas'] = MagicMock()
sys.modules['src.utils.pdf_parsers'] = MagicMock()
sys.modules['src.services.gstr_2b_analyzer'] = MagicMock()
sys.modules['src.config'] = MagicMock()

# Import the class under test
# We need to bypass some imports inside scrutiny_parser
from src.services.scrutiny_parser import ScrutinyParser

class TestRCMLogic(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()
        
        # Construct Dummy Data
        # Scenario: RCM Liability 100, Cash Paid 80, 2B Inward 120, 2B CN 10
        self.data = {
            "3b_3_1_d": {"igst": 100, "cgst": 100, "sgst": 100, "cess": 0},
            "3b_4a_2_3": {"igst": 90, "cgst": 90, "sgst": 90, "cess": 0},
            "3b_6_1_cash": {"igst": 80, "cgst": 80, "sgst": 80, "cess": 0},
            "2b_rcm_inward": {"igst": 120, "cgst": 120, "sgst": 120, "cess": 0},
            "2b_rcm_cn": {"igst": 10, "cgst": 10, "sgst": 10, "cess": 0},
            "flags": {
                "3b_found": True,
                "3b_6_1_found": True,
                "2b_found": True
            }
        }
        
    def test_sop_13_structure(self):
        print("\nTesting SOP 13 (RCM Liability vs Cash)...")
        res = self.parser._parse_sop_13(self.data)
        rows = res['summary_table']['rows']
        self.assertEqual(len(rows), 4, "SOP 13 should have 4 rows")
        print("SOP 13 Passed")

    def test_sop_14_structure(self):
        print("\nTesting SOP 14 (RCM ITC vs Cash)...")
        res = self.parser._parse_sop_14(self.data)
        rows = res['summary_table']['rows']
        self.assertEqual(len(rows), 4, "SOP 14 should have 4 rows")
        print("SOP 14 Passed")

    def test_sop_15_structure(self):
        print("\nTesting SOP 15 (RCM ITC vs 2B)...")
        res = self.parser._parse_sop_15(self.data)
        rows = res['summary_table']['rows']
        self.assertEqual(len(rows), 5, "SOP 15 should have 5 rows")
        
        # Check specific row labels
        labels = [r['col0']['value'] for r in rows]
        print(f"SOP 15 Labels: {labels}")
        self.assertIn("Inward Supplies Liable for Reverse Charge as per GSTR-2B", labels)
        self.assertIn("ITC pertaining to credit notes (Reverse Charge)", labels)
        print("SOP 15 Passed")
        
    def test_sop_16_structure(self):
        print("\nTesting SOP 16 (RCM Cash vs 2B)...")
        res = self.parser._parse_sop_16(self.data)
        rows = res['summary_table']['rows']
        self.assertEqual(len(rows), 5, "SOP 16 should have 5 rows")
        
        # Check value calculation for SOP 16
        # Net 2B = 120 - 10 = 110
        # Cash = 80
        # Diff = 110 - 80 = 30
        # Shortfall = 30
        
        # Row 4 is Difference (Index 3)
        diff_row = rows[3]
        shortfall_row = rows[4]
        
        self.assertEqual(diff_row['col1']['value'], 30, "Difference Check Failed for IGST") # IGST
        self.assertEqual(shortfall_row['col1']['value'], 30, "Shortfall Check Failed for IGST")
        
        print("SOP 16 Passed")

if __name__ == '__main__':
    unittest.main()
