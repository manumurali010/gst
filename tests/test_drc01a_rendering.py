import sys
import unittest
from unittest.mock import MagicMock
import os

# Add src to path
sys.path.append(os.path.abspath(os.curdir))

class TestDRC01ARendering(unittest.TestCase):
    def setUp(self):
        # Mock ProceedingsWorkspace for minimal testing
        from src.ui.proceedings_workspace import ProceedingsWorkspace
        # We need to mock the UI elements that _get_drc01a_model reads if we want to test the full chain,
        # but here we'll primarily test the render_drc01a_html with mocked models.
        self.workspace = MagicMock(spec=ProceedingsWorkspace)
        # Use the actual implementation of render_drc01a_html
        self.workspace.render_drc01a_html = ProceedingsWorkspace.render_drc01a_html.__get__(self.workspace)
        
    def test_rendering_with_populated_data(self):
        """Verify that the template renders a table when TaxRows is populated"""
        model = {
            'gstin': '32AAAAA0000A1Z5',
            'legal_name': 'Test Taxpayer',
            'trade_name': 'TP Trade',
            'address': 'Test Address',
            'case_id': 'CASE123',
            'oc_no': 'OC/2024/001',
            'oc_date': '24/02/2026',
            'financial_year': '2023-24',
            'initiating_section': 'Section 73',
            'section_title': 'section 73(5)',
            'section_body': '73(5)',
            'issues_html': '<p>Issue 1 Detail</p>',
            'sections_violated_html': '<ul><li>Section 7</li></ul>',
            'tax_rows': [
                {'Act': 'IGST', 'Period': '2023-24', 'Tax': '1,000', 'Interest': '180', 'Penalty': '0', 'Total': '1,180'},
                {'Act': 'CGST', 'Period': '2023-24', 'Tax': '500', 'Interest': '90', 'Penalty': '0', 'Total': '590'}
            ],
            'grand_total_liability': '1,770',
            'tax_period_from': '01/04/2023',
            'tax_period_to': '31/03/2024',
            'payment_date': '10/03/2026',
            'reply_date': '10/03/2026'
        }
        
        html = self.workspace.render_drc01a_html(model)
        
        # Check for key content
        self.assertIn("32AAAAA0000A1Z5", html)
        self.assertIn("Test Taxpayer", html)
        self.assertIn("IGST", html)
        self.assertIn("1,180", html)
        self.assertIn("CGST", html)
        self.assertIn("590", html)
        self.assertIn("₹ 1,770", html)
        self.assertIn("Grand Total (Ascertained)", html)
        self.assertIn("3. Tax Demand Details", html)

    def test_rendering_with_empty_data(self):
        """Verify that the template handles empty TaxRows gracefully"""
        model = {
            'gstin': '32AAAAA0000A1Z5',
            'legal_name': 'Test Taxpayer',
            'trade_name': '',
            'address': 'Test Address',
            'case_id': 'CASE123',
            'oc_no': 'OC/2024/001',
            'oc_date': '24/02/2026',
            'financial_year': '2023-24',
            'initiating_section': 'Section 73',
            'section_title': 'section 73(5)',
            'section_body': '73(5)',
            'issues_html': '',
            'sections_violated_html': '<i>Not specified</i>',
            'tax_rows': [],
            'grand_total_liability': '0',
            'tax_period_from': '01/04/2023',
            'tax_period_to': '31/03/2024',
            'payment_date': '10/03/2026',
            'reply_date': '10/03/2026'
        }
        
        html = self.workspace.render_drc01a_html(model)
        
        # Check for key content
        self.assertIn("32AAAAA0000A1Z5", html)
        self.assertIn("Test Taxpayer", html)
        self.assertIn("₹ 0", html)
        self.assertIn("Grand Total (Ascertained)", html)
        # Table should still exist but have no body rows (except maybe header/footer)
        self.assertIn("Tax Demand Details", html)

if __name__ == "__main__":
    unittest.main()
