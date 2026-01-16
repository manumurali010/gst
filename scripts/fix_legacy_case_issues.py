import sqlite3
import json
import argparse
import sys
import re

DB_PATH = 'data/adjudication.db'

# Strict Enum Mapping (Tertiary Check)
CATEGORY_MAPPING = {
    "Outward Liability Mismatch (GSTR 3B vs GSTR 1)": "LIABILITY_3B_R1",
    "Liability Mismatch (3B vs 1)": "LIABILITY_3B_R1", # LEGACY
    "Outward Liability (GSTR 3B vs GSTR 1)": "LIABILITY_3B_R1", # LEGACY 2
    "RCM Liability mismatch (GSTR 3B vs GSTR 2B)": "RCM_LIABILITY_ITC",
    "Liability Mismatch (3B vs 2A)": "RCM_LIABILITY_ITC", # LEGACY
    "RCM (GSTR 3B vs GSTR 2B)": "RCM_LIABILITY_ITC", # LEGACY 2
    "ISD Credit mismatch (GSTR 3B vs GSTR 2B)": "ISD_CREDIT_MISMATCH",
    "ISD Credit Mismatch": "ISD_CREDIT_MISMATCH", # LEGACY
    "ISD Credit (GSTR 3B vs GSTR 2B)": "ISD_CREDIT_MISMATCH", # LEGACY 2
    "All Other ITC Mismatch (GSTR 3B vs GSTR 2B)": "ITC_3B_2B_OTHER",
    "ITC Mismatch (3B vs 2A)": "ITC_3B_2B_OTHER", # LEGACY
    "All Other ITC (GSTR 3B vs GSTR 2B)": "ITC_3B_2B_OTHER", # LEGACY 2
    "TDS/TCS Credit Mismatch (GSTR 3B vs GSTR 2B)": "TDS_TCS_MISMATCH",
    "TDS/TCS (GSTR 3B vs GSTR 2B)": "TDS_TCS_MISMATCH", # LEGACY
    "Import ITC Mismatch (GSTR 3B vs ICEGATE)": "IMPORT_ITC_MISMATCH",
    "Import ITC Mismatch (3B vs ICEGATE)": "IMPORT_ITC_MISMATCH", # LEGACY
    "GSTR 3B vs 2B (discrepancy identified from GSTR 9)": "ITC_3B_2B_9X4",
    "E-Waybill Comparison (GSTR 3B vs E-Waybill)": "EWAY_BILL_MISMATCH",
    "ITC from Cancelled Suppliers": "CANCELLED_SUPPLIERS",
    "ITC passed on by Cancelled TPs": "CANCELLED_SUPPLIERS", # LEGACY
    "ITC from Non-Filing Suppliers": "NON_FILER_SUPPLIERS",
    "ITC passed on by Suppliers who have not filed GSTR 3B": "NON_FILER_SUPPLIERS", # LEGACY
    "Section 16(4) ITC Violation": "SEC_16_4_VIOLATION",
    "Ineligible Availment of ITC [Violation of Section 16(4)]": "SEC_16_4_VIOLATION", # LEGACY
    "Rule 42/43 Reversal Mismatch": "RULE_42_43_VIOLATION"
}

# Template Type Mapping (Primary Check)
TEMPLATE_TYPE_MAPPING = {
    "liability_mismatch": "LIABILITY_3B_R1",
    "summary_3x4": None, # Too generic, rely on Category
    "liability_monthly": "LIABILITY_3B_R1",
    "itc_yearly_summary": "ITC_3B_2B_9X4" # Likely
}

def identify_semantic_id(issue_obj):
    """
    Deterministically identifies the Semantic ID based on strict rules.
    Returns: (Semantic_ID, Strategy) or (None, Reason)
    """
    if not isinstance(issue_obj, dict):
         return None, "Invalid Object"

    # 1. Primary: Template Type
    t_type = issue_obj.get('template_type')
    if t_type and t_type in TEMPLATE_TYPE_MAPPING and TEMPLATE_TYPE_MAPPING[t_type]:
        return TEMPLATE_TYPE_MAPPING[t_type], f"Primary: template_type='{t_type}'"

    # 2. Secondary: Table Schema Signature
    # Check issue_table_data headers
    table_data = issue_obj.get('issue_table_data', {})
    if not table_data:
        # Fallback to old keys? grid_data
        pass
        
    headers = table_data.get('headers', []) if table_data else []
    
    # 3. Tertiary: Strict Category Enum
    cat = issue_obj.get('category') or issue_obj.get('issue_name')
    # Strip prefixes like "Point 1- " for matching
    cleaned_cat = cat
    if cat:
        cleaned_cat = re.sub(r'^Point \d+- ?', '', cat).strip()
    
    if cleaned_cat in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[cleaned_cat], f"Tertiary: Exact Category Match '{cleaned_cat}'"

    return None, f"Unmappable: cat='{cleaned_cat}', type='{t_type}'"

def fix_legacy_issues(execute=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Legacy Data Recovery (Proceedings Table) ---")
    
    # Target 'proceedings' table, 'selected_issues' column
    cursor.execute("SELECT id, legal_name, selected_issues FROM proceedings WHERE selected_issues LIKE '%SOP-%'")
    rows = cursor.fetchall()
    
    if not rows:
        print("Pre-check Passed: No 'SOP-' unique strings found in selected_issues.")
        conn.close()
        return

    print(f"Found {len(rows)} proceedings with potential legacy ID usage.")
    
    corrections = []
    unmappable = []
    
    for r_id, name, issues_json_str in rows:
        try:
            issues_list = json.loads(issues_json_str)
            if not isinstance(issues_list, list):
                continue
                
            modified_list = False
            new_issues_list = []
            
            for idx, issue in enumerate(issues_list):
                iid = issue.get('issue_id')
                if iid and iid.startswith('SOP-'):
                    sem_id, strategy = identify_semantic_id(issue)
                    if sem_id:
                        # Modify the issue object
                        issue['issue_id'] = sem_id
                        # Also update mapped template keys/vars if needed? 
                        # For now, just ID update to link to Master logic.
                        # Actually, better to keep existing data but update ID.
                        
                        corrections.append((r_id, iid, sem_id, strategy))
                        modified_list = True
                        new_issues_list.append(issue)
                    else:
                        unmappable.append((r_id, iid, strategy))
                        # Keep original if unmappable? or Fail whole batch?
                        # Script says "ABORT record migration".
                        # If Execute=True, we fail.
                        pass
                else:
                    new_issues_list.append(issue)
            
            if modified_list:
                # Prepare UPDATE tuple
                # (new_json_str, row_id)
                pass # Stored in separate list or applied directly
                
                # We need to store specific updates. A bit complex for single tuple list.
                # Let's execute immediately if execute=True?
                # No, standard pattern: Collect then Execute.
                
                # Store the FULL updated JSON for this row
                corrections.append({
                    "type": "UPDATE_ROW",
                    "id": r_id,
                    "name": name,
                    "new_json": json.dumps(new_issues_list)
                })

        except Exception as e:
            print(f"Error parsing row {r_id}: {e}")

    # Deduplicate logging (corrections list has individual and row logs is messy)
    # Let's filter corrections for display vs execution
    
    row_updates = [c for c in corrections if isinstance(c, dict) and c.get("type") == "UPDATE_ROW"]
    individual_logs = [c for c in corrections if isinstance(c, tuple)]
    
    print(f"\nAnalysis Results:")
    print(f"  Total Issues to Migrate: {len(individual_logs)}")
    print(f"  Proceedings to Update: {len(row_updates)}")
    print(f"  Unmappable Issues: {len(unmappable)}")
    
    if unmappable:
        print("\nCRITICAL: The following issues could not be mapped:")
        for r in unmappable:
            print(f"  Proc {r[0]} | Issue {r[1]}: {r[2]}")
        if execute:
             print("Aborting execution due to unmappable records.")
             conn.close()
             sys.exit(1)

    print("\nProposed Migrations:")
    for r in individual_logs:
        print(f"  Proc {r[0]}: {r[1]} -> {r[2]} [{r[3]}]")

    if execute:
        print("\nExecuting Updates...")
        for update in row_updates:
            cursor.execute("UPDATE proceedings SET selected_issues = ? WHERE id = ?", (update['new_json'], update['id']))
        conn.commit()
        print(f"SUCCESS: Updated {len(row_updates)} rows.")
    else:
        print("\n[Dry Run] No changes applied. Use --execute to apply.")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recover legacy case data")
    parser.add_argument("--execute", action="store_true", help="Perform actual updates")
    args = parser.parse_args()
    
    fix_legacy_issues(args.execute)
