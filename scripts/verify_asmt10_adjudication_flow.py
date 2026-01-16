import sys
import os
import json
import uuid

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database.db_manager import DatabaseManager

def test_flow():
    db = DatabaseManager()
    
    # Cleaning up previous test data if any (optional, but good)
    
    # 1. Create Scrutiny Case
    print("[1] Creating Scrutiny Case...")
    # Use unique GSTIN to avoid collisions from other tests
    gstin = f"99{str(uuid.uuid4())[:10]}".upper()
    scrutiny_id = db.create_proceeding({
        'gstin': gstin, 
        'financial_year': '2019-20',
        'legal_name': 'Test Flow Auto Trader'
    })
    
    # 2. Add Scrutiny Issues
    print("[2] Adding Scrutiny Issues...")
    issues = [
        {'category': 'ITC Mismatch', 'description': 'Issue 1', 'observation': 'Narrative 1', 'tax_breakdown': {'CGST':{'tax':100}}},
        {'category': 'RCM Liability', 'description': 'Issue 2', 'observation': 'Narrative 2', 'tax_breakdown': {'SGST':{'tax':200}}}
    ]
    db.update_proceeding(scrutiny_id, {'selected_issues': issues})
    
    # 3. Finalize ASMT-10 (Create Adjudication)
    print(f"[3] Finalizing Scrutiny Case {scrutiny_id}...")
    oc_data = {'OC_Number': f'TEST-OC-{uuid.uuid4().hex[:6]}', 'OC_Date': '2026-01-01', 'OC_Content': 'Test'}
    asmt_data = {'gstin': gstin, 'financial_year': '2019-20', 'issue_date': '2026-01-01', 'case_id': scrutiny_id}
    adj_data = {'gstin': gstin, 'legal_name': 'Test Flow Auto Trader', 'financial_year': '2019-20', 'source_scrutiny_id': scrutiny_id}
    
    # Transaction
    success = db.finalize_proceeding_transaction(scrutiny_id, oc_data, asmt_data, adj_data)
    if not success:
         print("FAIL: Transaction failed.")
         return
    
    # 4. Find the Adjudication Case ID
    # Query adjudication_cases for source_scrutiny_id
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM adjudication_cases WHERE source_scrutiny_id = ?", (scrutiny_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("FAIL: Adjudication case not created in DB.")
        return
        
    adj_id = row[0]
    print(f"[4] Created Adjudication Case ID: {adj_id}")
    
    # 5. Load Proceeding (Simulate UI load)
    print(f"[5] Loading Proceeding Data via get_proceeding({adj_id})...")
    proc_data = db.get_proceeding(adj_id)
    
    if not proc_data:
        print("FAIL: get_proceeding returned None")
        return
        
    print(f"    - Source Scrutiny ID: {proc_data.get('source_scrutiny_id')}")
    print(f"    - Issues Count: {len(proc_data.get('selected_issues', []))}")
    
    if proc_data.get('source_scrutiny_id') != scrutiny_id:
        print("FAIL: source_scrutiny_id mismatch")
        return
        
    if len(proc_data.get('selected_issues', [])) != 2:
        print("FAIL: Scrutiny issues not merged into proceeding data")
        return
        
    print("PASS: Data Merge logic works.")
    
    # 6. Simulate SCN Auto-Population Logic
    print("[6] Simulating SCN Auto-Population Logic...")
    # This logic mirrors what we added to proceedings_workspace.py
    
    scrutiny_issues = proc_data.get('selected_issues', [])
    scn_issues_list = []
    for item in scrutiny_issues:
        issue_data = {
            'issue': item.get('description') or item.get('category'),
            'scn_content': item.get('observation', ''),
            'tax_breakdown': item.get('tax_breakdown', {}),
            'variables': {k:v for k,v in item.items() if k not in ['tax_breakdown', 'observation']}
        }
        scn_issues_list.append({'issue_id': 'GENERIC', 'data': issue_data})
        
    db.save_case_issues(adj_id, scn_issues_list, stage='SCN')
    
    # 7. Verify SCN Issues Saved
    saved_issues = db.get_case_issues(adj_id, stage='SCN')
    print(f"[7] Verifying Saved SCN Issues: {len(saved_issues)} found.")
    
    if len(saved_issues) != 2:
        print(f"FAIL: Expected 2 SCN issues, found {len(saved_issues)}")
        return
        
    # Verify content Check
    first_issue = saved_issues[0]['data']
    print(f"    - Issue 1 Title: {first_issue.get('issue')}")
    if first_issue.get('issue') != "Issue 1":
         print("FAIL: Issue content mismatch")
         return

    print("PASS: SCN Auto-population verified.")

if __name__ == "__main__":
    test_flow()
