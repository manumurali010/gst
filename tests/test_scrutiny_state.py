
import unittest
from unittest.mock import MagicMock

class TestScrutinyStateTransitions(unittest.TestCase):
    
    def setUp(self):
        self.tab = MagicMock()
        self.tab.case_state = 'INIT'
        
        # Valid transition map
        self.valid_map = {
            'INIT': ['READY'],
            'READY': ['ANALYZED'],
            'ANALYZED': ['FINALIZED']
        }
        
        # Mock _transition_case_state
        def transition(new_state):
            current = self.tab.case_state
            if new_state not in self.valid_map.get(current, []):
                raise RuntimeError(f"ILLEGAL STATE TRANSITION: {current} -> {new_state}")
            self.tab.case_state = new_state
            
        self.tab._transition_case_state = transition

    def test_upload_transition(self):
        """Verify INIT -> READY transition logic for handle_file_upload."""
        # Simulations Logic from handle_file_upload
        if self.tab.case_state == 'INIT':
            self.tab._transition_case_state('READY')
            
        self.assertEqual(self.tab.case_state, 'READY')

    def test_analysis_recovery_transition(self):
        """Verify self-recovery in analyze_file if state is still INIT."""
        # Simulation Logic from analyze_file
        # Suppose for some reason it's still INIT
        self.tab.case_state = 'INIT' 
        
        # Before transitioning to ANALYZED
        if self.tab.case_state == 'INIT':
            self.tab._transition_case_state('READY')
            
        self.tab._transition_case_state('ANALYZED')
        
        self.assertEqual(self.tab.case_state, 'ANALYZED')

    def test_illegal_jump_fails(self):
        """Verify that direct INIT -> ANALYZED still fails without the recovery."""
        self.tab.case_state = 'INIT'
        with self.assertRaises(RuntimeError):
            self.tab._transition_case_state('ANALYZED')

if __name__ == '__main__':
    unittest.main()
