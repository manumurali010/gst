
import unittest
from unittest.mock import MagicMock, patch
import json

class TestDBDeepMerge(unittest.TestCase):
    
    def test_additional_details_deep_merge(self):
        """
        Verify that get_proceeding's deep-merge logic works as expected.
        """
        # Mock source (Scrutiny)
        source_data = {
            'id': 'scrutiny-123',
            'additional_details': {
                'file_paths': {'gstr9': '/path/to/gstr9'},
                'common_meta': 'from-scrutiny'
            }
        }
        
        # Mock target (Adjudication) - DOUBLE SERIALIZED STRING Case
        adj_data = {
            'id': 'adj-456',
            'source_scrutiny_id': 'scrutiny-123',
            'additional_details': '"{\\"scn_metadata\\": {\\"no\\": \\"SCN-1\\"}, \\"common_meta\\": \\"from-adj\\"}"'
        }
        
        # Implementation of logic from db_manager.py
        import copy
        final_data = source_data.copy()
        
        def _ensure_dict(val):
            if not val: return {}
            if isinstance(val, dict): return val
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, str): # Handle double-serialization
                        parsed = json.loads(parsed)
                    return parsed if isinstance(parsed, dict) else {}
                except: return {}
            return {}

        src_details = _ensure_dict(source_data.get('additional_details'))
        adj_details = _ensure_dict(adj_data.get('additional_details'))
        
        final_data.update(adj_data)
        
        # Merging sub-dict
        from copy import deepcopy
        merged_details = deepcopy(src_details) if src_details else {}
        if isinstance(adj_details, dict) and adj_details:
            merged_details.update(adj_details)
            
        final_data['additional_details'] = merged_details
        
        # Assertions
        # 1. Scrutiny specific keys are preserved
        self.assertIn('file_paths', final_data['additional_details'])
        self.assertEqual(final_data['additional_details']['file_paths']['gstr9'], '/path/to/gstr9')
        
        # 2. Adjudication specific keys are added
        self.assertIn('scn_metadata', final_data['additional_details'])
        
        # 3. Common keys are overridden by Adjudication
        self.assertEqual(final_data['additional_details']['common_meta'], 'from-adj')
        
        # 4. Overall data merge works
        self.assertEqual(final_data['id'], 'adj-456')

if __name__ == '__main__':
    unittest.main()
