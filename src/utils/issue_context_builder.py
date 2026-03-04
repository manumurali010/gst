import json

class IssueContextBuilder:
    """
    Responsible for constructing the render context dictionary for issue templates.
    Merges case metadata, analysis engine outputs, and grid_data computed variables.
    """

    @staticmethod
    def build_issue_context(issue_id, case_data, grid_results=None, issue_metadata=None):
        """
        Builds a comprehensive dictionary for Jinja2 template rendering.
        
        Args:
            issue_id (str): The ID of the issue being rendered.
            case_data (dict): Global case metadata (taxpayer details, FY, etc.).
            grid_results (dict): The resolved grid_data containing calculation nodes.
            issue_metadata (dict, optional): Additional issue-specific data from issues_master.
            
        Returns:
            dict: The combined context dictionary.
        """
        context = {}
        
        # 1. Base Case Data (Global Context)
        if case_data:
            # Extract Taxpayer Details gracefully
            tp_details = case_data.get('taxpayer_details', {})
            if isinstance(tp_details, str):
                try:
                    tp_details = json.loads(tp_details)
                except:
                    tp_details = {}
            elif tp_details is None:
                tp_details = {}
                
            context['taxpayer_name'] = case_data.get('legal_name') or tp_details.get('Legal Name', 'Taxpayer')
            context['trade_name'] = case_data.get('trade_name') or tp_details.get('Trade Name', '')
            context['gstin'] = case_data.get('gstin') or tp_details.get('GSTIN', '')
            context['address'] = case_data.get('address') or tp_details.get('Address', '')
            
            context['financial_year'] = case_data.get('financial_year', 'N/A')
            context['case_id'] = case_data.get('case_id', '')
            context['initiating_section'] = case_data.get('initiating_section', '')
            context['adjudication_section'] = case_data.get('adjudication_section', '')

        # 2. Issue Metadata
        context['issue_id'] = issue_id
        if issue_metadata:
            context['issue_name'] = issue_metadata.get('issue_name', 'Issue')
            context['category'] = issue_metadata.get('category', '')
            
        # 3. Grid Data Variables (Calculation Engine Extraction)
        # Extract predefined semantic variables like 'total_shortfall'
        if grid_results:
            # Check for high-level summary fields often injected by analyzers
            if 'total_shortfall' in grid_results:
                context['total_shortfall'] = grid_results['total_shortfall']
            
            # Extract formal 'var' nodes from the grid definition
            rows = grid_results.get('rows', [])
            for row in rows:
                if isinstance(row, dict):
                    for cell_id, cell_data in row.items():
                        if isinstance(cell_data, dict) and cell_data.get('var'):
                            var_name = cell_data['var']
                            var_value = cell_data.get('value', '')
                            # Only set if not explicitly empty, or allow empty if that's the calculated state
                            # We prefer not to overwrite with empty string if we already have it from another source
                            if var_value != '' or var_name not in context:
                                context[var_name] = var_value
        
        # 4. Format numbers for specific keys if needed 
        # (usually done down the pipeline or via Jinja filters, but we ensure string safety)
        # Formatting handles 'Rs.' or grouping if necessary, but Jinja filters are better.
        # For backward compatibility, ensure 'total_shortfall_formatted' exists:
        if 'total_shortfall' in context:
            from src.utils.formatting import format_indian_number
            try:
                context['total_shortfall_formatted'] = format_indian_number(float(context['total_shortfall']), prefix_rs=False)
            except:
                pass

        return context
