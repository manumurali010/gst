import os
import sys
from src.utils.document_generator import DocumentGenerator

# Mock ConfigManager to return default letterhead path
class MockConfig:
    def get_letterhead_path(self, fmt):
        return r"c:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System\templates\letterheads\default.html"

def test_robust_pdf():
    doc_gen = DocumentGenerator()
    config = MockConfig()
    
    # 1. Generate DRC-01A HTML (Mocking generate_drc01a_html)
    # Using the EXACT content from drc_01a.html as it is on disk now
    with open(r"c:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System\templates\drc_01a.html", "r") as f:
        html_template = f.read()
        
    # Mock replacements
    html = html_template.replace("{{SelectedSection}}", "Section 73(5)")
    html = html.replace("{{OCNumber}}", "12345")
    html = html.replace("{{CurrentDate}}", "27/11/2025")
    html = html.replace("{{GSTIN}}", "29ABCDE1234F1Z5")
    html = html.replace("{{LegalName}}", "Test Company")
    html = html.replace("{{Address}}", "Test Address")
    html = html.replace("{{GroundsContent}}", "Test Grounds")
    html = html.replace("{{AdviceText}}", "Test Advice")
    html = html.replace("{{ComplianceDate}}", "27/12/2025")
    
    # Mock tax rows - STRESS TEST: Add many rows to force page break
    tax_rows = ""
    for i in range(50):
        tax_rows += f"""
            <tr>
                <td style="border: 1px solid #000; padding: 4px;">CGST Act {i}</td>
                <td style="border: 1px solid #000; padding: 4px;">2023-24</td>
                <td style="border: 1px solid #000; padding: 4px;">1,000</td>
                <td style="border: 1px solid #000; padding: 4px;">100</td>
                <td style="border: 1px solid #000; padding: 4px;">100</td>
                <td style="border: 1px solid #000; padding: 4px;">1,200</td>
            </tr>
        """
    tax_rows += """
        <tr style="font-weight: bold; background-color: #f9f9f9;">
            <td colspan="2" style="border: 1px solid #000; padding: 4px; text-align: right;">Total</td>
            <td style="border: 1px solid #000; padding: 4px;">50,000</td>
            <td style="border: 1px solid #000; padding: 4px;">5,000</td>
            <td style="border: 1px solid #000; padding: 4px;">5,000</td>
            <td style="border: 1px solid #000; padding: 4px;">60,000</td>
        </tr>
    """
    html = html.replace("{{TaxTableRows}}", tax_rows)
    
    # 2. Inject Letterhead (Mocking adjudication_wizard.py logic)
    letterhead_path = config.get_letterhead_path('pdf')
    with open(letterhead_path, 'r', encoding='utf-8') as f:
        letterhead_full = f.read()
        
    import re
    match = re.search(r'(<div class="letterhead">.*?</div>)', letterhead_full, re.DOTALL)
    if match:
        letterhead_div = match.group(1)
    else:
        letterhead_div = "<div style='text-align:center'><h1>GOVERNMENT OF INDIA</h1></div>"
        
    html_content = html.replace(
        '<div id="letterhead-placeholder"></div>',
        letterhead_div
    )
    
    # 3. Generate PDF
    print("Generating PDF...")
    try:
        path = doc_gen.generate_pdf_from_html(html_content, "debug_robust_output")
        print(f"Success! PDF generated at: {path}")
    except Exception as e:
        print("Exception occurred:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_robust_pdf()
