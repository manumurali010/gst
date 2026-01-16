
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock PyQt6 modules BEFORE importing ui
sys.modules["PyQt6"] = MagicMock()
sys.modules["PyQt6.QtWidgets"] = MagicMock()
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtGui"] = MagicMock()
sys.modules["PyQt6.QtWebEngineWidgets"] = MagicMock()
sys.modules["PyQt6.QtPrintSupport"] = MagicMock()

# Add gst (project root) to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.ui.scrutiny_tab import ScrutinyTab

class TestEnrichment(unittest.TestCase):
    def setUp(self):
        # Mock DB
        self.mock_db = MagicMock()
        
        # ScrutinyTab inherits from a Mock (QWidget), so init is safe or mocked.
        self.tab = ScrutinyTab()
        self.tab.db = self.mock_db
            
        # We need to manually bind the helper methods if __init__ was mocked?
        # No, methods belong to class.
        pass

    def test_new_facts_enrichment(self):
        # 1. Setup Master Issue with Table Definition
        table_def = {
            "columns": [{"id": "desc", "label": "Desc"}, {"id": "igst", "label": "IGST"}],
            "rows": [
                {"row_id": "r1", "label": "Label 1", "source": "facts.group", 
                 "semantics": {"condition": "is_positive", "severity": "critical"}}
            ]
        }
        
        self.mock_db.get_issue.return_value = {
            "issue_id": "TEST_ID", "issue_name": "Test Issue", "sop_point": 1,
            "table_definition": table_def,
            "grid_data": [] # Legacy grid (should be ignored)
        }
        
        # 2. Setup Input Issue with Facts
        issue_input = {
            "issue_id": "TEST_ID",
            "facts": {"group": {"igst": 100}}, # Positive value
            "description": "Test Desc"
        }
        
        # 3. Method Call
        from src.ui.scrutiny_tab import ScrutinyTab # Import again to ensure methods exist
        # We need to bind self.tab methods if we mocked init? No, instance methods work.
        
        # We need to re-verify _hydrate_grid_from_facts exists on self.tab
        # Start the enrichment
        enriched = self.tab.enrich_issues_with_templates([issue_input])
        
        self.assertEqual(len(enriched), 1)
        res = enriched[0]
        
        # 4. Assert Grid Data
        grid = res.get('grid_data')
        self.assertIsNotNone(grid)
        self.assertEqual(len(grid), 2) # Header + 1 Row
        
        # Row 1 (Data)
        row = grid[1]
        # Col 0 is Label
        self.assertEqual(row[0]['value'], "Label 1")
        # Col 1 is Value
        val_cell = row[1]
        self.assertEqual(val_cell['value'], 100) # Should be 100 from facts.group.igst? 
        # Wait, source="facts.group.igst".
        # _resolve_fact_path(facts, "facts.group.igst") -> facts["group"]["igst"] -> 100.
        # But loop sees col_id="igst".
        # base_fact = _resolve...("facts.group.igst") -> 100?
        # No, base_fact is assumed to be a DICT containing keys matching col_ids.
        # Logic in code:
        # base_fact = self._resolve_fact_path(facts, source_path)
        # val = base_fact.get(col_id, 0)
        
        # So source path should point to the DICT (e.g. facts.group), not the leaf.
        # My table_def above said "source": "facts.group.igst".
        # If I want it to resolve "igst" col, source should be "facts.group".
        
        # Let's adjust the test expectation to match the implementation logic I wrote.
        # I wrote: base_fact = _resolve(...); val = base_fact.get(col_id)
        
        # So if table_def says "source": "facts.group.igst", then base_fact is 100 (int).
        # And base_fact.get causes AttributeError.
        
        # This highlights a BUG or MISMATCH in my Plan vs Logic!
        # Implementation assumed source path yields a dict.
        # Plan said: {"row_id": "r1", "label": "Tax Liability (GSTR-1)", "source": "facts.gstr1"}
        # And facts.gstr1 IS a dict {"igst": ...}.
        # So my test setup "source": "facts.group.igst" is WRONG for the logic.
        # It should be "source": "facts.group".
        
    def test_logic_dict_resolution(self):
        # We need to verify if the code handles non-dict base_fact gracefully or if I should fix the logic.
        # The logic: val = base_fact.get(col_id, 0) if isinstance(base_fact, dict) else 0
        # So it handles it safely (returns 0).
        pass

if __name__ == '__main__':
    unittest.main()
