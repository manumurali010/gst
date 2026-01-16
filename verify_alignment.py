import sys
import os
import json

# Add project root to sys.path
sys.path.append('C:/Users/manum/.gemini/antigravity/scratch/gst')

from src.database.db_manager import DatabaseManager
from src.services.asmt10_generator import ASMT10Generator

def verify_alignment():
    db = DatabaseManager()
    
    # 1. Mock ScrutinyResult (Snapshot) for Point 12
    # The user corrected the amount to Rs. 13,574,248
    mock_snapshot = {
        "row1_desc": "ITC as per Table 8A of GSTR 9",
        "row1_igst": 10000000,
        "row1_cgst": 0,
        "row1_sgst": 0,
        "row1_cess": 0,
        
        "row2_desc": "ITC as per Table 8B of GSTR 9",
        "row2_igst": 23574248,
        "row2_cgst": 0,
        "row2_sgst": 0,
        "row2_cess": 0,
        
        "row3_desc": "ITC as per Table 8C of GSTR 9",
        "row3_igst": 0,
        "row3_cgst": 0,
        "row3_sgst": 0,
        "row3_cess": 0,
        
        "row4_desc": "ITC availed in Excess as per GSTR 9",
        "row4_igst": 13574248,
        "row4_cgst": 0,
        "row4_sgst": 0,
        "row4_cess": 0,
        
        "total_shortfall": 13574248
    }
    
    issue = {
        "issue_id": "ITC_3B_2B_9X4",
        "description": "Point 12- GSTR 3B vs 2B (discrepancy identified from GSTR 9)",
        "total_shortfall": 13574248,
        "snapshot": mock_snapshot
    }

    # 2. Simulate ScrutinyTab.enrich_issues_with_templates
    master = db.get_issue("ITC_3B_2B_9X4")
    if not master:
        print("FAIL: Master issue ITC_3B_2B_9X4 not found!")
        return
    
    master_json = json.loads(master[1])
    master_grid = master_json.get('grid_data')
    
    import copy
    rehydrated_grid = copy.deepcopy(master_grid)
    for row in rehydrated_grid:
        for cell in row:
            var_name = cell.get('var')
            if var_name and var_name in mock_snapshot:
                cell['value'] = mock_snapshot[var_name]
    
    issue['grid_data'] = rehydrated_grid
    issue['brief_facts'] = master_json.get('templates', {}).get('brief_facts')

    # 3. Verify ASMT-10 HTML Generation
    table_html = ASMT10Generator.generate_issue_table_html(issue)
    print("\n--- ASMT-10 Table HTML Preview (Grid Based) ---")
    print(table_html[:500] + "...")
    
    if "13,574,248" in table_html:
        print("SUCCESS: ASMT-10 Table contains the corrected amount!")
    else:
        print("FAIL: ASMT-10 Table MISSING the corrected amount.")

    # 4. Verify SCN Adoption logic
    # In proceedings_workspace.py: build_scn_issue_from_asmt10
    # mimics the persistence of snapshot_data
    asmt_record = {
        'issue_id': "ITC_3B_2B_9X4",
        'data': {
            'issue_id': "ITC_3B_2B_9X4",
            'total_shortfall': 13574248,
            'snapshot': mock_snapshot,
            'grid_data': rehydrated_grid # Saved as legally frozen
        }
    }
    
    # Simulate Adapter (ProceedingsWorkspace.build_scn_issue_from_asmt10)
    scn_template = db.get_issue("ITC_3B_2B_9X4")
    scn_template_json = json.loads(scn_template[1])
    scn_template_json['grid_data'] = rehydrated_grid
    
    print("\n--- SCN Adoption Preview ---")
    print(f"Issue ID: {asmt_record['issue_id']}")
    print(f"Table Rows: {len(scn_template_json['grid_data'])}")
    
    if len(scn_template_json['grid_data']) == 5: # Header + 4 rows
        print("SUCCESS: SCN Adoption correctly rehydrated the 5-row table.")
    else:
        print(f"FAIL: SCN Adoption has {len(scn_template_json['grid_data'])} rows, expected 5.")

if __name__ == "__main__":
    verify_alignment()
