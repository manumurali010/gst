import sys
import os
import json
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.ui.issue_card import IssueCard
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    # Load Imported JSON
    try:
        with open('data/issues_from_excel.json', 'r') as f:
            data = json.load(f)
            issues = data['issues']
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        sys.exit(1)
        
    if not issues:
        print("No issues found in JSON")
        sys.exit(1)
        
    # Check Metadata for First Issue
    issue = issues[0]
    print(f"Checking Metadata for: {issue['issue_name']}")
    
    # Check if Brief Facts is populated (should be from Col B)
    brief_facts = issue['templates'].get('brief_facts', '')
    if brief_facts:
        print(f"Brief Facts Found: {brief_facts[:50]}...")
    else:
        print("WARNING: Brief Facts is empty!")
        
    # Check Legal Provisions
    legal = issue['templates'].get('legal', '')
    if legal:
        print(f"Legal Provisions Found: {legal[:50]}...")
    else:
        print("WARNING: Legal Provisions is empty!")
        
    # Create IssueCard and Generate HTML
    card = IssueCard(issue)
    
    # Set some values to test dynamic HTML generation
    # Find an input variable
    grid_data = issue['grid_data']
    input_var = None
    for row in grid_data:
        for cell in row:
            if cell['type'] == 'input':
                input_var = cell['var']
                break
        if input_var: break
        
    if input_var:
        print(f"Setting {input_var} to 9999")
        card.variables[input_var] = 9999
        
    html = card.generate_html()
    
    # Verify HTML contains the table and the value
    if "<table" in html:
        print("SUCCESS: HTML contains <table>")
    else:
        print("FAILURE: HTML does not contain <table>")
        
    if "9999" in html:
        print("SUCCESS: HTML contains set value 9999")
    else:
        print("FAILURE: HTML does not contain set value 9999")
        
    # Save HTML for inspection
    with open('verify_output.html', 'w') as f:
        f.write(html)
    print("Saved HTML to verify_output.html")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
