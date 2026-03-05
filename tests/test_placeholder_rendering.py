import unittest
import os
from src.utils.template_engine import TemplateEngine
from src.utils.issue_context_builder import IssueContextBuilder

class TestPlaceholderRendering(unittest.TestCase):
    def setUp(self):
        # Reset caching and set default mode
        IssueContextBuilder._case_cache = {}
        if "GST_TEMPLATE_MODE" in os.environ:
            del os.environ["GST_TEMPLATE_MODE"]
        TemplateEngine.MODE = "PRODUCTION"

    def test_basic_rendering(self):
        template = "GSTIN: {{gstin}}, Taxpayer: {{taxpayer_name}}, Shortfall: {{total_shortfall}}"
        context = {
            'gstin': '07AAAAA0000A1Z5',
            'taxpayer_name': 'M/s Test Taxpayer',
            'total_shortfall': 125000
        }
        rendered = TemplateEngine.render_issue_template(template, context)
        self.assertIn("07AAAAA0000A1Z5", rendered)
        self.assertIn("M/s Test Taxpayer", rendered)
        self.assertIn("125000", rendered)

    def test_formatted_variables(self):
        case_data = {
            'case_id': 'CASE_001',
            'gstin': '07AAAAA0000A1Z5',
            'legal_name': 'Test Corp'
        }
        grid_results = {
            'total_shortfall': 125000
        }
        context = IssueContextBuilder.build_issue_context('ISSUE_1', case_data, grid_results)
        
        template = "Total: {{total_shortfall}}, Formatted: {{total_shortfall_formatted}}"
        rendered = TemplateEngine.render_issue_template(template, context)
        self.assertIn("125000", rendered)
        self.assertIn("1,25,000", rendered)

    def test_production_mode_safe_defaults(self):
        TemplateEngine.MODE = "PRODUCTION"
        template = "Hello {{missing_var}}, Amount: {{total_shortfall_formatted}}"
        context = {}
        rendered = TemplateEngine.render_issue_template(template, context)
        self.assertIn("-", rendered) # Default for generic
        self.assertIn("0", rendered) # Default for formatted/shortfall

    def test_strict_mode_failure(self):
        TemplateEngine.MODE = "STRICT"
        template = "Hello {{missing_var}}"
        context = {}
        with self.assertRaises(ValueError):
            TemplateEngine.render_issue_template(template, context)

    def test_registry_validation_warning(self):
        # We can't easily check logs here without complexity, but we can verify it doesn't crash
        template = "Hello {{typo_var_not_in_registry}}"
        context = {'typo_var_not_in_registry': 'Value'}
        rendered = TemplateEngine.render_issue_template(template, context)
        self.assertEqual(rendered, "Hello Value")

    def test_lazy_table_rendering(self):
        def dummy_gen(template, vars):
            return "<table>Computed</table>"
        
        case_data = {'case_id': 'C1'}
        context = IssueContextBuilder.build_issue_context(
            'I1', case_data, 
            table_generator=(dummy_gen, {}, {})
        )
        
        template_with_table = "Results: {{summary_table}}"
        template_without_table = "No table here"
        
        # Verify rendered correctly when used
        rendered = TemplateEngine.render_issue_template(template_with_table, context)
        self.assertIn("<table>Computed</table>", rendered)
        
        # Verify it doesn't break when not used
        rendered_no_table = TemplateEngine.render_issue_template(template_without_table, context)
        self.assertEqual(rendered_no_table, "No table here")

    def test_case_context_caching(self):
        case_data = {
            'case_id': 'CACHE_TEST',
            'gstin': 'ORIGINAL_GSTIN'
        }
        # First build
        context1 = IssueContextBuilder.build_issue_context('I1', case_data)
        self.assertEqual(context1['gstin'], 'ORIGINAL_GSTIN')
        
        # Modify case_data (simulate same case_id but different object)
        case_data_updated = {
            'case_id': 'CACHE_TEST',
            'gstin': 'UPDATED_GSTIN'
        }
        # Second build should use cached value
        context2 = IssueContextBuilder.build_issue_context('I2', case_data_updated)
        self.assertEqual(context2['gstin'], 'ORIGINAL_GSTIN')

if __name__ == "__main__":
    unittest.main()
