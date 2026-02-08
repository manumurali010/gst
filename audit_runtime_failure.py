
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.ui.issue_card import IssueCard
import logging
import json

from PyQt6.QtWidgets import QApplication

# Setup Logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# Init App
app = QApplication(sys.argv)

print("--- AUDIT START ---")

# 1. Simulate Legacy ASMT-10 Snapshot (Worst Case)
# This mimics what comes from DB for an old issue
snapshot = {
    'origin': 'ASMT10',
    'sop_point': 1, # Int
    'issue_id': 'LEGACY-RECOVERED-12345', # Surrogate present
    'template': { # Corrupted/Legacy Template block
        'issue_id': 'LEGACY-RECOVERED-12345',
        'issue_name': 'Recovered Issue',
        'grid_data': [{'value': 100}]
    },
    'grid_data': [{'value': 100}] # Legacy content
}

print(f"SECTION A - SNAPSHOT CONTENT: {json.dumps(snapshot, indent=2)}")

# 2. Call restore_snapshot
try:
    print("\nSECTION C - SOP LOOKUP EXECUTION START")
    card = IssueCard.restore_snapshot(snapshot)
    print("SECTION C - SOP LOOKUP EXECUTION END")
    
    print(f"\n--- AUDIT RESULTS ---")
    print(f"Card ID (prop): {card.issue_id}")
    print(f"Card Template ID: {card.template.get('issue_id')}")
    print(f"Locked Headers: {card.locked_headers}")
    
    # Section E - Overwrite Check
    if card.issue_id == "LIABILITY_3B_R1":
        print("SECTION E: Authoritative Metadata Preserved (Success).")
    else:
        print("SECTION E: Authoritative Metadata LOST (Overwrite or Lookup Failure).")
        
    # Section F Check
    print(f"Template Grid Data Type: {type(card.template.get('grid_data'))}")
    if isinstance(card.template.get('grid_data'), list) and len(card.template['grid_data']) > 0:
        first_row = card.template['grid_data'][0]
        print(f"Template Grid Data Row 0: {first_row}")
        
    # Section G Check
    if card.issue_id == "LIABILITY_3B_R1" and card.locked_headers and "IGST" in card.locked_headers:
        print("SECTION G: Invariant Holds.")
    else:
        print("SECTION G: INVARIANT VIOLATION.")

except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("--- AUDIT END ---")
