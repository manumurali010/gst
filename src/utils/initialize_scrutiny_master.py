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
    # Define Columns
    columns = []
    # Map colloquial headers to IDs if possible, else generic
    for idx, h in enumerate(headers):
         kv_id = h.lower().replace(" ", "_")
         columns.append({"id": kv_id, "label": h, "type": "input"})

    # Data Rows (Placeholders for snapshot injection)
    rows_data = [
        "RCM Tax liability as declared in Table 3.1(d) of GSTR-3B",
        "ITC availed in Tables 4(A)(2) and 4(A)(3) of GSTR-3B",
        "Difference (ITC Availed - RCM Liability)",
        "Liability (Positive Shortfall Only)"
    ]
    
    rows = []
    for i, r_desc in enumerate(rows_data):
        # Row Object
        row_obj = {
            "id": f"r{i+1}",
            # Cells using column IDs
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "cgst": {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            "sgst": {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            "cess": {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        }
        rows.append(row_obj)
        
    return {"columns": columns, "rows": rows}

def get_grid_schema_point_12():
    """Point 12 uses a 4-row summary table"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "cgst", "label": "CGST", "type": "currency"},
        {"id": "sgst", "label": "SGST", "type": "currency"},
        {"id": "igst", "label": "IGST", "type": "currency"},
        {"id": "cess", "label": "Cess", "type": "currency"}
    ]
    
    rows_data = [
        "ITC as per Table 8A of GSTR 9",
        "ITC as per Table 8B of GSTR 9",
        "ITC as per Table 8C of GSTR 9",
        "ITC availed in Excess as per GSTR 9"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
        row_obj = {
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "cgst": {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            "sgst": {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            "cess": {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        }
        rows.append(row_obj)

    return {"columns": columns, "rows": rows}

def get_list_schema(headers):
    columns = []
    for idx, h in enumerate(headers):
         kv_id = h.lower().replace(" ", "_").replace("-", "_")
         columns.append({"id": kv_id, "label": h, "type": "input"})
         
    rows = []
    for i in range(1, 6): # Placeholder for 5 rows
        row_obj = {"id": f"r{i}"}
        # Pre-fill empty cells for structure
        for col in columns:
             row_obj[col["id"]] = {"value": "", "type": "input"}
        rows.append(row_obj)
        
    return {"columns": columns, "rows": rows}

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

def get_grid_schema_sop1():
    """SOP 1: Outward Liability Mismatch (GSTR 3B vs GSTR 1)"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "cgst", "label": "CGST", "type": "currency"},
        {"id": "sgst", "label": "SGST", "type": "currency"},
        {"id": "igst", "label": "IGST", "type": "currency"},
        {"id": "cess", "label": "Cess", "type": "currency"}
    ]
    rows_data = [
        "Tax Liability Declared as per GSTR-1",
        "Tax Liability as per GSTR-3B",
        "Difference (Declared - Reported)",
        "Liability (Positive Only)"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
        rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "cgst": {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            "sgst": {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            "cess": {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop3():
    """SOP 3: ISD Credit mismatch"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "cgst", "label": "CGST", "type": "currency"},
        {"id": "sgst", "label": "SGST", "type": "currency"},
        {"id": "igst", "label": "IGST", "type": "currency"},
        {"id": "cess", "label": "Cess", "type": "currency"}
    ]
    rows_data = [
        "ITC availed i.r.o of 'Inward Supplies from ISD' in Table 4(A)(4) of GSTR-3B",
        "ITC as per GSTR-2B ISD",
        "Difference (Claimed - Available)",
        "Liability (Positive Shortfall)"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
         rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "cgst": {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            "sgst": {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            "cess": {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop4():
    """SOP 4: All Other ITC Mismatch"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "cgst", "label": "CGST", "type": "currency"},
        {"id": "sgst", "label": "SGST", "type": "currency"},
        {"id": "igst", "label": "IGST", "type": "currency"},
        {"id": "cess", "label": "Cess", "type": "currency"}
    ]
    rows_data = [
        "ITC claimed in GSTR-3B (Table 4A5)",
        "ITC available in GSTR-2B (Net of Credit Notes)",
        "Difference (GSTR 3B - GSTR 2B)",
        "Liability"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
         rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "cgst": {"value": 0, "type": "input", "var": f"row{i+1}_cgst"},
            "sgst": {"value": 0, "type": "input", "var": f"row{i+1}_sgst"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"},
            "cess": {"value": 0, "type": "input", "var": f"row{i+1}_cess"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop5():
    """SOP 5: TDS/TCS Credit mismatch (2-column Taxable Value comparison)"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "amount", "label": "Amount (Rs.)", "type": "currency"}
    ]
    rows_data = [
        "--- TDS Mismatch (Section 51) ---",
        "Taxable Value (TDS Credit) – from GSTR-2A",
        "Taxable Value as per Table 3.1(a) of GSTR-3B",
        "Difference (2A - 3B)",
        "Liability",
        "", 
        "--- TCS Mismatch (Section 52) ---",
        "Net Amount Liable for TCS – from GSTR-2A",
        "Taxable Value as per Table 3.1(a) of GSTR-3B",
        "Difference (2A - 3B)",
        "Liability"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
         rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "amount": {"value": 0, "type": "input", "var": f"row{i+1}_amount"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop10():
    """SOP 10: Import ITC Mismatch (IGST Only)"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "igst", "label": "IGST", "type": "currency"}
    ]
    rows_data = [
        "ITC claimed in GSTR-3B (Table 4(A)(1))",
        "ITC available as per GSTR-2B (IMPG + IMPGSEZ)",
        "Difference (GSTR-3B - GSTR-2B)",
        "Liability (Positive Shortfall Only)"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
        rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "igst": {"value": 0, "type": "input", "var": f"row{i+1}_igst"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop11():
    """SOP 11: Rule 42/43 Reversal Mismatch"""
    columns = [
        {"id": "description", "label": "Description", "type": "text"},
        {"id": "amount", "label": "Amount (Rs.)", "type": "currency"}
    ]
    rows_data = [
        "Exempt + Non-GST Turnover (3.1c + 3.1e)",
        "Total Turnover (3.1a + b + c + d + e)",
        "Reversal Ratio (Exempt / Total)",
        "Total ITC Availed (Table 4(A)(1)-(5))",
        "ITC Required to be Reversed",
        "ITC Actually Reversed (Table 4(B)(1))",
        "Difference (Required - Actual)",
        "Liability (Payable)"
    ]
    rows = []
    for i, r_desc in enumerate(rows_data):
        rows.append({
            "id": f"r{i+1}",
            "description": {"value": r_desc, "type": "static", "var": f"row{i+1}_desc"},
            "amount": {"value": 0, "type": "input", "var": f"row{i+1}_amount"}
        })
    return {"columns": columns, "rows": rows}

def get_grid_schema_sop7_cancelled():
    """SOP 7: Cancelled Suppliers (User Req: Effective Date of Cancellation)"""
    headers = ["GSTIN", "Invoice No.", "Invoice Date", "Effective Date of Cancellation", "CGST", "SGST", "IGST"]
    columns = []
    for h in headers:
        kv_id = h.lower().replace(" ", "_").replace(".", "")
        if "gstin" in kv_id: kv_id = "gstin"
        elif "invoice_no" in kv_id: kv_id = "invoice_no"
        elif "invoice_date" in kv_id: kv_id = "invoice_date"
        elif "cancellation" in kv_id: kv_id = "cancellation_date"
        columns.append({"id": kv_id, "label": h, "type": "input"})
    
    rows = []
    for i in range(1, 6):
        row_obj = {"id": f"r{i}"}
        for col in columns:
             row_obj[col["id"]] = {"value": "", "type": "input"}
        rows.append(row_obj)
    return {"columns": columns, "rows": rows, "row_policy": "dynamic"}

def get_grid_schema_sop8_non_filer():
    """SOP 8: Non-Filer (User Req: GSTR 2A Period, Taxable Value)"""
    headers = ["GSTR 2A Period", "GSTIN", "Invoice Number", "Invoice Date", "Taxable Value", "CGST", "SGST", "IGST"]
    columns = []
    for h in headers:
        kv_id = h.lower().replace(" ", "_").replace(".", "")
        if "period" in kv_id: kv_id = "period"
        elif "gstin" in kv_id: kv_id = "gstin"
        elif "invoice_number" in kv_id: kv_id = "invoice_no"
        elif "invoice_date" in kv_id: kv_id = "invoice_date"
        elif "taxable" in kv_id: kv_id = "taxable_value"
        columns.append({"id": kv_id, "label": h, "type": "input"})
        
    rows = []
    for i in range(1, 6):
        row_obj = {"id": f"r{i}"}
        for col in columns:
             row_obj[col["id"]] = {"value": "", "type": "input"}
        rows.append(row_obj)
    return {"columns": columns, "rows": rows, "row_policy": "dynamic"}

def get_grid_schema_sop9_sec16_4():
    """SOP 9: Sec 16(4) (User Req: Cut off Date)"""
    headers = ["Tax Period", "Due Date of Filing Return", "Actual Date of Filing Return", "Cut off Date of availing ITC", "CGST", "SGST", "IGST"]
    columns = []
    for h in headers:
        kv_id = h.lower().replace(" ", "_").replace("-", " ")
        kv_id = kv_id.replace(" ", "_")
        # Manual mapping to backend keys if needed, else strict slug
        columns.append({"id": kv_id, "label": h, "type": "input"})
        
    rows = []
    for i in range(1, 6):
        row_obj = {"id": f"r{i}"}
        for col in columns:
             row_obj[col["id"]] = {"value": "", "type": "input"}
        rows.append(row_obj)
    return {"columns": columns, "rows": rows, "row_policy": "dynamic"}

issues = [
    {"issue_id": "LIABILITY_3B_R1", "issue_name": "Outward Liability Mismatch (GSTR 3B vs GSTR 1)", "sop_point": 1, "grid_data": get_grid_schema_sop1(), 
     "table_definition": get_strict_table_def_point_1(), "analysis_type": "auto", "sop_version": "CBIC_SCRUTINY_SOP_2024.1", "applicable_from_fy": "2017-18",
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST", "CGST", "SGST", "Cess"]}},
    {"issue_id": "RCM_LIABILITY_ITC", "issue_name": "RCM Liability mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 2, "grid_data": get_grid_schema_summary_3x4(["Description", "IGST", "CGST", "SGST", "Cess"]),
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST", "CGST", "SGST", "Cess"]}},
    {"issue_id": "ISD_CREDIT_MISMATCH", "issue_name": "ISD Credit mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 3, "grid_data": get_grid_schema_sop3(),
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST", "CGST", "SGST", "Cess"]}},
    {"issue_id": "ITC_3B_2B_OTHER", "issue_name": "All Other ITC Mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 4, "grid_data": get_grid_schema_sop4(),
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST", "CGST", "SGST", "Cess"]}},
    {"issue_id": "TDS_TCS_MISMATCH", "issue_name": "TDS/TCS Credit mismatch (GSTR 3B vs GSTR 2B)", "sop_point": 5, "grid_data": get_grid_schema_sop5(),
     "liability_config": {"model": "multiple_rows", "row_indices": [4, 10], "column_heads": ["Amount"]}},
    {"issue_id": "EWAY_BILL_MISMATCH", "issue_name": "E-Waybill Comparison (GSTR 3B vs E-Waybill)", "sop_point": 6, "grid_data": []},
    {"issue_id": "CANCELLED_SUPPLIERS", "issue_name": "ITC from Cancelled Suppliers", "sop_point": 7, "grid_data": get_grid_schema_sop7_cancelled(),
     "liability_config": {"model": "sum_of_rows", "row_indices": "all_data_rows", "column_heads": ["IGST", "CGST", "SGST"]}},
    {"issue_id": "NON_FILER_SUPPLIERS", "issue_name": "ITC from Non-Filing Suppliers", "sop_point": 8, "grid_data": get_grid_schema_sop8_non_filer(),
     "liability_config": {"model": "sum_of_rows", "row_indices": "all_data_rows", "column_heads": ["IGST", "CGST", "SGST"]}},
    {"issue_id": "SEC_16_4_VIOLATION", "issue_name": "Section 16(4) ITC Violation", "sop_point": 9, "grid_data": get_grid_schema_sop9_sec16_4(),
     "liability_config": {"model": "sum_of_rows", "row_indices": "all_data_rows", "column_heads": ["IGST", "CGST", "SGST"]}},
    {"issue_id": "IMPORT_ITC_MISMATCH", "issue_name": "Import ITC Mismatch (GSTR 3B vs ICEGATE)", "sop_point": 10, "grid_data": get_grid_schema_sop10(),
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST"]}},
    {"issue_id": "RULE_42_43_VIOLATION", "issue_name": "Rule 42/43 Reversal Mismatch", "sop_point": 11, "grid_data": get_grid_schema_sop11(),
     "liability_config": {"model": "single_column", "row_indices": [7], "column_heads": ["Amount"]}},
    {"issue_id": "ITC_3B_2B_9X4", "issue_name": "GSTR 3B vs 2B (discrepancy identified from GSTR 9)", "sop_point": 12, "grid_data": get_grid_schema_point_12(),
     "liability_config": {"model": "single_row", "row_indices": [3], "column_heads": ["IGST", "CGST", "SGST", "Cess"]}},
]

# Add default templates
for issue in issues:
    issue['templates'] = {
        "brief_facts": f"Discrepancy identified in {issue['issue_name']}.",
        "brief_facts_scn": f"On examination of returns, a discrepancy related to {issue['issue_name']} was identified.",
        "scn": f"On examination of returns, a discrepancy related to {issue['issue_name']} was identified."
    }
    if issue['issue_id'] == "ITC_3B_2B_9X4":
        issue['templates']['brief_facts_scn'] = "Table 8 of the Annual Return (GSTR-9) filed by you shows that the total ITC availed via GSTR-3B (Table 8B + 8C) exceeds the cumulative ITC available as per GSTR-2A (Table 8A) by ₹ {{total_shortfall}}."
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
                templates, grid_data, liability_config, tax_demand_mapping,
                active, updated_at
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (
            issue['issue_id'], 
            issue['issue_name'], 
            "Scrutiny Summary", 
            issue['sop_point'],
            tbl_def, an_type, sop_ver, app_fy,
            json.dumps(issue.get('templates', {})),
            json.dumps(issue.get('grid_data', [])),
            json.dumps(issue.get('liability_config')),
            json.dumps(issue.get('tax_demand_mapping'))
        ))
        
        # Legacy Sync (Optional but keeps issues_data alive if used elsewhere)
        issue_payload = { 
            "issue_id": issue['issue_id'], 
            "issue_name": issue['issue_name'], 
            "grid_data": issue['grid_data'], 
            "templates": issue['templates'],
            "liability_config": issue.get('liability_config'),
            "tax_demand_mapping": issue.get('tax_demand_mapping')
        }
        c.execute("""
            INSERT OR REPLACE INTO issues_data 
            (issue_id, issue_json, liability_config, tax_demand_mapping) 
            VALUES (?, ?, ?, ?)
        """, (
            issue['issue_id'], 
            json.dumps(issue_payload),
            json.dumps(issue.get('liability_config')),
            json.dumps(issue.get('tax_demand_mapping'))
        ))
    conn.commit()
    conn.close()
    print(f"Initialized {len(issues)} Scrutiny Points.")

if __name__ == "__main__":
    run_init()
