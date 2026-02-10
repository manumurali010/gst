
import sys
import os
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ui.developer.grid_adapter import GridAdapter

class TestGridAdapterStrictness(unittest.TestCase):
    def test_fail_fast_on_string_columns(self):
        """
        Verify that GridAdapter raises ValueError when encountering string columns,
        forcing upstream producers to be canonical.
        """
        print("--- Test: GridAdapter Strictness (Fail-Fast) ---")
        
        # Bad Input: String columns
        bad_input = {
            "columns": ["Tax", "Penalty"],
            "rows": []
        }
        
        # Action: Normalize (Should Raise)
        with self.assertRaises(ValueError) as cm:
            GridAdapter.normalize_to_schema(bad_input)
            
        print(f"Caught Expected Error: {cm.exception}")
        self.assertIn("CRITICAL: Detected pseudo-canonical data", str(cm.exception))

    def test_canonical_passthrough(self):
        """
        Verify valid data passes through.
        """
        good_input = {
            "columns": [{"id": "c1", "label": "Tax"}],
            "rows": []
        }
        result = GridAdapter.normalize_to_schema(good_input)
        self.assertEqual(result, good_input)

if __name__ == "__main__":
    unittest.main()
