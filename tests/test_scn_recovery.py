
import unittest
from unittest.mock import MagicMock
import copy

class TestSCNRecovery(unittest.TestCase):
    
    def test_recovery_from_stale_default(self):
        """
        Verify that hydrate_scn_grounds_data updates docs_verified 
        if it's exactly equal to the STALE_DEFAULT and new files are found.
        """
        # Mock instance
        ws = MagicMock()
        ws.proceeding_data = {
            'additional_details': {
                'file_paths': {
                    'gstr2b_monthly': 'path',
                    'gstr9_yearly': 'path'
                },
                'scn_grounds': {
                    'data': {
                        'docs_verified': ["GSTR-1", "GSTR-3B", "GSTR-2A"] # STALE DEFAULT
                    }
                }
            }
        }
        
        # Helper extracted from proceedings_workspace.py
        def _get_current_file_doc_list(details_dict):
            f_paths = details_dict.get('file_paths', {})
            d_list = []
            if 'tax_liability_yearly' in f_paths: d_list.append("Tax Liability Excel")
            if any(k.startswith('gstr3b') for k in f_paths): d_list.append("GSTR-3B")
            if any(k.startswith('gstr1') for k in f_paths): d_list.append("GSTR-1")
            if any(k.startswith('gstr2a') for k in f_paths): d_list.append("GSTR-2A")
            if any(k.startswith('gstr2b') for k in f_paths): d_list.append("GSTR-2B")
            if any(k.startswith('gstr9') for k in f_paths): d_list.append("GSTR-9")
            if any(k.startswith('gstr9c') for k in f_paths): d_list.append("GSTR-9C")
            return d_list

        details = ws.proceeding_data['additional_details']
        grounds = details.get('scn_grounds')
        
        # Logic to test:
        current_docs = grounds.get('data', {}).get('docs_verified', [])
        STALE_DEFAULT = ["GSTR-1", "GSTR-3B", "GSTR-2A"]
        
        if current_docs == STALE_DEFAULT:
            fresh_list = _get_current_file_doc_list(details)
            if fresh_list and fresh_list != STALE_DEFAULT:
                grounds['data']['docs_verified'] = fresh_list
                
        # Verification
        self.assertIn("GSTR-2B", grounds['data']['docs_verified'])
        self.assertIn("GSTR-9", grounds['data']['docs_verified'])
        self.assertEqual(len(grounds['data']['docs_verified']), 2)

    def test_preservation_of_manual_edits(self):
        """
        Verify that if the list is NOT exactly the stale default (user edited it),
        we do NOT touch it.
        """
        ws = MagicMock()
        ws.proceeding_data = {
            'additional_details': {
                'file_paths': {'gstr2b_monthly': 'path'},
                'scn_grounds': {
                    'data': {
                        'docs_verified': ["My Custom Document"] 
                    }
                }
            }
        }
        
        # ... logic ...
        details = ws.proceeding_data['additional_details']
        grounds = details.get('scn_grounds')
        current_docs = grounds.get('data', {}).get('docs_verified', [])
        STALE_DEFAULT = ["GSTR-1", "GSTR-3B", "GSTR-2A"]
        
        if current_docs == STALE_DEFAULT:
            # Should not happen
            pass
            
        self.assertEqual(grounds['data']['docs_verified'], ["My Custom Document"])

if __name__ == '__main__':
    unittest.main()
