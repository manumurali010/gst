import sqlite3
import json
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.services.scrutiny_parser import ScrutinyParser

DB_PATH = 'data/adjudication.db'

def reproduce_analysis():
    print("--- Scrutiny Analysis Reproduction ---")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch cases with additional_details (where file_paths are stored)
    cursor.execute("SELECT id, legal_name, additional_details FROM proceedings WHERE additional_details IS NOT NULL AND additional_details != ''")
    rows = cursor.fetchall()
    
    parser = ScrutinyParser()
    updated_count = 0
    
    for r_id, name, details_str in rows:
        try:
            details = json.loads(details_str)
            # Handle double-encoding if details is still a string
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    pass # Keep as string if parsing fails, but next line might fail
                    
            if not isinstance(details, dict):
                 print(f"Skipping {name} (Invalid details format: {type(details)})")
                 continue

            file_paths = details.get('file_paths', {})
            
            # Check if primary file exists
            main_file = file_paths.get('tax_liability_yearly')
            gstr9_file = file_paths.get('gstr9_yearly')
            
            if not main_file and not gstr9_file:
                print(f"Skipping {name} (No primary files found)")
                continue
                
            print(f"Reprocessing {name}...")
            
            # Prepare Configs
            group_configs = details.get('group_configs', {})
            configs = {
                "gstr3b_freq": group_configs.get('gstr3b', {}).get('frequency', 'Yearly'),
                "gstr1_freq": group_configs.get('gstr1', {}).get('frequency', 'Yearly')
            }
            
            # RUN ANALYSIS
            # Matches functionality of ScrutinyTab.analyze_file
            results = parser.parse_file(main_file, file_paths, configs)
            
            if "error" in results:
                print(f"  FAILED: {results.get('error')}")
                continue
                
            # Update Database
            # ScrutinyTab calls save_findings which updates `selected_issues`
            new_issues_json = json.dumps(results)
            
            cursor.execute("UPDATE proceedings SET selected_issues = ? WHERE id = ?", (new_issues_json, r_id))
            updated_count += 1
            print(f"  SUCCESS: Updated {len(results)} issues.")
            
        except Exception as e:
            print(f"  Error processing {name}: {e}")
            import traceback
            traceback.print_exc()

    conn.commit()
    conn.close()
    
    print(f"\nCompleted. Refreshed analysis for {updated_count} cases.")

if __name__ == "__main__":
    reproduce_analysis()
