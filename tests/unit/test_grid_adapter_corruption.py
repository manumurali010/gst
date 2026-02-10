
import sys
import os
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ui.developer.grid_adapter import GridAdapter

class TestGridAdapterCorruption(unittest.TestCase):
    def test_pseudo_canonical_reentry(self):
        """
        Simulate the state where columns are strings (pseudo-canonical) 
        but rows are already normalized (dicts of dicts).
        """
        print("--- Test: Pseudo-Canonical Re-entry ---")
        
        # Input: corrupted schema often seen in "Zombie" snapshots or after naive JSON loads
        # Columns are strings (bad), Rows are canonical cells (good)
        bad_input = {
            "columns": ["col0"],
            "rows": [
                {
                    "col0": {"value": "Test Value", "type": "static"}
                }
            ]
        }
        
        # Action: Normalize
        normalized = GridAdapter.normalize_to_schema(bad_input)
        
        # Verification
        first_row = normalized['rows'][0]
        
        # Find the cell data (key might be regenerated)
        # Using values() to be key-agnostic for this test
        cell_data = list(first_row.values())[0]

        val = cell_data.get('value')
        print(f"Output Cell Value: {val}")
        
        # ASSERT: Value must NOT be a dict (which would mean double-wrapping)
        self.assertNotIsInstance(val, dict, "Value is nested dict! Double-wrapping occurred.")
        self.assertEqual(val, "Test Value", "Value mismatch.")

if __name__ == "__main__":
    unittest.main()
