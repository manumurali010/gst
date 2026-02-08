
import sys
import os
import json
import argparse
from datetime import datetime

# Setup Path
sys.path.append(os.getcwd())

# Mock/Import DB and Workspace
try:
    from src.database.db_manager import DatabaseManager
    from src.ui.proceedings_workspace import ProceedingsWorkspace
    from PyQt6.QtWidgets import QApplication
except ImportError:
    print("Error: Could not import project modules. Ensure you are in the project root.")
    sys.exit(1)

def is_stub_grid(grid_data):
    """
    Copy of is_stub_grid logic from proceedings_workspace.py
    """
    if not grid_data:
        return True
        
    # Case 1: Dictionary Schema {"columns": [], "rows": []}
    if isinstance(grid_data, dict):
        rows = grid_data.get('rows', [])
        if not rows: return True
        for row in rows:
            # Row can be dict (canonical) or list (legacy?) - Canonical is dict of cells
            if isinstance(row, dict):
                for col_id, cell in row.items():
                    if isinstance(cell, dict):
                        val = cell.get('value')
                        if val not in (None, "", "____"):
                            return False
                    elif cell not in (None, "", "____"):
                        return False
            # Fallback if row is list? Usually canonical is list of dicts.
        return True

    # Case 2: List of Lists (Legacy)
    if isinstance(grid_data, list):
        if len(grid_data) <= 1: # Only header or nothing
            return True
        for row in grid_data[1:]:
            for cell in row:
                if isinstance(cell, dict):
                    val = cell.get('value')
                    if val not in (None, "", "____"):
                        return False
                elif cell not in (None, "", "____"):
                    return False
        return True
        
    return True

def run_repair(dry_run=True):
    print(f"--- SCN Table Repair Tool [{'DRY RUN' if dry_run else 'LIVE COMMIT'}] ---")
    print(f"Started at: {datetime.now()}")
    
    # Init DB
    db = DatabaseManager() # Adjust DB path if needed or use default
    
    # We need a headless workspace to run the adapter logic
    # This might require a QApplication instance
    app = QApplication(sys.argv)
    
    # Hack: Subclass to avoid full UI init
    class HeadlessWorkspace(ProceedingsWorkspace):
        def __init__(self, db_manager):
            self.db = db_manager
            # Skip super().__init__ which does UI
            self.proceeding_id = None
            
    workspace = HeadlessWorkspace(db)
    
    stats = {'scanned': 0, 'candidates': 0, 'skipped_unsafe': 0, 'repaired': 0}
    
    # 1. Scan case_issues directly (Stage='SCN')
    scn_issues = []
    try:
        conn = db._get_conn()
        cursor = conn.cursor()
        # Fetch columns needed to construct "issue" object
        cursor.execute("""
            SELECT id, proceeding_id, issue_id, data_json, origin, source_proceeding_id, added_by
            FROM case_issues 
            WHERE stage='SCN'
        """)
        rows = cursor.fetchall()
        for row in rows:
            try:
                data = json.loads(row[3])
            except:
                data = {}
            
            scn_issues.append({
                'id': row[0],
                'proceeding_id': row[1],
                'issue_id': row[2],
                'data': data,
                'origin': row[4],
                'source_proceeding_id': row[5],
                'added_by': row[6]
            })
            
        conn.close()
        print(f"[DEBUG] Found {len(scn_issues)} SCN issues directly in case_issues table.")
        
        # 1.5 Fetch Adjudication Mapping (Adj Case ID -> Source Scrutiny ID)
        adj_source_map = {}
        try:
            conn = db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id, source_scrutiny_id FROM adjudication_cases")
            rows = cursor.fetchall()
            for r in rows:
                if r[0] and r[1]:
                    adj_source_map[r[0]] = r[1]
            conn.close()
            print(f"[DEBUG] Loaded {len(adj_source_map)} adjudication mappings.")
        except Exception as e:
            print(f"Warning: Could not fetch adjudication mappings: {e}")

    except Exception as e:
        print(f"Error fetching case_issues: {e}")
        return

    try:
        for issue in scn_issues:
            stats['scanned'] += 1
            issue_id = issue.get('issue_id')
            proc_id = issue.get('proceeding_id')
            data = issue.get('data', {})
            # Template snapshot is usually in 'template_snapshot' key inside data or separate column?
            # Schema says data_json stores "full JSON state". IssueCard persists 'template_snapshot' inside data_payload!
            # Wait, persist_scn_issues:
            # snapshot_item = { 'data': data_payload... }
            # data_payload = { 'template_snapshot': ..., 'variables': ... }
            # So 'data' in DB is snapshot_item['data']?
            # Let's check save_case_issues in db_manager.
            # It saves `data` as json.
            # So `data` has `template_snapshot`.
            
            template = data.get('template_snapshot', {})
            grid_data = template.get('grid_data') or data.get('table_data') or template.get('tables')
            
            # Check 1: Origin
            # Use column value first, then data
            origin = issue.get('origin') or data.get('origin') or 'SCN'
            
            if origin not in ['ASMT10', 'SCRUTINY']:
                continue
                
            # Check 2: Is Stub?
            if not is_stub_grid(grid_data):
                continue
                
            stats['candidates'] += 1
            print(f"[CANDIDATE] {issue_id} in {proc_id} (Origin: {origin}) has stub grid.")
            
            # Check 3: Safety (Re-generation)
            # Need source ASMT-10 record
            source_issue_id = data.get('source_issue_id')
            if not source_issue_id:
                    # Try to infer from issue_id if it matches
                    source_issue_id = issue_id

            # Get source record
            source_proc_id = issue.get('source_proceeding_id') or data.get('source_proceeding_id')
            
            # Fallback: Check adjudication map
            if not source_proc_id and proc_id:
                source_proc_id = adj_source_map.get(proc_id)
                if source_proc_id:
                     print(f"  [INFO] inferred source_proc_id {source_proc_id} from adjudication_cases.")
            
            if not source_proc_id:
                print(f"  [SKIP] No source proceeding ID found for {issue_id}")
                stats['skipped_unsafe'] += 1
                continue
                
            source_records = db.get_case_issues(source_proc_id, stage='DRC-01A')
            source_record = next((r for r in source_records if r['issue_id'] == source_issue_id), None)
            
            if not source_record:
                print(f"  [SKIP] Source ASMT-10 record {source_issue_id} not found.")
                stats['skipped_unsafe'] += 1
                continue
                
            # Regenerate
            try:
                regenerated = workspace.build_scn_issue_from_asmt10(source_record)
                regen_data = regenerated['data']
                regen_template = regenerated['template']
                
                # Verify Narration (Content)
                # SCN narration key might be 'scn_narration' or 'content'
                curr_content = data.get('scn_narration') or data.get('content') or ""
                regen_content = regen_data.get('scn_narration') or regen_data.get('content') or ""
                
                # Looseness: If current is empty, it's safe. If current == regen, safe.
                # Normalizing for comparison (strip whitespace)
                if curr_content.strip() and curr_content.strip() != regen_content.strip():
                    print(f"  [SKIP] Manual edits detected in narration.")
                    stats['skipped_unsafe'] += 1
                    continue
                    
                # SAFE TO REPAIR
                new_grid = regen_template.get('grid_data')
                if not new_grid or is_stub_grid(new_grid):
                    print(f"  [SKIP] Regenerated grid is also stub! (Source might be empty)")
                    continue
                    
                print(f"  [REPAIRABLE] Found valid grid with {len(new_grid.get('rows', []))} rows.")
                
                if not dry_run:
                    # APPLY REPAIR
                    # Update in-memory
                    # Force update template grid_data if template exists or create it
                    if template is None: template = {}
                    template['grid_data'] = new_grid
                    data['template_snapshot'] = template
                    
                    data['table_data'] = new_grid
                    
                    # DB Update
                    issue_pk = issue.get('id') # Internal DB ID
                    if issue_pk:
                        import json
                        def default(o):
                            if isinstance(o, (datetime.date, datetime.datetime)):
                                return o.isoformat()
                            
                        conn = db._get_conn()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE case_issues SET data_json = ? WHERE id = ?", (json.dumps(data, default=str), issue_pk))
                        conn.commit()
                        # conn.close() -- Moved to after verify
                        
                        print("  [SUCCESS] Repaired and Saved.")
                        
                        # Verify persistence immediately
                        chk_cursor = conn.cursor()
                        chk_cursor.execute("SELECT data_json FROM case_issues WHERE id=?", (issue_pk,))
                        saved_json = chk_cursor.fetchone()[0]
                        saved_data = json.loads(saved_json)
                        saved_template = saved_data.get('template_snapshot', {})
                        saved_grid = saved_template.get('grid_data') or saved_data.get('table_data')
                        print(f"  [VERIFY] Saved grid rows: {len(saved_grid.get('rows', [])) if saved_grid else 'None'}")
                        
                        conn.close() # Close after verify
                        
                        stats['repaired'] += 1
                    else:
                        print("  [FAIL] No PK found for issue.")
                else:
                    print("  [DRY RUN] Would update grid_data.")
                    stats['repaired'] += 1 # Count as potential repair
                    
            except Exception as e:
                print(f"  [ERROR] Regeneration failed: {e}")
                stats['skipped_unsafe'] += 1
                    
    except Exception as e:
        print(f"Fatal Processing Error: {e}")
        import traceback
        traceback.print_exc()
        
    print("-" * 30)
    print(f"SCAN COMPLETE.")
    print(f"Scanned: {stats['scanned']}")
    print(f"Candidates: {stats['candidates']}")
    print(f"Skipped (Unsafe/Missing Source): {stats['skipped_unsafe']}")
    print(f"{'Repaired' if not dry_run else 'Repairable'}: {stats['repaired']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', action='store_true', help="Execute changes (Live Mode)")
    args = parser.parse_args()
    
    run_repair(dry_run=not args.commit)
