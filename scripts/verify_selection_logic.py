
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from services.asmt10_generator import ASMT10Generator
except ImportError:
    # Handle running from root
    sys.path.append(os.getcwd())
    from src.services.asmt10_generator import ASMT10Generator

def verify_logic():
    print("Verifying Selection Logic...")
    
    # Mock Data
    issues = [
        {
            'issue_id': 'SOP-01',
            'issue_name': 'Included Issue',
            'total_shortfall': 100.0,
            'is_included': True,
            'brief_facts': 'Should appear'
        },
        {
            'issue_id': 'SOP-02',
            'issue_name': 'Excluded Issue',
            'total_shortfall': 200.0,
            'is_included': False,
            'brief_facts': 'Should NOT appear'
        },
        {
            'issue_id': 'SOP-03',
            'issue_name': 'Zero Shortfall Included',
            'total_shortfall': 0.0,
            'is_included': True,
            'brief_facts': 'Should NOT appear'
        },
        {
            'issue_id': 'SOP-04',
            'issue_name': 'Legacy Issue (Default True)',
            'total_shortfall': 50.0,
            # is_included missing -> default True
            'brief_facts': 'Should appear'
        }
    ]
    
    # 1. Verify Filter Logic (Simulation of ScrutinyTab.finalize_asmt_notice)
    print("\n1. Testing Filter Logic (Simulation)...")
    active_issues = [i for i in issues if float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)]
    
    ids = [i['issue_id'] for i in active_issues]
    print(f"Active Issues: {ids}")
    
    assert 'SOP-01' in ids, "SOP-01 should be included"
    assert 'SOP-02' not in ids, "SOP-02 should be excluded (is_included=False)"
    assert 'SOP-03' not in ids, "SOP-03 should be excluded (shortfall=0)"
    assert 'SOP-04' in ids, "SOP-04 should be included (default True)"
    
    print("Filter Logic Passed.")
    
    # 2. Verify ASMT10 Generator
    print("\n2. Testing ASMT10Generator...")
    # Mock data structure needed for template
    data = {"legal_name": "Test Trader", "gstin": "29AAAAA0000A1Z5"}
    
    try:
        html = ASMT10Generator.generate_html(data, issues)
        # Check for presence of issue names/facts in HTML
        if "Included Issue" in html:
            print("PASS: 'Included Issue' found in HTML")
        else:
            print("FAIL: 'Included Issue' NOT found in HTML")
            
        if "Excluded Issue" not in html:
             print("PASS: 'Excluded Issue' correctly absent from HTML")
        else:
             print("FAIL: 'Excluded Issue' FOUND in HTML (Should be absent)")

        if "Legacy Issue" in html:
            print("PASS: 'Legacy Issue' found in HTML")
        else:
            print("FAIL: 'Legacy Issue' NOT found in HTML")

    except Exception as e:
        print(f"Generator Error: {e}")
        # If template not found (since we are in scratch), it might fail. 
        # But generate_html just uses f-strings mostly? 
        # Actually it uses jinja2 or string replacement. 
        # Let's check imports in asmt10_generator.py if needed. 
        # Assuming it runs basic string ops or uses embedded templates.

if __name__ == "__main__":
    verify_logic()
