
import sqlite3
import json
import argparse
import sys
import uuid

DB_PATH = "data/adjudication.db"

def migrate(dry_run=True):
    print(f"=== MIGRATION SCRIPT (Dry Run: {dry_run}) ===\n")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Register LEGACY_GENERIC in Master if missing
    print("--- 1. Verification of Master Identifiers ---")
    cursor.execute("SELECT issue_id FROM issues_master WHERE issue_id='LEGACY_GENERIC'")
    if not cursor.fetchone():
        print("  [WARN] LEGACY_GENERIC not found in master. It will be created.")
        if not dry_run:
            # Create a placeholder master entry
            templates = {
                "brief_facts": "Legacy issue imported from earlier system.",
                "scn": "Legacy issue imported from earlier system."
            }
            cursor.execute("""
                INSERT INTO issues_master (issue_id, issue_name, category, sop_point, templates, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ('LEGACY_GENERIC', 'Legacy Imported Issue', 'Legacy', 99, json.dumps(templates)))
            print("  [ACTION] Created LEGACY_GENERIC in issues_master.")
    else:
        print("  [OK] LEGACY_GENERIC exists in master.")
    
    # 2. Repair Source Rows (DRC-01A / ASMT-10)
    print("\n--- 2. Scanning Source Rows (DRC-01A / ASMT-10) ---")
    cursor.execute("""
        SELECT id, issue_id, stage, data_json, proceeding_id 
        FROM case_issues 
        WHERE stage IN ('DRC-01A', 'ASMT-10')
    """)
    rows = cursor.fetchall()
    
    repaired_count = 0
    generic_fix_count = 0
    
    affected_proceedings = set()
    
    for row in rows:
        try:
            data = json.loads(row['data_json'])
            modifications = False
            
            # A) Grid Data Normalization
            grid = data.get('grid_data')
            summary = data.get('summary_table')
            
            # Check if Grid is Missing OR matches Summary (Idempotent Fix)
            grid_is_empty = not grid or (isinstance(grid, dict) and not grid.get('rows'))
            
            # Idempotency: If grid and summary are identical, we might have already patched it.
            # But we still want to add to affected_proceedings to ensure SCN re-clone happens!
            grid_matches_summary = (grid == summary) and summary
            
            should_patch = (grid_is_empty and summary) or grid_matches_summary
            
            if should_patch and summary and isinstance(summary, dict) and summary.get('rows'):
                # Only log if actually changing (grid empty) or forcing re-clone (grid match)
                if grid_is_empty:
                     print(f"  [DETECT] Row {row['id']} ({row['issue_id']}): Promoting summary_table to grid_data.")
                else:
                     print(f"  [RE-DETECT] Row {row['id']}: Already patched, but ensuring SCN sync.")
                
                # Promotion Logic (Always apply to ensure columns are fixed)
                new_grid = summary.copy()
                
                # Ensure Columns exist
                if 'columns' not in new_grid:
                     # Infer from headers if available
                     if 'headers' in new_grid:
                          new_grid['columns'] = [{'id': f'col{i}', 'title': h} for i, h in enumerate(new_grid['headers'])]
                     elif new_grid['rows']:
                          # Infer from first row keys
                          first = new_grid['rows'][0]
                          if isinstance(first, dict):
                               new_grid['columns'] = [{'id': k, 'title': k.upper()} for k in first.keys()]
                
                # Update only if different
                if data.get('grid_data') != new_grid:
                    data['grid_data'] = new_grid
                    modifications = True
                else:
                    # If data match, we still flag modification=True to trigger the affected_proceedings logic?
                    # No, modification implies DB write.
                    # We just need to add to set.
                    affected_proceedings.add(row['proceeding_id'])
                
            # B) Identifier Correction
                
            # B) Identifier Correction
            original_id = row['issue_id']
            if original_id == 'GENERIC':
                print(f"  [DETECT] Row {row['id']}: Remapping GENERIC -> LEGACY_GENERIC")
                data['issue_id'] = 'LEGACY_GENERIC' # Update payload
                # Also need to update SQL column
                modifications = True
                generic_fix_count += 1
            
            if modifications:
                repaired_count += 1
                if not dry_run:
                    # Persist JSON
                    cursor.execute("UPDATE case_issues SET data_json = ? WHERE id = ?", (json.dumps(data), row['id']))
                    
                    # Persist ID change if needed
                    if original_id == 'GENERIC':
                         cursor.execute("UPDATE case_issues SET issue_id = 'LEGACY_GENERIC' WHERE id = ?", (row['id'],))
                         
                    affected_proceedings.add(row['proceeding_id']) # Not strictly needed unless reverse lookup? 
                    # Actually, we need to know which SCNs are derived from this.
                    # We can find SCNs by `source_proceeding_id`.
                    # But wait, `source_proceeding_id` is on the SCN row.
                    # So we need the Proceeding ID of THIS row.
                    
                    # Store the proceeding ID of the SOURCE row.
                    # Any SCN row that points to this proceeding ID needs re-cloning.
                    cursor.execute("SELECT id FROM proceedings WHERE id=?", (row['proceeding_id'],)) # Verify existence
                    
                    # IMPORTANT: Find CHILD SCN proceedings that link to this source proceeding
                    # The SCN *Proceeding* might link to the Source *Proceeding*? 
                    # Or SCN *Issue* links to Source *Proceeding*?
                    # The schema says `case_issues.source_proceeding_id`.
                    # So we collect `row['proceeding_id']` as a target source.
                    affected_proceedings.add(row['proceeding_id'])

        except Exception as e:
            print(f"  [ERROR] Parsing Row {row['id']}: {e}")

    print(f"\n  Found {repaired_count} Source Rows to repair.")
    print(f"  Found {generic_fix_count} GENERIC Identifiers to fix.")

    # 3. SCN Re-Cloning
    print("\n--- 3. SCN Re-Cloning ---")
    if not affected_proceedings:
        print("  No SCN re-cloning needed (No source changes or dry-run).")
    else:
        print(f"  Scanning for SCNs derived from {len(affected_proceedings)} Source Proceedings: {list(affected_proceedings)}")
        
        # Find SCN Issues derived from these proceedings
        # Method A: Explicit Linkage
        placeholders = ','.join(['?']*len(affected_proceedings))
        query = f"SELECT id, proceeding_id, issue_id, source_proceeding_id FROM case_issues WHERE stage='SCN' AND source_proceeding_id IN ({placeholders})"
        cursor.execute(query, list(affected_proceedings))
        scn_rows_explicit = cursor.fetchall()
        
        # Method B: Parent Linkage (Reverse Lookup)
        # Check if Source Proceeding points to SCN Proceeding via adjudication_case_id
        scn_rows_implicit = []
        for src_proc_id in affected_proceedings:
             # Check what this Source Proceeding links to
             cursor.execute("SELECT adjudication_case_id FROM proceedings WHERE id=?", (src_proc_id,))
             link = cursor.fetchone()
             if link and link[0]:
                  potential_scn_proc_id = link[0]
                  # Verify this potential proc has SCN issues
                  cursor.execute("SELECT id, proceeding_id, issue_id, source_proceeding_id FROM case_issues WHERE proceeding_id=? AND stage='SCN'", (potential_scn_proc_id,))
                  rows = cursor.fetchall()
                  if rows:
                       print(f"  [LINK] Found {len(rows)} SCN Issues via Parent Linkage (Source {src_proc_id} -> SCN {potential_scn_proc_id})")
                       # Inject implicit source ID for the cloner
                       for r in rows:
                            # Use a dict/tuple to carry the inferred source
                            r_dict = dict(r)
                            r_dict['inferred_source_id'] = src_proc_id
                            scn_rows_implicit.append(r_dict)

        # Merge unique SCN issues
        final_targets = {}
        for r in scn_rows_explicit:
             final_targets[r['id']] = {'row': r, 'source': r['source_proceeding_id']}
        for r in scn_rows_implicit:
             if r['id'] not in final_targets:
                  final_targets[r['id']] = {'row': r, 'source': r['inferred_source_id']}

        print(f"  Found {len(final_targets)} SCN Issues to Delete & Re-Clone.")
        
        if not dry_run and final_targets:
            for scn_id, info in final_targets.items():
                 scn_row = info['row']
                 # Delete
                 cursor.execute("DELETE FROM case_issues WHERE id=?", (scn_id,))
                 print(f"  [ACTION] Deleted SCN Issue {scn_id} ({scn_row['issue_id']})")
            
            # Re-Clone map
            proc_map = {} # SCN_Proc -> Source_Proc
            for info in final_targets.values():
                 proc_map[info['row']['proceeding_id']] = info['source']

            for scn_proc_id, src_proc_id in proc_map.items():
                 print(f"  [ACTION] Re-Cloning for SCN Proceeding {scn_proc_id} from Source {src_proc_id}")
                 
                 # Fetch Source Issues from src_proc_id
                 cursor.execute("SELECT issue_id, data_json FROM case_issues WHERE proceeding_id=? AND stage IN ('DRC-01A', 'ASMT-10')", (src_proc_id,))
                 sources = cursor.fetchall()
                 
                 count = 0
                 for src in sources:
                      # Insert copy
                      cursor.execute("""
                          INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json, source_proceeding_id, origin)
                          VALUES (?, ?, 'SCN', ?, ?, 'MIGRATION')
                      """, (scn_proc_id, src['issue_id'], src['data_json'], src_proc_id))
                      count += 1
                 print(f"    -> Cloned {count} issues.")

    if not dry_run:
        conn.commit()
        print("\n[SUCCESS] Migration Committed.")
    else:
        print("\n[INFO] Dry Run Complete. No changes made.")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Execute changes (Default is Dry Run)')
    args = parser.parse_args()
    
    migrate(dry_run=not args.execute)
