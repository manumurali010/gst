
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ui.issue_card import IssueCard

app = QApplication(sys.argv)

class TestIssueCardSafety(unittest.TestCase):

    def test_origin_read_only_contract(self):
        """
        Adjudication Safety Contract:
        - Scrutiny-origin issues MUST BE Read-Only.
        - Manual/SCN-origin issues MUST BE Editable.
        """
        import inspect
        print("DEBUG: IssueCard.set_read_only source:")
        try:
            print(inspect.getsource(IssueCard.set_read_only))
        except Exception as e:
            print(f"Failed to get source: {e}")
        
        # 1. Test Scrutiny Origin in SCN Mode (Split-Lock)
        template_scrutiny = {
            'issue_id': 'SOP-01',
            'issue_name': 'Scrutiny Issue',
            'variables': {'tax_igst': 100}
        }
        data_scrutiny = {'origin': 'ASMT10'}
        
        # 1. Test Scrutiny Origin in SCN Mode (Split-Lock)
        template_scrutiny = {
            'issue_id': 'SOP-01',
            'issue_name': 'Scrutiny Issue',
            'variables': {'tax_igst': 100}
        }
        data_scrutiny = {'origin': 'ASMT10'}
        
        # Manually verify Constructor Logic using Factory Token
        card_scrutiny = IssueCard(
            token=IssueCard._FACTORY_TOKEN,
            template=template_scrutiny, 
            data=data_scrutiny, 
            mode="SCN",
            lifecycle_stage="NEW_ISSUE" 
        )
        
        # Phase 5B.2 Contract:
        # Title: Locked (Identity)
        # Structure: Locked (Facts)
        # Content: Unlocked (Allegations)
        
        print("\n--- Testing Scrutiny SCN Mode (Split-Lock) ---")
        self.assertFalse(card_scrutiny.is_read_only, "Scrutiny-SCN should be Interactive")
        self.assertTrue(card_scrutiny.lock_title, "Title MUST be Locked")
        self.assertTrue(card_scrutiny.lock_structure, "Structure MUST be Locked")
        self.assertFalse(card_scrutiny.lock_content, "Content MUST be Editable")
        
        # Verify set_read_only(False) doesn't break locks
        card_scrutiny.set_read_only(False)
        self.assertTrue(card_scrutiny.lock_title, "Title should remain Locked after set_read_only(False)")
        
        # 2. Test Manual Origin (Fully Open)
        template_manual = {
            'issue_id': 'MANUAL-01', 
            'issue_name': 'Manual Issue',
            'variables': {}
        }
        data_manual = {'origin': 'MANUAL_SOP'}
        card_manual = IssueCard(
            token=IssueCard._FACTORY_TOKEN,
            template=template_manual, 
            data=data_manual, 
            mode="SCN",
            lifecycle_stage="NEW_ISSUE"
        )
        
        print("\n--- Testing Manual SCN Mode (Fully Open) ---")
        self.assertFalse(card_manual.is_read_only, "Manual should be Interactive")
        self.assertFalse(card_manual.lock_title, "Title should be Editable")
        self.assertFalse(card_manual.lock_structure, "Structure should be Editable")
        self.assertFalse(card_manual.lock_content, "Content should be Editable")
        
        # 3. Test Scrutiny Origin in VIEW Mode (Fully Locked)
        data_scrutiny_view = {'origin': 'SCRUTINY'}
        card_view = IssueCard(
            token=IssueCard._FACTORY_TOKEN,
            template=template_scrutiny, 
            data=data_scrutiny_view, 
            mode="VIEW",
            lifecycle_stage="NEW_ISSUE"
        )
        
        print("\n--- Testing Scrutiny VIEW Mode (Fully Locked) ---", flush=True)
        self.assertTrue(card_view.is_read_only, "View Mode must be fully Read-Only")
        self.assertTrue(card_view.lock_title)
        self.assertTrue(card_view.lock_structure)
        self.assertTrue(card_view.lock_content)
        
        # Attempt toggle check
        print("CALLING set_read_only(False)...", flush=True)
        card_view.set_read_only(False)
        print("CALLED set_read_only(False).", flush=True)
        
        # Re-check policy application
        # Origin=SCRUTINY, Mode=VIEW -> Should revert to Locked
        self.assertTrue(card_view.is_read_only, "Security Policy should prevent unlocking Scrutiny View")
        self.assertTrue(card_view.lock_title)


if __name__ == '__main__':
    # Manual execution for debug visibility
    t = TestIssueCardSafety()
    try:
        t.test_origin_read_only_contract()
        print("MANUAL RUN: SUCCESS")
    except Exception as e:
        print(f"MANUAL RUN: FAILED: {e}")
        import traceback
        traceback.print_exc()

    # Standard runner
    unittest.main()

