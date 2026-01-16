import json
from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

# Mock 2A Analyzer to return valid data for SOP-7
class MockAnalyzer:
    def analyze_sop(self, sop_id):
        if sop_id == 7:
            return {
                'rows': [{'gstin': 'G1', 'invoice_no': 'I1', 'invoice_date': '2023-01-01', 'cancellation_date': '2022-12-31', 'igst': 100, 'cgst': 0, 'sgst': 0}],
                'total_liability': 100,
                'status': 'fail'
            }
        return {}

def diagnose():
    parser = ScrutinyParser()
    
    # Simulate SOP-7 (Cancelled)
    # We can rely on the logic we just wrote, but let's confirm the parser output structure
    print("--- SOP-7 PAYLOAD DIAGNOSIS ---")
    mock_analyzer = MockAnalyzer()
    
    # We need to trick parser.parse_file into running SOP-7
    # It requires file_path (doesn't matter if we mock) or we can call the block logic?
    # Parsing the whole file is complex because of file I/O.
    # Let's inspect the code or try to run parse_file with a dummy file?
    # No, let's just inspect the logic we verified in previous step.
    # SOP-7 Output has 'tables' key (Verified).
    
    # Simulate SOP-3 (ISD Credit)
    # Parser logic:
    # res = { ..., "summary_table": {Columns, Rows}, ... }
    # It does NOT generate 'tables' or 'grid_data' keys.
    # So if passed to IssueCard:
    # IssueCard(template=res)
    # init_ui checks:
    # 1. grid_data? No.
    # 2. tables? No.
    # 3. tables (dict)? No.
    # 4. placeholders? Maybe (if mapped from template DB or default).
    
    # Wait, if SOP-3 has NO visible table in IssueCard, that's a finding.
    # But the user says "despite similar data structures". This implies SOP-3 HAS a table.
    
    # Let's check if 'summary_3x4' template type injects grid_data?
    # Or if the DB template for 'ISD_CREDIT_MISMATCH' has 'grid_data'?
    # Ah! The IssueCard merges template + data.
    # self.template = template.
    # If the parser result IS the template (in SCN flow), then it lacks grid_data.
    # BUT, in normal Scrutiny flow, IssueCard might be initialized with a DB template?
    # No, ScrutinyTab.add_result calls IssueCard(issue_data).
    
    # Let's verify what keys SOP-3 has in ScrutinyParser.
    # It definitely has "summary_table".
    
    print("\n--- HYPOTHESIS ---")
    print("SOP-7 uses 'tables' (List of Dicts).")
    print("SOP-3 uses 'summary_table' (Dict).")
    print("IssueCard Logic:")
    print("  - Checks 'grid_data'")
    print("  - Checks 'tables' (List)")
    print("  - Checks 'tables' (Dict) -> init_excel_table_ui")
    
    print("Critique: SOP-3 'summary_table' matches NONE of these if key is 'summary_table'.")
    print("UNLESS 'summary_table' is renamed to 'tables' or 'grid_data' somewhere?")
    
    # Let's checking if IssueCard maps 'summary_table' to 'grid_data'?
    # It does NOT in the code I read.
    
    # Does 'CompliancePointCard' handle 'summary_table'? YES.
    # CompliancePointCard.set_status handles 'summary_table' (Line 1003).
    # AND it calls `render_grid_to_table_widget`.
    
    print("\n--- CONCLUSION ---")
    print("User is asking about ComplianceDashboard (Accordion), NOT IssueCard (SCN).")
    print("SOP-7 (tables) uses HTML Renderer (Priority 0 in CompliancePointCard).")
    print("SOP-3 (summary_table) uses Native QTableWidget (Fallback in CompliancePointCard).")
    
diagnose()
