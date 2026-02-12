
import sys
import os
import unittest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.scn_generator import generate_intro_narrative

class TestSCNGroundsGenerator(unittest.TestCase):
    
    def test_basic_generation(self):
        data = {
            "version": 1,
            "type": "scrutiny",
            "manual_override": False,
            "data": {
                "financial_year": "2023-24",
                "docs_verified": ["GSTR-1", "GSTR-3B"],
                "asmt10_ref": {
                    "oc_no": "OC/123",
                    "date": "2024-01-01",
                    "officer_designation": "Superintendent",
                    "office_address": "Kochi"
                },
                "reply_ref": {
                    "received": False
                }
            }
        }
        
        narrative = generate_intro_narrative(data)
        self.assertIn("2023-24", narrative)
        self.assertIn("GSTR-1, GSTR-3B", narrative)
        self.assertIn("OC/123", narrative)
        self.assertIn("Superintendent", narrative)
        self.assertIn("no reply has been received", narrative)

    def test_reply_received(self):
        data = {
            "manual_override": False,
            "data": {
                "financial_year": "2023-24",
                "reply_ref": {
                    "received": True,
                    "date": "2024-02-01"
                }
            }
        }
        narrative = generate_intro_narrative(data)
        self.assertIn("reply dated <b>2024-02-01</b> have been received", narrative)

    def test_missing_data_placeholders(self):
        data = {
            "manual_override": False,
            "data": {}
        }
        narrative = generate_intro_narrative(data)
        self.assertIn("[FINANCIAL YEAR]", narrative)
        self.assertIn("[DOCUMENTS VERIFIED]", narrative)
        self.assertIn("[ASMT-10 OC NO]", narrative)

    def test_manual_override(self):
        data = {
            "manual_override": True,
            "manual_text": "Custom narrative text here."
        }
        narrative = generate_intro_narrative(data)
        self.assertEqual(narrative, "Custom narrative text here.")

if __name__ == '__main__':
    unittest.main()
