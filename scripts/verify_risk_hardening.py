
import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestRiskHardening(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()
        # Mock Thresholds for safety
        self.parser.SOP_THRESHOLDS = {
             "DEFAULT": {"type": "flat", "tolerance": 10},
             "RCM_LIABILITY_ITC": {"type": "tiered", "alert_limit": 50},
             "RULE_42_43_VIOLATION": {"type": "flat", "tolerance": 5}
        }

    def test_determine_status(self):
        """Test the centralized status helper."""
        # Tolerance 10
        s, m = self.parser._determine_status(5, "DEFAULT")
        self.assertEqual(s, "pass")
        
        s, m = self.parser._determine_status(100, "DEFAULT")
        self.assertEqual(s, "fail")
        
        # Tiered (RCM)
        s, m = self.parser._determine_status(30, "RCM_LIABILITY_ITC")
        self.assertEqual(s, "alert") # < 50
        
        s, m = self.parser._determine_status(60, "RCM_LIABILITY_ITC")
        self.assertEqual(s, "fail")

    def test_safe_div(self):
        """Test safe division helper."""
        self.assertEqual(self.parser._safe_div(10, 2), 5.0)
        self.assertEqual(self.parser._safe_div(10, 0), 0.0)
        self.assertEqual(self.parser._safe_div(10, 0, default=-1), -1)

    def test_inject_meta(self):
        """Test metadata injection."""
        payload = {"status": "pass"}
        self.parser._inject_meta(payload, "Claimed", "Avail", "high", "Note")
        self.assertIn("meta", payload)
        self.assertEqual(payload["meta"]["confidence"], "high")
        self.assertEqual(payload["meta"]["source_claimed"], "Claimed")

    # --- SIMULATED SOP LOGIC CALLS ---
    # Since specific aggregation logic is hard to integration-test without files,
    # we verified the logic injection in previous steps. 
    # Here we simulate the return structure modification if feasible, 
    # or rely on the unit checks above for the HELPERS which are the core change.
    
    # We can invoke _determine_status via a mock? No need, tested above.
    
    # Let's verify SOP-10 Info Logic by simulating _parse_group_b
    def test_sop10_strict_info(self):
        # Mock a GSTR2B analyzer returning valid pass
        mock_2b = MagicMock()
        mock_2b.analyze_sop_10.return_value = {"status": "pass", "igst": 100}
        
        # Call with SOP-10 ID
        res = self.parser._parse_group_b_itc_summary(
            "dummy_path.xlsx", "Summary", "Cat", "Type", [], [], [], 
            "IMPORT_ITC_MISMATCH", gstr2b_analyzer=mock_2b
        )
        
        # Assert Info mandated
        self.assertEqual(res["status"], "info")
        self.assertIn("Verified against GSTR-2B only", res["status_msg"])
        self.assertIn("meta", res)

if __name__ == '__main__':
    unittest.main()
