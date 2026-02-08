
import sys
import os
import json

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_manager import DatabaseManager

def purge_invalid_scn_issues():
    db = DatabaseManager()
    
    # 1. Get all proceedings
    proceedings = db.get_all_proceedings()
    print(f"--- SCN ISSUE PURGE & RESET ---")
    print(f"Scanning {len(proceedings)} proceedings...")
    
    purged_proceedings_count = 0
    total_issues_deleted = 0
    
    for proc in proceedings:
        pid = proc['id']
        p_title = f"{proc.get('taxpayer', {}).get('legal_name', 'Unknown')} ({pid})"
        
        # 2. Get SCN issues
        issues = db.get_case_issues(pid, stage='SCN')
        if not issues:
            continue
            
        has_invalid = False
        invalid_reasons = []
        
        for issue_record in issues:
            data = issue_record.get('data', {})
            issue_id = issue_record.get('issue_id') # From DB column
            issue_id_in_data = data.get('issue_id')
            
            # CRITERIA 1: Missing ID
            if not issue_id or not issue_id_in_data:
                has_invalid = True
                invalid_reasons.append(f"Missing Issue ID")
                break # Optimization: One strike and you're out (per proceeding)
            
            # CRITERIA 2: Legacy Table Data (List)
            if isinstance(data.get('table_data'), list):
                has_invalid = True
                invalid_reasons.append(f"Legacy table_data (List) found in {issue_id}")
                break
                
            # CRITERIA 3: Missing Proper Grid (Dict) AND Missing Baseline (Dict)
            has_grid = isinstance(data.get('grid_data'), dict)
            has_baseline = isinstance(data.get('baseline_grid_data'), dict)
            is_narrative = data.get('narrative_only') is True
            
            # Note: repair script might have tagged narrative, so we respect that.
            # But if user wants DESTRUCTIVE cleanup of *invalid* ones, we respect Strict Rules.
            # "Any SCN issue... does not contain... baseline_grid_data... or grid_data is invalid"
            # BUT: "Any SCN issue where table_data is list... must be deleted"
            
            # If we respect narrative_only, we might keep it. 
            # But user said "Any SCN issue that does not contain either: baseline... or grid... IS INVALID."
            # That implies narrative_only issues are also technically invalid if they violate that "either/or" rule strict reading?
            # Wait, "Explicit Constraints... No legacy auto-conversion...".
            # AND "Narrative-only" was discussed in previous step.
            # However, this prompt text overrides? "Any SCN issue that does not contain either ... is invalid."
            # It didn't mention narrative_only exception in the "Mandatory Cleanup Rules".
            # BUT, the repair script just ran and tagged them.
            # If I purge them now, I undo the repair.
            # User said "Option A ... purge all invalid ... rebuild clean state from ASMT-10".
            # The "GENERIC" issue found in audit was "UNKNOWN" origin. ASMT-10 auto-adoption cannot rebuild it.
            # If I purge it, it's gone forever.
            # However, the user said "Confirm... This is expected behavior... Implement one-time destructive data cleanup".
            # And "Any SCN issue that does not contain either... is invalid."
            # This implies the previous "narrative_only" fix might have been a patch user is now rejecting in favor of strict purge?
            # OR, "narrative_only" IS valid if it has `grid_data`? (No, narrative usually means empty grid).
            # Let's look at "Explicit Constraints... Do NOT modify IssueCard guards."
            # My IssueCard guard ALLOWS narrative_only.
            # So if I delete them, I am being stricter than the guard.
            # But the user's rule for *Cleanup* says:
            # "Any SCN issue that does not contain either: baseline... or grid... is invalid."
            # It seems strict.
            # BUT, if I delete the `GENERIC` issue, the user loses that data.
            # Is that acceptable? "Destructive data cleanup". "No legacy auto-conversion".
            # I will follow the strict rule: If no grid/baseline, it is invalid.
            # (Even if narrative_only is True).
            # Wait, if I delete it, the user might complain I deleted the narrative data.
            # BUT "Option A... rebuild clean state from ASMT-10".
            # This implies the valid state comes from ASMT-10.
            # `GENERIC` issue with `UNKNOWN` origin does NOT come from ASMT-10.
            # So it will be lost.
            # User seems to accept this: "destructive... not patched in-place...".
            # I will proceed with STRICT purge.
            
            if not has_grid and not has_baseline:
                 # Check if narrative_only saves it? User didn't list it as exception in "Mandatory Cleanup Rules".
                 # But previous step "Contract enforcement is accepted... blank IssueCards... expected...".
                 # I will assume "Narrative Only" issues which HAVE content but no grid might be valid if they conform to "Narrative Only" mode?
                 # Actually, "Narrative Only" usually implies `grid_data` is None.
                 # If user says "Any SCN issue that does not contain... is invalid", then Narrative Only issues are invalid?
                 # Let's check if "Narrative Only" issues have a stub grid?
                 # If `grid_data` is missing, it fails the check.
                 # I will err on side of caution: If `narrative_only` is True, I will spare it?
                 # User: "Delete ... not patched in-place."
                 # User: "Option A ... rebuild clean state from ASMT-10".
                 # If I spare it, it might block adoption? No, adoption adds others.
                 # But strict rule says "Invalid".
                 # I will verify `audit_scn_issues` result. The `GENERIC` issue had `Origin: UNKNOWN`.
                 # It was "BROKEN [No Table]".
                 # If I just repaired it to "Narrative Only", does it have `grid_data`? No.
                 # So it strictly violates "does not contain either baseline... or grid...".
                 # So I MUST delete it.
                 
                 has_invalid = True
                 invalid_reasons.append(f"Missing Grid/Baseline (Strict)")
                 break
        
        if has_invalid:
            print(f"PURGING Proceeding {pid} ({p_title})")
            print(f"  Reason: {invalid_reasons[0]}")
            
            # 1. Delete ALL SCN issues
            deleted_count = db.delete_all_case_issues(pid, stage='SCN')
            total_issues_deleted += deleted_count
            
            # 2. Reset Adoption Flag to allow Re-Adoption
            additional = proc.get('additional_details', {})
            # Handle string case if legacy
            if isinstance(additional, str): additional = {}
            
            if additional.get('scn_adopted_from_asmt10'):
                additional['scn_adopted_from_asmt10'] = False
                db.update_proceeding_additional_details(pid, additional)
                print(f"  -> Reset 'scn_adopted_from_asmt10' flag.")
            
            purged_proceedings_count += 1
            print(f"  -> Deleted {deleted_count} issues.")
            
    print(f"\n--- PURGE COMPLETE ---")
    print(f"Proceedings Purged: {purged_proceedings_count}")
    print(f"Total Issues Deleted: {total_issues_deleted}")

if __name__ == "__main__":
    purge_invalid_scn_issues()
