
import sys
import os
import unittest
import copy

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ui.developer.grid_adapter import GridAdapter

class TestGridAdapter(unittest.TestCase):
    def setUp(self):
        # Sample Analytical Issue Schema (SOP 2 / RCM_LIABILITY_ITC)
        self.complex_schema = {
            "columns": [
                {"id": "description", "label": "Description", "type": "text"},
                {"id": "igst", "label": "IGST", "type": "currency"},
                {"id": "cgst", "label": "CGST", "type": "currency"}
            ],
            "rows": [
                {
                    "id": "r1",
                    "description": {"value": "RCM Liability", "type": "static"},
                    "igst": {"value": 100, "type": "input", "var": "v1"},
                    "cgst": {"value": 100, "type": "input", "var": "v2"}
                },
                {
                    "id": "r2",
                    "description": {"value": "ITC Claimed", "type": "static"},
                    "igst": {"value": 80, "type": "input"},
                    "cgst": {"value": 80, "type": "input"}
                }
            ],
            "metadata": {"version": "2.0", "locked": True}
        }

    def test_hydration_structure(self):
        """Verify hydration creates correct UI structure"""
        ui_data = GridAdapter.hydrate_from_grid_schema(self.complex_schema)
        
        self.assertEqual(ui_data['rows'], 3) # Header + 2 Rows
        self.assertEqual(ui_data['cols'], 3)
        self.assertEqual(len(ui_data['cells']), 3)
        
        # Check Header Row
        self.assertEqual(ui_data['cells'][0], ["Description", "IGST", "CGST"])
        
        # Check Data Row 1
        # Adapter converts numeric 100 to string "100"
        self.assertEqual(ui_data['cells'][1][0], "RCM Liability")
        self.assertEqual(ui_data['cells'][1][1], "100") 

    def test_metadata_preservation(self):
        """Verify _meta field stores original schema exactly"""
        ui_data = GridAdapter.hydrate_from_grid_schema(self.complex_schema)
        
        self.assertIn('_meta', ui_data)
        self.assertEqual(ui_data['_meta'], self.complex_schema)
        
        # Ensure deep copy (mutation safeguard)
        ui_data['_meta']['metadata']['locked'] = False
        self.assertTrue(self.complex_schema['metadata']['locked'])

    def test_read_only_serialization(self):
        """Verify serialization ignores UI changes and returns _meta"""
        ui_data = GridAdapter.hydrate_from_grid_schema(self.complex_schema)
        
        # Simulate UI Edit
        ui_data['cells'][1][1] = "99999" # User edited the cell
        
        # Serialize
        serialized = GridAdapter.serialize_to_grid_schema(ui_data)
        
        # Assert: Should match ORIGINAL schema, not the edited UI
        self.assertEqual(serialized, self.complex_schema)
        self.assertEqual(serialized['rows'][0]['igst']['value'], 100)
        
    def test_empty_hydration(self):
        """Verify empty input handling"""
        ui_data = GridAdapter.hydrate_from_grid_schema({})
        self.assertEqual(ui_data['rows'], 4) # Default
        self.assertEqual(ui_data['_meta'], {})

if __name__ == "__main__":
    unittest.main()
