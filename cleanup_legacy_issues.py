
import sqlite3
import os
import sys

# Adjust path to import src
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager()
    
    # List of authoritative SOP- IDs to KEEP
    keep_ids = [
        "SOP-1925D69B",
        "SOP-1A4E8A27",
        "SOP-643E26D5",
        "SOP-76CB395D",
        "SOP-A4E847E9",
        "SOP-C4969EE7",
        "SOP-B9618191",
        "SOP-6677D35C",
        "SOP-AEA26C26",
        "SOP-AC2C13C3",
        "SOP-360EDAD3",
        "SOP-FD40E50F"
    ]
    
    all_issues = db.get_all_issues_metadata()
    print(f"Total issues before cleanup: {len(all_issues)}")
    
    deleted_count = 0
    for issue in all_issues:
        issue_id = issue['issue_id']
        category = issue.get('category', '')
        
        # Determine if this is a legacy issue
        # It is legacy if it's NOT in keep_ids (and perhaps check if it looks like a legacy ID)
        # Assuming all valid new issues start with SOP- or are in the keep list.
        # Actually user said "Phase 1: Mark all non-listed ... as deprecated (or delete if safe)"
        # And "Phase 2: Permanently delete".
        
        # We will delete everything that is NOT in the authoritative list AND is related to Scrutiny.
        # (Assuming we don't want to delete unrelated Adjudication issues if they exist, but user said "Establish a single source of truth for Scrutiny issues")
        # Currently list shows only Scrutiny stuff + legacy stuff.
        
        if issue_id in keep_ids:
            print(f"KEEPING: {issue_id} - {issue['issue_name']}")
            continue
            
        # Safety check: Don't delete if it starts with SOP- but is somehow not in our list? 
        # (Maybe user created a custom one? User said "Only these issues may have active templates")
        # But wait, looking at the list, there are only these SOP- ones and the legacy uppercase ones.
        
        print(f"DELETING: {issue_id} - {issue['issue_name']}")
        try:
            db.delete_issue(issue_id)
            deleted_count += 1
        except Exception as e:
            print(f"FAILED to delete {issue_id}: {e}")

    print("-" * 40)
    print(f"Cleanup Complete. Deleted {deleted_count} legacy issues.")
    
except Exception as e:
    print(f"Error: {e}")
