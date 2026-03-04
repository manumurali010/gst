"""
Placeholder Registry Configuration
Centralized definition of standard application placeholders (Metadata, System variables).
Grid variables are dynamically detected during execution.
"""

from typing import List, Dict

# Known Metadata Placeholders mapping standard case information
METADATA_PLACEHOLDERS = [
    {"name": "gstin", "label": "GSTIN", "type": "string", "source": "metadata"},
    {"name": "taxpayer_name", "label": "Taxpayer Name", "type": "string", "source": "metadata"},
    {"name": "trade_name", "label": "Trade Name", "type": "string", "source": "metadata"},
    {"name": "address", "label": "Address", "type": "string", "source": "metadata"},
    {"name": "financial_year", "label": "Financial Year", "type": "string", "source": "metadata"},
    {"name": "case_id", "label": "Case ID", "type": "string", "source": "metadata"},
    {"name": "initiating_section", "label": "Initiating Section", "type": "string", "source": "metadata"},
    {"name": "demand_section", "label": "Demand Section", "type": "string", "source": "metadata"}
]

# Computed/System Level Constants
SYSTEM_PLACEHOLDERS = [
    {"name": "total_shortfall", "label": "Total Shortfall Amount", "type": "currency", "source": "system"},
    {"name": "total_shortfall_formatted", "label": "Total Shortfall (Formatted)", "type": "string", "source": "system"},
    {"name": "summary_table", "label": "Comparison Table", "type": "table", "source": "system"}
]

def get_standard_placeholders() -> List[Dict]:
    """Returns all pre-defined placeholders."""
    return METADATA_PLACEHOLDERS + SYSTEM_PLACEHOLDERS

def group_placeholders_by_category(placeholders: List[Dict]) -> Dict[str, List[Dict]]:
    """Groups a flat list of placeholders into categories for UI rendering."""
    grouped = {
        "Taxpayer Information": [],
        "Return Data & Analysis": [],
        "Tables": [],
        "Other / Detected": []
    }
    
    for p in placeholders:
        name = p.get('name', '')
        source = p.get('source', '')
        
        if source == 'metadata':
            grouped["Taxpayer Information"].append(p)
        elif source == 'system':
            if p.get('type') == 'table':
                grouped["Tables"].append(p)
            else:
                grouped["Return Data & Analysis"].append(p)
        elif source == 'grid':
            grouped["Return Data & Analysis"].append(p)
        else:
            grouped["Other / Detected"].append(p)
            
    # Clean up empty categories
    return {k: v for k, v in grouped.items() if v}
