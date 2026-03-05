import json
import logging
from src.utils.formatting import format_indian_number

logger = logging.getLogger(__name__)

class LazyTableWrapper:
    """Lazy wrapper for summary_table to ensure it's only rendered if needed."""
    def __init__(self, generator_func, *args, **kwargs):
        self.generator_func = generator_func
        self.args = args
        self.kwargs = kwargs
        self._rendered = None

    def __str__(self):
        if self._rendered is None:
            try:
                self._rendered = self.generator_func(*self.args, **self.kwargs)
            except Exception as e:
                logger.error(f"Lazy Table Rendering failed: {e}")
                self._rendered = "<!-- Table Generation Error -->"
        return self._rendered

class IssueContextBuilder:
    """
    Responsible for constructing the render context dictionary for issue templates.
    Merges case metadata, analysis engine outputs, and grid_data computed variables.
    Includes case-scoped caching to prevent redundant lookups.
    """
    
    _case_cache = {} # Static cache: {case_id: metadata_dict}

    @staticmethod
    def build_issue_context(issue_id, case_data, grid_results=None, issue_metadata=None, table_generator=None):
        """
        Builds a comprehensive dictionary for Jinja2 template rendering.
        """
        context = {}
        case_id = case_data.get('case_id') if case_data else None

        # 1. Base Case Data (Global Context & Caching)
        metadata = {}
        if case_id and case_id in IssueContextBuilder._case_cache:
            metadata = IssueContextBuilder._case_cache[case_id]
        elif case_data:
            tp_details = case_data.get('taxpayer_details', {})
            if isinstance(tp_details, str):
                try: tp_details = json.loads(tp_details)
                except: tp_details = {}
            
            metadata = {
                'taxpayer_name': case_data.get('legal_name') or tp_details.get('Legal Name', 'Taxpayer'),
                'trade_name': case_data.get('trade_name') or tp_details.get('Trade Name', ''),
                'gstin': case_data.get('gstin') or tp_details.get('GSTIN', ''),
                'address': case_data.get('address') or tp_details.get('Address', ''),
                'financial_year': case_data.get('financial_year', 'N/A'),
                'case_id': case_id,
                'initiating_section': case_data.get('initiating_section', ''),
                'adjudication_section': case_data.get('adjudication_section', '')
            }
            if case_id:
                IssueContextBuilder._case_cache[case_id] = metadata
        
        context.update(metadata)

        # 2. Issue Metadata
        context['issue_id'] = issue_id
        if issue_metadata:
            context['issue_name'] = issue_metadata.get('issue_name', 'Issue')
            context['category'] = issue_metadata.get('category', '')
            
        # 3. Grid Data Variables
        if grid_results:
            if 'total_shortfall' in grid_results:
                context['total_shortfall'] = grid_results['total_shortfall']
            
            rows = grid_results.get('rows', [])
            for row in rows:
                if isinstance(row, dict):
                    for cell_data in row.values():
                        if isinstance(cell_data, dict) and cell_data.get('var'):
                            context[cell_data['var']] = cell_data.get('value', '')

        # 4. Explicit Formatted Values
        if 'total_shortfall' in context:
            try:
                shortfall_val = float(context['total_shortfall'])
                context['total_shortfall_formatted'] = format_indian_number(shortfall_val, prefix_rs=False)
            except:
                pass

        # 5. Lazy System Variables
        if table_generator:
            # table_generator is expected to be a tuple: (func, template_ref, variables_ref)
            gen_func, t_ref, v_ref = table_generator
            context['summary_table'] = LazyTableWrapper(gen_func, t_ref, v_ref)

        return context

