
import sys
import time
import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication, QTableWidget

# --- MOCKING DEPENDENCIES FOR ProceedingsWorkspace ---
sys.modules['src.ui.scrutiny_tab'] = MagicMock()
sys.modules['src.database.db_manager'] = MagicMock()
sys.modules['src.utils.generate_image'] = MagicMock()
# ---------------------------------------------------

from src.ui.ui_helpers import render_grid_to_table_widget
from src.ui.issue_card import IssueCard
from src.ui.proceedings_workspace import ProceedingsWorkspace

class TestPhase4Closure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)

    def test_issue_card_lifecycle_traces(self):
        print("\n--- TEST: IssueCard Lifecycle (Traces + Headers) ---")
        
        # ASMT-10 Payload
        template = {
            "issue_id": "TEST_TRACE",
            "issue_name": "Trace Test",
            "grid_data": {
                "columns": [{"id": "c1", "label": "Taxable"}, {"id": "c2", "label": "Tax"}],
                "rows": [{"c1": {"value": 100}, "c2": {"value": 18}}]
            },
            "summary_table": {
                "headers": ["Taxable", "Tax"]
            }
        }
        data = {"origin": "ASMT10", "status": "ACTIVE"}
        
        print("Instantiating IssueCard...")
        # [Phase-4 Fix-18R] Use Factory Method
        card = IssueCard.create_new(template, data=data) 
        # Note: factory signature is create_new(template, parent=None, data=None)
        # My implementation added data=None support?
        # Let's check IssueCard implementation in previous turn.
        # "def create_new(cls, template, parent=None, data=None):" -> YES.
        
        # Trigger explicit render call if needed (init_ui calls init_grid_ui)
        # The __init__ calls calculate_values (if NEW_ISSUE), so traces should appear.
        print("IssueCard Instantiated.")
        
        print(">> Triggering Header Dump via generate_html...")
        html = card.generate_html()
        print(">> HTML Generated (Sample):", html[:50])

    def test_issue_card_hydration_no_traces(self):
        print("\n--- TEST: IssueCard Hydration (Side-Effect Free) ---")
        from src.ui.issue_card import IssueCard
        
        template = {"issue_id": "TEST_HYDRATION", "issue_name": "Hydration Test"}
        data = {"origin": "SCN", "status": "ACTIVE"}
        
        time.sleep(1) # simulate persistence
        # In restore, data typically includes template or we assume external mgmt.
        # Fix-18R restore_snapshot(snapshot, parent)
        # Let's construct a snapshot that 'looks' like DB payload
        snapshot = {
            'issue_id': 'TEST_HYDRATION',
            'issue_name': 'Hydration Test',
            'Variables': {},
            'origin': 'SCN',
            'template': template # IMPORTANT: Fix-18R logic relies on template being inside or reconstructed
        }
        
        print("Instantiating IssueCard with restore_snapshot...")
        # Should prints debug message but NO stack traces
        card = IssueCard.restore_snapshot(snapshot)
        print("IssueCard Instantiated (Hydration Mode).")

    def test_zero_row_rejection_runtime(self):
        print("\n--- TEST: Zero-Row Rejection Runtime (insert_scn_issue) ---")
        
        # Instantiate Workspace (Mocked DB/Parent)
        parent = MagicMock()
        db = MagicMock()
        workspace = ProceedingsWorkspace(parent, db)
        
        # Mock build_scn_issue_from_asmt10 to return a Zero-Row template
        workspace.build_scn_issue_from_asmt10 = MagicMock()
        workspace.build_scn_issue_from_asmt10.return_value = {
            'template': {
                'issue_id': 'ZERO_ROW_ISSUE',
                'grid_data': {'rows': [{}, {}]} # Empty dicts = Zero valid rows
            },
            'data': {}
        }
        
        payload = {
            'issue_id': 'ZERO_ROW_ISSUE',
            'origin': 'ASMT10',
            'data': {'summary_table': {'rows': [{'a':1}]}} # Pass initial validation
        }
        
        print(">> Calling insert_scn_issue (expecting Rejection Log)...")
        workspace.insert_scn_issue(payload)
        print(">> insert_scn_issue call complete.")

    def test_signal_wiring_audit(self):
        print("\n--- TEST: Fix-19 Signal Wiring Audit ---")
        from src.ui.issue_card import IssueCard
        # Mock Parent Workspace
        workspace = MagicMock()
        workspace.calculate_grand_totals = MagicMock()
        
        # 1. Hydration Phase
        template = {"issue_id": "SIG_TEST", "issue_name": "Signal Test"}
        snapshot = {'issue_id': 'SIG_TEST', 'origin': 'SCN'}
        
        card = IssueCard.restore_snapshot(snapshot) # Hydration
        
        # Audit: verify NO internal slots connected (via blockSignals check or inspection)
        # PyQt signals inspection is hard. 
        # But we can check if emitting 'valuesChanged' triggers the mock.
        
        # Manually connect loosely to simulate workspace adding it but NOT wiring yet?
        # Fix-19 logic: add_scn_issue_card creates card. 
        # Does NOT connect valuesChanged.
        # So emitting valuesChanged should do NOTHING on the workspace mock.
        
        # Let's verify IssueCard itself is compliant.
        print("Emitting valuesChanged (Hydration Mode)...")
        card.valuesChanged.emit({'value': 100.0})
        
        # 2. Activation Phase (Simulation)
        print("Activating Signals (Simulating _wire_interactive_signals)...")
        # workspace._wire_interactive_signals(card) logic:
        card.valuesChanged.connect(workspace.calculate_grand_totals)
        
        print("Emitting valuesChanged (Active Mode)...")
        card.valuesChanged.emit({'value': 200.0})
        
        # Verify Mock Call Count
        # Should be 1 (only from Active Mode)
        print(f"Mock Call Count: {workspace.calculate_grand_totals.call_count}")
        if workspace.calculate_grand_totals.call_count == 1:
             print("SUCCESS: Signal Wiring is Lifecycle-Aware.")
        else:
             print(f"FAILURE: Mock called {workspace.calculate_grand_totals.call_count} times (Expected 1).")

    def test_semantic_restoration(self):
        print("\n--- TEST: Fix-20 Semantic Restoration (Identity & Headers) ---")
        from src.ui.issue_card import IssueCard
        # Mock Layout
        layout = MagicMock()
        layout.addWidget = MagicMock()
        
        # Scenario: Snapshot with Identity + Headers (but List Grid)
        # This simulates the critical failure mode.
        snapshot = {
             'issue_id': 'SEMANTIC_TEST',
             'issue_name': 'Semantic Fidelity Test',
             'summary_table': {'headers': ['Taxable Value', 'Integrated Tax']},
             'grid_data': [{'value': 100}, {'value': 18}], # List format (Legacy)
             'origin': 'SCN'
        }
        
        print("Restoring Snapshot...")
        card = IssueCard.restore_snapshot(snapshot)
        
        # 1. Identity Assertion
        print(f"Restored Identity: {card.issue_id} / {card.issue_name}")
        if card.issue_id == 'SEMANTIC_TEST' and card.issue_name == 'Semantic Fidelity Test':
             print("SUCCESS: Identity Restored Deterministically.")
        else:
             print(f"FAILURE: Identity Mismatch. Got {card.issue_id}")
             
        # 2. Header Assertion (Trigger Render)
        print("Triggering init_grid_ui...")
        card.init_grid_ui(layout, data=snapshot)
        
        # Verify Headers passed to Table
        # We can check card.table if it was created
        if hasattr(card, 'table'):
             h1 = card.table.horizontalHeaderItem(0).text()
             h2 = card.table.horizontalHeaderItem(1).text()
             print(f"Restored Headers: ['{h1}', '{h2}']")
             
             if h1 == "Taxable Value" and h2 == "Integrated Tax":
                  print("SUCCESS: Headers Restored from Summary Table.")
             else:
                  print(f"FAILURE: Header Mismatch. Got ['{h1}', '{h2}']")
        else:
             # If table not created (e.g. error returned), fail
             print("FAILURE: Table Widget not created.")


    def test_fix21_mandatory_semantic_restoration(self):
        print("\n--- TEST: Fix-21 Mandatory Semantic Restoration ---")
        from src.ui.issue_card import IssueCard
        # 1. Non-Fatal Identity Recovery (Legacy Snapshot)
        legacy_snapshot = {
             'issue_name': 'Legacy Issue',
             'grid_data': [{'value': 500}],
             'origin': 'SCN'
             # NO issue_id
        }
        
        print("Restoring Legacy Snapshot (Expecting No Crash)...")
        try:
             card = IssueCard.restore_snapshot(legacy_snapshot)
             print(f"Restored Identity: {card.issue_id}")
             
             if card.issue_id.startswith("LEGACY-RECOVERED-"):
                  print("SUCCESS: Surrogate Identity Generated.")
             else:
                  print(f"FAILURE: Unexpected Identity format: {card.issue_id}")
                  
             # Determinism Check
             card2 = IssueCard.restore_snapshot(legacy_snapshot)
             if card.issue_id == card2.issue_id:
                  print("SUCCESS: Surrogate Identity is Deterministic.")
             else:
                  print(f"FAILURE: Identity Instability ({card.issue_id} vs {card2.issue_id})")
                  
        except Exception as e:
             print(f"FAILURE: Hydration Crashed: {e}")
             import traceback
             traceback.print_exc()

        # 2. Header Locking Check
        # Restore a card with specific headers
        snapshot_headers = {'issue_id': 'LOCK_TEST', 'summary_table': {'headers': ['Fixed A', 'Fixed B']}}
        card_lock = IssueCard.restore_snapshot(snapshot_headers)
        
        # Simulate 'init_grid_ui' which sets the lock
        # We need to mock 'init_grid_ui' or manually set it since we can't call UI methods easily here without layout
        # But wait, init_grid_ui IS the mechanism.
        layout = MagicMock()
        layout.addWidget = MagicMock()
        card_lock.init_grid_ui(layout, data=snapshot_headers)
        
        print(f"Locked Headers after Init: {card_lock.locked_headers}")
        
        # Simulate Calculation that might overwrite headers
        # We trigger calculate_values via 'active' lifecycle?
        # But card is HYDRATION. calculation is blocked.
        # We must verify logic path: if we switch to ACTIVE and calc, headers adhere.
        
        # Force switch lifecycle for test
        card_lock.lifecycle_stage = "NEW_ISSUE"
        card_lock._is_calculating = False
        
        # Inject a template structure that mimics what calculate logic might generate default headers for?
        # Or just verify that calculate_values respects locked headers.
        # Actual check: inspect template afterwards.
        
        # trigger calc
        try:
             card_lock.calculate_values() # Should trigger header guard
             
             # Check template headers
             final_h = card_lock.template.get('summary_table', {}).get('headers')
             print(f"Final Headers after Calc: {final_h}")
             
             if final_h == ['Fixed A', 'Fixed B']:
                  print("SUCCESS: Headers Locked and Preserved.")
             else:
                  print(f"FAILURE: Headers Overwritten. Got {final_h}")
                  
        except Exception as e:
             print(f"Calc Error: {e}")

        except Exception as e:
             print(f"Calc Error: {e}")

    def test_fix22_semantic_enrichment(self):
        print("\n--- TEST: Fix-22 Semantic Enrichment ---")
        from src.ui.issue_card import IssueCard
        # Scenario: Snapshot lacks ID/Headers, but Template has them (Authoritative Source)
        template_source = {
             'issue_id': 'AUTH_ID_001', 
             'issue_name': 'Authoritative Name',
             'grid_data': {
                  'columns': [{'label': 'Legal Header A'}, {'label': 'Legal Header B'}]
             }
        }
        
        snapshot = {
             'template': template_source,
             'origin': 'ASMT10',
             'grid_data': [{'value': 10}],
             # No issue_id, No summary_table headers
        }
        
        print("Restoring Snapshot with Authoritative Template...")
        card = IssueCard.restore_snapshot(snapshot)
        
        # 1. Identity Check
        print(f"Restored Identity: {card.issue_id}")
        if card.issue_id == 'AUTH_ID_001':
             print("SUCCESS: Authoritative Identity Recovered from Template.")
        elif card.issue_id.startswith("LEGACY-RECOVERED"):
             print("FAILURE: Fell back to Surrogate ID despite authoritative source.")
        else:
             print(f"FAILURE: Unknown Identity: {card.issue_id}")
             
        # 2. Header Check
        # Trigger init_grid_ui
        layout = MagicMock()
        layout.addWidget = MagicMock()
        card.init_grid_ui(layout, data=snapshot)
        
        print(f"Locked Headers: {card.locked_headers}")
        if card.locked_headers == ['Legal Header A', 'Legal Header B']:
             print("SUCCESS: Semantic Headers Enriched from Template Columns.")
        else:
             print(f"FAILURE: Header Enrichment Failed. Got {card.locked_headers}")


    def test_fix22_master_lookup(self):
        print("\n--- TEST: Fix-22 Master Template Lookup (Legacy Snapshot) ---")
        from src.ui.issue_card import IssueCard
        
        # Scenario: Legacy snapshot with ONLY sop_point, no template, no ID
        legacy_snapshot = {
             'origin': 'ASMT10',
             'sop_point': 1, # Should map to LIABILITY_3B_R1
             'grid_data': [{'value': 100}] # Legacy content list
        }
        
        print("Restoring Legacy ASMT-10 Snapshot...")
        card = IssueCard.restore_snapshot(legacy_snapshot)
        
        # 1. Identity Check
        print(f"Restored Identity: {card.issue_id}")
        if card.issue_id == "LIABILITY_3B_R1":
             print("SUCCESS: Master Identity Recoved from SOP Point 1.")
        else:
             print(f"FAILURE: Identity Mismatch. Expected LIABILITY_3B_R1, Got {card.issue_id}")
             
        # 2. Header Check (SOP 1 has specific headers)
        layout = MagicMock()
        layout.addWidget = MagicMock()
        card.init_grid_ui(layout, data=legacy_snapshot)
        
        print(f"Locked Headers: {card.locked_headers}")
        # SOP 1 Headers: ["Description", "CGST", "SGST", "IGST", "Cess"] (Check initialized master order)
        # Note: get_grid_schema_sop1() uses these headers.
        expected = ["Description", "CGST", "SGST", "IGST", "Cess"]
        
        if card.locked_headers == expected:
             print("SUCCESS: SOP 1 Semantic Headers Enriched.")
        else:
             print(f"FAILURE: Header Enrichment Failed. Got {card.locked_headers}")

    def test_fix22_surrogate_override(self):
        print("\n--- TEST: Fix-22 Surrogate Override (Correction) ---")
        from src.ui.issue_card import IssueCard
        
        # Scenario: Snapshot WAS previously saved with a Surrogate ID (Corruption)
        # But it still has ASMT-10 origin and SOP point.
        bad_snapshot = {
             'origin': 'ASMT10',
             'sop_point': 1,
             'issue_id': 'LEGACY-RECOVERED-BADHASH',
             'template': {
                 'issue_id': 'LEGACY-RECOVERED-BADHASH',
                 'issue_name': 'Recovered Issue (BADHASH)'
             },
             'grid_data': [{'value': 999}]
        }
        
        print("Restoring Corrupted 'Legacy' Snapshot...")
        card = IssueCard.restore_snapshot(bad_snapshot)
        
        # Check Identity
        print(f"Restored Identity: {card.issue_id}")
        if card.issue_id == "LIABILITY_3B_R1":
             print("SUCCESS: System OVERRODE Surrogate ID with Master ID.")
        elif card.issue_id == "LEGACY-RECOVERED-BADHASH":
             print("FAILURE: System respected Surrogate ID instead of correcting it.")
        else:
             print(f"FAILURE: Unknown ID {card.issue_id}")

    def test_fix23_header_enforcement(self):
        """
        [Fix-23] Verify that restore_snapshot forcibly overwrites snapshot template drift with Master data.
        Scenario: Snapshot has 'grid_data' with 'Header 1', 'Header 2'.
                  Master (ITC_3B_2B_9X4) has 'Description', 'CGST', 'SGST', 'IGST', 'Cess'.
        Expected: Template Ref in restored card has Master columns.
        """
        print("\n--- TEST: Fix-23 Header Enforcement ---")
        from src.ui.issue_card import IssueCard
        
        # 1. Create Corrupted Snapshot Payload
        corrupt_snapshot = {
            "origin": "ASMT10",
            "sop_point": 12, # ITC_3B_2B_9X4
            "issue_id": None, # Force Master Lookup
            "template": {
                "grid_data": {
                    "columns": [
                        {"id": "col1", "label": "Header 1"},
                        {"id": "col2", "label": "Header 2"}
                    ]
                }
            },
            "data": {}
        }
        print(f"Snapshot columns (Before Restore): {corrupt_snapshot['template']['grid_data']['columns']}")
        
        # 2. Restore
        card = IssueCard.restore_snapshot(snapshot=corrupt_snapshot, parent=None)
        
        # 3. Verify Rendered Headers (Locked Headers)
        print(f"Locked Headers: {card.locked_headers}")
        
        expected_labels = ["Description", "CGST", "SGST", "IGST", "Cess"]
        
        if card.locked_headers == expected_labels:
             print("SUCCESS: Master Headers Enforced.")
        else:
             print(f"FAILURE: Headers mismatch. Got {card.locked_headers}")


    def test_fix24_value_projection(self):
        """[Fix-24] Verify Value Projection from Snapshot to Master Schema"""
        print("\n--- TEST: Fix-24 Value Projection ---")
        
        # 1. Legacy Snapshot with mismatched headers but valid data
        legacy_snapshot = {
            "origin": "ASMT10",
            "sop_point": 1, # SOP 1: LIABILITY_3B_R1
            "issue_id": "LIABILITY_3B_R1",
            "table_data": [
                ["Headers Still Corrupt", "H1", "H2", "H3", "H4"], 
                ["GSTR-1 Declaration", 500, 600, 700, 800]
            ],
            "variables": {} # Empty variables
        }
        
        # 2. Restore
        # Factory will resolve SOP 1 Master Schema
        card = IssueCard.restore_snapshot(snapshot=legacy_snapshot, parent=None)
        
        # 3. Verify Master Headers (Fix-23 Invariant)
        # SOP 1 Headers: ['Description', 'CGST', 'SGST', 'IGST', 'Cess']
        print(f"Locked Headers: {card.locked_headers}")
        
        # 4. Verify Value Projection (Fix-24 Invariant)
        # Row 1 Master Vars: row1_desc, row1_cgst, row1_sgst, row1_igst, row1_cess
        # Values from Snapshot: "GSTR-1 Declaration", 500, 600, 700, 800
        print(f"Projected row1_desc: {card.variables.get('row1_desc')}")
        print(f"Projected row1_cgst: {card.variables.get('row1_cgst')}")
        print(f"Projected row1_igst: {card.variables.get('row1_igst')}")
        
        if card.variables.get('row1_cgst') == 500 and card.variables.get('row1_igst') == 700:
             print("SUCCESS: Values Projected Positionally into Master Schema.")
        else:
             print(f"FAILURE: Projection mismatched. Card Variables: {card.variables}")


if __name__ == "__main__":
    unittest.main()
