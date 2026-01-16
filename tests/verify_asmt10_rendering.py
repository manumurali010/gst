import sys
import os
import unittest
from unittest.mock import MagicMock

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.asmt10_generator import ASMT10Generator

class TestASMT10TableRendering(unittest.TestCase):
    def test_canonical_grid_rendering(self):
        """Verify that component dicts are unwrapped and numbers formatted."""
        issue = {
            "template_type": "summary_3x4",
            "summary_table": {
                "columns": [
                    {"id": "col0", "label": "Description"},
                    {"id": "col1", "label": "Amount", "type": "float"}
                ],
                "rows": [
                    {
                        "col0": {"value": "Test Item", "type": "string"},
                        "col1": {"value": 123456.78, "type": "float", "style": "red_bold"}
                    }
                ]
            }
        }

        html = ASMT10Generator.generate_issue_table_html(issue)
        
        # 1. Check for Dict Artifacts
        self.assertNotIn("{'value':", html)
        self.assertNotIn("123456.78", html) # Should be formatted
        
        # 2. Check Formatting (Indian Format + No Decimals)
        # 1,23,457 (Rounded)
        self.assertIn("1,23,457", html)
        self.assertIn("text-align: right", html)
        self.assertIn("color: red", html)
        
    def test_hard_guard_missing_data(self):
        """Verify that missing table data triggers explicit INFO block."""
        issue = {
            "template_type": "unknown",
            # No rows, no grid_data, no summary_table
        }
        
        html = ASMT10Generator.generate_issue_table_html(issue)
        
        self.assertIn("Detailed calculation data is not available", html)
        self.assertIn("Source: Legacy Data or Missing Analysis Payload", html)
        
    def test_legacy_list_of_dicts(self):
        """Verify backward compatibility for simple dict rows (if any still exist)."""
        issue = {
            "grid_data": [
                 {"gstin": "29ABCDE1234F1Z5", "val": 500}
            ]
        }
        # My implementation handles "Scenario B: No Columns defined (Legacy List of Lists)"
        # where iter_items = row.values()
        
        html = ASMT10Generator.generate_issue_table_html(issue)
        self.assertIn("29ABCDE1234F1Z5", html)
        self.assertIn("500", html)

if __name__ == '__main__':
    unittest.main()
