import sqlite3
import json
import os

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(BASE_DIR, 'data', 'adjudication.db')

def get_strict_table_def_point_1():
    return {
        "columns": [
            {"id": "desc", "label": "Description", "type": "text"},
            {"id": "igst", "label": "IGST", "type": "currency"},
            {"id": "cgst", "label": "CGST", "type": "currency"},
            {"id": "sgst", "label": "SGST", "type": "currency"},
            {"id": "cess", "label": "Cess", "type": "currency"}
        ],
        "rows": [
            {
                "row_id": "r1", 
                "label": "Tax Liability (GSTR-1)", 
                "source": "facts.gstr1"
            },
            {
                "row_id": "r2", 
                "label": "Tax Paid (GSTR-3B)", 
                "source": "facts.gstr3b"
            },
            {
                "row_id": "r3", 
                "label": "Shortfall / (Excess)", 
                "source": "facts.shortfall", 
                "semantics": {"emphasis": "primary", "severity": "critical", "condition": "is_positive"}
            }
        ]
    }

def get_grid_schema_summary_3x4(headers):
    """
    Standard 3x4 summary table structure (actually 3 rows + header, for 5 cols)
    Description | IGST | CGST | SGST | Cess
    """
    grid = []
    # Header Row
    grid.append([{"value": h, "type": "static", "style": "header"} for h in headers])
    
    # Data Rows (Placeholders for snapshot injection)
    rows = [
        "RCM Tax liability as declared in Table 3.1(d) of GSTR-3B",
        "ITC availed in Tables 4(A)(2) and 4(A)(3) of GSTR-3B",
        "Difference (ITC Availed - RCM Liability)",
        "Liability (Positive Shortfall Only)"
    ]
    for i, r_desc in enumerate(rows):
        grid.append([
            {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cgst"}, # CGST First
            {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        ])
    return grid

def get_grid_schema_point_12():
    """Point 12 uses a 4-row summary table"""
    headers = ["Description", "IGST", "CGST", "SGST", "Cess"]
    grid = []
    grid.append([{"value": h, "type": "static", "style": "header"} for h in headers])
    
    rows = [
        "ITC as per Table 8A of GSTR 9",
        "ITC as per Table 8B of GSTR 9",
        "ITC as per Table 8C of GSTR 9",
        "ITC availed in Excess as per GSTR 9"
    ]
    for i, r_desc in enumerate(rows):
        grid.append([
            {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        ])
    return grid

def get_list_schema(headers):
    grid = []
    grid.append([{"value": h, "type": "static", "style": "header"} for h in headers])
    for i in range(1, 6): # Placeholder for 5 rows
        grid.append([{"value": "", "type": "input", "var": f"row{i}_col{j}"} for j in range(len(headers))])
    return grid

def get_grid_schema_liability_1():
    """
    Specific 3x4 summary table for Outward Liability Mismatch (GSTR 3B vs GSTR 1)
    Description | IGST | CGST | SGST | Cess
    """
    headers = ["Description", "IGST", "CGST", "SGST", "Cess"]
    grid = []
    # Header Row
    grid.append([{"value": h, "type": "static", "style": "header"} for h in headers])
    
    # Data Rows
    rows = ["As per GSTR-3B", "As per GSTR-1", "Shortfall / Difference"]
    for i, r_desc in enumerate(rows):
        grid.append([
            {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        ])
    return grid

issues = [
    {"issue_id": "LIABILITY_3B_R1", "issue_name": "Outward Liability Mismatch (GSTR 3B vs GSTR 1)", "sop_point": 1, "grid_data": get_grid_schema_liability_1(), 
     "table_definition": get_strict_table_def_point_1(), "analysis_type": "auto", "sop_version": "CBIC_SCRUTINY_SOP_2024.1", "applicable_from_fy": "2017-18"},
    {"issue_id": "RCM_LIABILITY_ITC", "issue_name": "RCM Liability mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 2, "grid_data": get_grid_schema_summary_3x4(["Description", "IGST", "CGST", "SGST", "Cess"])},
    {"issue_id": "ISD_CREDIT_MISMATCH", "issue_name": "ISD Credit mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 3, "grid_data": get_grid_schema_summary_3x4(["Description", "IGST", "CGST", "SGST", "Cess"])},
    {"issue_id": "ITC_3B_2B_OTHER", "issue_name": "All Other ITC Mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 4, "grid_data": []},
    {"issue_id": "TDS_TCS_MISMATCH", "issue_name": "TDS/TCS Credit mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 5, "grid_data": []},
    {"issue_id": "EWAY_BILL_MISMATCH", "issue_name": "E-Waybill Comparison (GSTR 3B vs E-Waybill)", "sop_point": 6, "grid_data": get_grid_schema_summary_3x4(["Description", "IGST", "CGST", "SGST", "Cess"])},
    {"issue_id": "CANCELLED_SUPPLIERS", "issue_name": "ITC from Cancelled Suppliers", "sop_point": 7, "grid_data": get_list_schema(["GSTIN", "Supplier Name", "ITC Availed"])},
    {"issue_id": "NON_FILER_SUPPLIERS", "issue_name": "ITC from Non-Filing Suppliers", "sop_point": 8, "grid_data": get_list_schema(["GSTIN", "Supplier Name", "ITC Availed"])},
    {"issue_id": "SEC_16_4_VIOLATION", "issue_name": "Section 16(4) ITC Violation", "sop_point": 9, "grid_data": []},
    {"issue_id": "IMPORT_ITC_MISMATCH", "issue_name": "Import ITC Mismatch (GSTR 3B vs ICEGATE)", "sop_point": 10, "grid_data": get_grid_schema_summary_3x4(["Description", "IGST", "CGST", "SGST", "Cess"])},
    {"issue_id": "RULE_42_43_VIOLATION", "issue_name": "Rule 42/43 Reversal Mismatch", "sop_point": 11, "grid_data": []},
    {"issue_id": "ITC_3B_2B_9X4", "issue_name": "GSTR 3B vs 2B (discrepancy identified from GSTR 9)", "sop_point": 12, "grid_data": get_grid_schema_point_12()}
]

# Add default templates
for issue in issues:
    issue['templates'] = {
        "brief_facts": f"Discrepancy identified in {issue['issue_name']}.",
        "scn": f"On examination of returns, a discrepancy related to {issue['issue_name']} was identified."
    }
    if issue['issue_id'] == "ITC_3B_2B_9X4":
        issue['templates']['scn'] = "Table 8 of the Annual Return (GSTR-9) filed by you shows that the total ITC availed via GSTR-3B (Table 8B + 8C) exceeds the cumulative ITC available as per GSTR-2A (Table 8A) by ₹ {{total_shortfall}}."
        issue['tax_demand_mapping'] = {
            "IGST": "row4_igst",
            "CGST": "row4_cgst",
            "SGST": "row4_sgst",
            "Cess": "row4_cess"
        }

def run_init():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for issue in issues:
        # Defaults
        tbl_def = json.dumps(issue.get('table_definition', {}))
        an_type = issue.get('analysis_type', 'auto')
        sop_ver = issue.get('sop_version')
        app_fy = issue.get('applicable_from_fy')

        c.execute("""
            INSERT OR REPLACE INTO issues_master (
                issue_id, issue_name, category, sop_point, 
                table_definition, analysis_type, sop_version, applicable_from_fy,
                templates, grid_data, updated_at
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            issue['issue_id'], 
            issue['issue_name'], 
            "Scrutiny Summary", 
            issue['sop_point'],
            tbl_def, an_type, sop_ver, app_fy,
            json.dumps(issue.get('templates', {})),
            json.dumps(issue.get('grid_data', []))
        ))
        
        # Legacy Sync (Optional but keeps issues_data alive if used elsewhere)
        issue_payload = { "issue_id": issue['issue_id'], "issue_name": issue['issue_name'], "grid_data": issue['grid_data'], "templates": issue['templates'] }
        c.execute("INSERT OR REPLACE INTO issues_data (issue_id, issue_json) VALUES (?, ?)", (issue['issue_id'], json.dumps(issue_payload)))
    conn.commit()
    conn.close()
    print(f"Initialized {len(issues)} Scrutiny Points.")

if __name__ == "__main__":
    run_init()
