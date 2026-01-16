import json
import os
import sys

# Mocking parts of the system to test logic
class MockDB:
    def get_issue(self, issue_id):
        return {
            "issue_id": issue_id,
            "issue_name": f"Template: {issue_id}",
            "templates": {
                "brief_facts_scn": "<p>SCN Facts for {{issue_id}}</p>",
                "grounds": "<p>SCN Grounds</p>"
            }
        }

class MockWorkspace:
    def __init__(self):
        self.db = MockDB()
    
    # Copying build_scn_issue_from_asmt10 from proceedings_workspace.py
    def build_scn_issue_from_asmt10(self, asmt_record: dict) -> dict:
        issue_id = asmt_record['issue_id']
        asmt_data = asmt_record['data']

        scn_template = self.db.get_issue(issue_id)
        
        if not scn_template or not scn_template.get('templates'):
             scn_template = {
                 'issue_id': issue_id,
                 'issue_name': asmt_data.get('issue', asmt_data.get('category', 'Issue')),
                 'templates': {
                     'brief_facts_scn': "<b>Brief Facts:</b><br><br>",
                     'grounds': "<b>Grounds:</b><br><br>",
                     'legal': "<b>Legal Provisions:</b><br><br>",
                     'conclusion': "<b>Conclusion:</b><br><br>"
                 }
             }
        
        factual_tables = asmt_data.get('tables') or asmt_data.get('grid_data') or []
        
        variables = {
            'brief_facts': "",
            'grounds': "",
            'legal_provisions': "",
            'conclusion': ""
        }
        
        return {
            'template': scn_template,
            'data': {
                'issue_id': issue_id,
                'origin': 'ASMT10',
                'table_data': factual_tables,
                'variables': variables,
                'status': 'ACTIVE',
                'source_issue_id': issue_id
            }
        }

# Test Record (Simulating Kaitharan Point 12)
asmt_record = {
    'issue_id': 'ITC_MISMATCH',
    'data': {
        'category': 'GSTR 3B vs 2B',
        'total_shortfall': 12000,
        'grid_data': [[{'var': 'TAX', 'value': 12000}]]
    }
}

ws = MockWorkspace()
output = ws.build_scn_issue_from_asmt10(asmt_record)

print("--- ADAPTER OUTPUT ---")
print(json.dumps(output, indent=2))

# Verify rules
print("\n--- VERIFICATION ---")
print(f"Template Resolved: {output['template']['issue_name']}")
print(f"Table Data Carried: {output['data']['table_data'] == asmt_record['data']['grid_data']}")
print(f"Variables Initialized Empty: {all(v == '' for v in output['data']['variables'].values())}")
