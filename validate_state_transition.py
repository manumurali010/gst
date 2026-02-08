
import unittest

class MockScrutinyTab:
    def __init__(self):
        self.case_state = "INIT"
        self.file_paths = {}
        self.analyze_btn_enabled = False

    def _transition_case_state(self, new_state):
        current = self.case_state
        print(f"Transitioning: {current} -> {new_state}")
        
        valid_map = {
            'INIT': ['READY'],
            'READY': ['ANALYZED'],
            'ANALYZED': ['FINALIZED']
        }
        
        if new_state not in valid_map.get(current, []):
             raise RuntimeError(f"ILLEGAL STATE TRANSITION: {current} -> {new_state}")
                 
        self.case_state = new_state

    def handle_file_upload(self, key, file_path):
        # Simulation of upload logic
        self.file_paths[key] = file_path
        
        has_primary = 'tax_liability_yearly' in self.file_paths
        has_gstr9 = any(k.startswith('gstr9') for k in self.file_paths)
        
        if has_primary or has_gstr9:
            self.analyze_btn_enabled = True
            
            # THE FIX Logic
            if getattr(self, 'case_state', 'INIT') == 'INIT':
                self._transition_case_state('READY')

    def analyze_file(self):
        # Simulation of analyze logic calling transition
        self._transition_case_state("ANALYZED")

class TestStateMachine(unittest.TestCase):
    def test_upload_transitions_to_ready(self):
        tab = MockScrutinyTab()
        self.assertEqual(tab.case_state, "INIT")
        
        # Upload Primary File
        tab.handle_file_upload("tax_liability_yearly", "dummy.xlsx")
        
        self.assertEqual(tab.case_state, "READY", "State should be READY after primary upload")
        self.assertTrue(tab.analyze_btn_enabled)

    def test_full_flow_no_crash(self):
        tab = MockScrutinyTab()
        
        # 1. Upload
        tab.handle_file_upload("tax_liability_yearly", "dummy.xlsx")
        
        # 2. Analyze (Should work now because we are in READY)
        try:
            tab.analyze_file()
        except RuntimeError as e:
            self.fail(f"analyze_file failed with: {e}")
            
        self.assertEqual(tab.case_state, "ANALYZED")

    def test_crash_without_files(self):
        # Verification that it WOULD crash if we skipped READY
        tab = MockScrutinyTab()
        # Direct jump attempt (simulating old bug if we forced analysis)
        with self.assertRaises(RuntimeError):
            tab.analyze_file()

if __name__ == "__main__":
    unittest.main()
