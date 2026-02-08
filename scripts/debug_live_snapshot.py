
import sys
import os
import json
import re

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.formatting import format_indian_number

# Mock ASMT10Generator to test local logic
class GeneratorMock:
    @staticmethod
    def _generate_grid_table(grid_data_dict):
        if not grid_data_dict: return ""
        rows = grid_data_dict.get('rows', [])
        columns = grid_data_dict.get('columns', [])
        if not rows and not columns: return ""
        html = '<table class="data-table">'
        if columns:
             html += "<tr>"
             for col_cell in columns:
                 html += f'<th>{col_cell}</th>'
             html += "</tr>"
        for row in rows:
            html += "<tr>"
            for c_index, col_def in enumerate(columns):
                col_id = f"col{c_index}"
                cell = row.get(col_id, {})
                val = cell.get('value', '') if isinstance(cell, dict) else cell
                html += f'<td>{val}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    @staticmethod
    def generate_issue_table_html(issue):
        summary_table = issue.get('summary_table')
        if summary_table:
            return GeneratorMock._generate_grid_table(summary_table)
        return "DATA_UNAVAILABLE"

    @staticmethod
    def generate_html(data, issues):
        def robust_float(val):
            if val is None: return 0.0
            try: return float(str(val).replace(',', '').strip())
            except: return 0.0

        active_issues = [i for i in issues if robust_float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)]
        total_tax = sum(robust_float(i.get('total_shortfall', 0)) for i in active_issues)
        issues_count = len(active_issues)
        intro_text = f"the {issues_count} discrepancies" if issues_count > 0 else "discrepancies"

        issue_sections = ""
        for idx, issue in enumerate(active_issues, 1):
            raw_name = issue.get('category') or issue.get('issue_name') or "Unknown Issue"
            issue_name = re.sub(r'^Point \d+- ?', '', raw_name, flags=re.IGNORECASE)
            section_html = f"""
            <div class="issue-block">
                <p><strong>Issue {idx} – {issue_name}</strong></p>
                <p>Tax: {format_indian_number(robust_float(issue.get('total_shortfall', 0)), prefix_rs=False)}</p>
                <div>{issue.get('description', '')}</div>
            """
            section_html += GeneratorMock.generate_issue_table_html(issue)
            section_html += "</div>"
            issue_sections += section_html

        html = f"""
        <html><body>
        <p>Intro: {intro_text}</p>
        {issue_sections}
        <p>Total: {total_tax}</p>
        </body></html>
        """
        return html

# Load live data
with open('case_snapshot_dump.txt', 'r', encoding='utf-8-sig') as f:
    snapshot = json.load(f)

case_data = snapshot['case_data']
issues = snapshot['issues']

html = GeneratorMock.generate_html(case_data, issues)

print(f"Generated HTML containing issue blocks: {'issue-block' in html}")
print(f"Number of issue blocks: {html.count('issue-block')}")
print("-" * 20)
print(html)
