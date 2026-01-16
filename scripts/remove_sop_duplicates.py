import sqlite3
import argparse
import sys
import json

DB_PATH = 'data/adjudication.db'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def check_references(cursor, issue_id):
    """
    Check for references to the issue_id in critical tables.
    Returns: List of strings describing where references were found.
    """
    references = []
    
    # 1. Check case_issues
    cursor.execute("SELECT count(*) FROM case_issues WHERE issue_id = ?", (issue_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        references.append(f"case_issues table (count={count})")

    # 2. Check adjudication_cases (selected_issues column)
    # This might be stored as a JSON string or comma-separated string.
    # We'll use a LIKE query for safety. 
    cursor.execute("SELECT id, selected_issues FROM adjudication_cases WHERE selected_issues LIKE ?", (f"%{issue_id}%",))
    rows = cursor.fetchall()
    if rows:
        references.append(f"adjudication_cases table (selected_issues match in {len(rows)} cases)")

    # 3. Check scrutiny_results (if table exists)
    try:
        cursor.execute("SELECT count(*) FROM scrutiny_results WHERE issue_id = ?", (issue_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            references.append(f"scrutiny_results table (count={count})")
    except sqlite3.OperationalError:
        pass # Table might not exist

    return references

def run_cleanup(execute=False):
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"Mode: {'EXECUTION (Destructive)' if execute else 'DRY RUN (Safe)'}")
    print("-" * 50)

    # 1. Identify Candidates (SOP-% only)
    cursor.execute("SELECT issue_id, issue_name FROM issues_master WHERE issue_id LIKE 'SOP-%'")
    candidates = cursor.fetchall()

    if not candidates:
        print("No issues matching pattern 'SOP-%' found.")
        conn.close()
        return

    print(f"Found {len(candidates)} candidate issues for deletion.")
    
    blocked_count = 0
    safe_to_delete = []

    # 2. Safety Check Loop
    print("\nSafety Analysis:")
    for issue_id, name in candidates:
        refs = check_references(cursor, issue_id)
        if refs:
            print(f"[BLOCKED] {issue_id} ({name}) is in use!")
            for r in refs:
                print(f"    - Found in {r}")
            blocked_count += 1
        else:
            print(f"[SAFE] {issue_id} ({name}) - No active references.")
            safe_to_delete.append(issue_id)

    print("-" * 50)
    print(f"Analysis Complete: Safe: {len(safe_to_delete)} | Blocked: {blocked_count}")

    if blocked_count > 0:
        print("\nCRITICAL: Script Aborted due to active references.")
        print("Please resolve references manually before deletion.")
        conn.close()
        sys.exit(1)

    if not safe_to_delete:
        print("No issues to delete.")
        conn.close()
        return

    # 3. Execution
    if execute:
        print(f"\nProceeding to DELETE {len(safe_to_delete)} issues...")
        deleted_count = 0
        for issue_id in safe_to_delete:
            try:
                cursor.execute("DELETE FROM issues_master WHERE issue_id = ?", (issue_id,))
                cursor.execute("DELETE FROM issues_data WHERE issue_id = ?", (issue_id,))
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {issue_id}: {e}")
        
        conn.commit()
        print(f"\nSUCCESS: Deleted {deleted_count} issues.")
    else:
        print(f"\nDRY RUN COMPLETE. {len(safe_to_delete)} issues identified for deletion. Use --execute to proceed.")

    # 4. Final Verification Stats
    cursor.execute("SELECT count(*) FROM issues_master")
    final_count = cursor.fetchone()[0]
    print(f"Remaining Issues in Master: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up duplicate SOP- issues.")
    parser.add_argument("--execute", action="store_true", help="Perform actual deletion")
    args = parser.parse_args()

    run_cleanup(execute=args.execute)
