
import sys
import json
from PyQt6.QtWidgets import QApplication, QTableWidget

# Mock dependencies if needed, or rely on actual imports
# Assuming the environment is set up correctly

from src.ui.issue_card import IssueCard
from src.ui.ui_helpers import render_grid_to_table_widget

def verify_replay_mode():
    app = QApplication(sys.argv)
    
    print("--- Starting Replay Architecture Verification ---")
    
    # 1. Define Frozen Artifact (Simulating what is saved in DRC-01A stage)
    # Intentionally diverging from SOP-1 Master Schema to prove authority
    frozen_artifact = {
        "issue_id": "LIABILITY_3B_R1", # SOP-1 ID
        "issue_name": "Frozen Replay Test",
        "sop_point": 1,
        "financial_year": "2023-24",
        "grid_data": {
            "columns": [
                {"id": "c0", "label": "Frozen Item"},
                {"id": "c1", "label": "Frozen Value"}
            ],
            "rows": [
                {
                    "c0": {"value": "Legacy Row 1", "type": "static", "style": "normal"},
                    "c1": {"value": "1000", "type": "static", "style": "bold"}
                },
                {
                    "c0": {"value": "Legacy Row 2", "type": "static", "style": "normal"},
                    "c1": {"value": "500", "type": "static", "style": "red"}
                }
            ]
        }
    }
    
    # [Verification 2] Narrative Baking
    frozen_artifact['brief_facts'] = "This is a locked narrative from the frozen artifact."
    
    print(f"Mock Artifact Created: {len(frozen_artifact['grid_data']['rows'])} rows.")
    
    # 2. Restore Snapshot (Should trigger Replay Mode)
    print("Restoring Snapshot...")
    card = IssueCard.restore_snapshot(frozen_artifact)
    
    # 3. Verify Template Injection
    # The template['grid_data'] MUST match our frozen artifact, NOT the master 4-row schema
    active_grid = card.template.get('grid_data')
    
    print("\n--- Verifying Authority ---")
    if active_grid == frozen_artifact['grid_data']:
        print("SUCCESS: Card initialized with Frozen Artifact grid_data.")
    else:
        print("FAILURE: Card ignored Frozen Artifact.")
        print(f"Expected: {json.dumps(frozen_artifact['grid_data'])[:50]}...")
        print(f"Actual:   {json.dumps(active_grid)[:50]}...")
        return False
        
    # [Verification 2] Narrative Capture
    print("\n--- Verifying Narrative ---")
    tmpl_facts = card.template.get('templates', {}).get('brief_facts')
    if tmpl_facts == frozen_artifact['brief_facts']:
        print("SUCCESS: Baked Narrative injected correctly.")
    else:
        print(f"FAILURE: Narrative mismatch. Got: {tmpl_facts}")
        return False

    # 4. Verify Master Bypass
    # Master SOP-1 has 5 columns (Desc, IGST, CGST, SGST, Cess). Ours has 2.
    cols = active_grid.get('columns', [])
    if len(cols) == 2 and cols[0]['label'] == "Frozen Item":
        print("SUCCESS: Master Schema Bypassed. Columns match Frozen Artifact.")
    else:
        print(f"FAILURE: Master Schema leaked through. Columns: {len(cols)}")
        return False
        
     # ... (rest of renderer verification)

    print("\n--- Verifying Renderer ---")
    table = QTableWidget()
    try:
        render_grid_to_table_widget(table, active_grid, interactive=True, locked=True)
        
        row_count = table.rowCount()
        col_count = table.columnCount()
        
        print(f"Rendered Table: {row_count} Rows, {col_count} Cols.")
        
        if row_count == 2 and col_count == 2:
            val_0_0 = table.item(0, 0).text()
            val_0_1 = table.item(0, 1).text()
            print(f"Cell (0,0): {val_0_0}")
            print(f"Cell (0,1): {val_0_1}")
            
            if val_0_0 == "Legacy Row 1" and val_0_1 == "1000":
                print("SUCCESS: Renderer correctly displayed Frozen Values.")
            else:
                print("FAILURE: Renderer values mismatch.")
                return False
        else:
            print("FAILURE: Dimensions mismatch.")
            return False
            
    except Exception as e:
        print(f"FAILURE: Renderer crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n--- REPLAY ARCHITECTURE VERIFIED ---")
    return True

if __name__ == "__main__":
    success = verify_replay_mode()
    sys.exit(0 if success else 1)
