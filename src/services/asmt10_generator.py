from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import QSizeF, QMarginsF
import os
from src.utils.formatting import format_indian_number

class ASMT10Generator:
    """Service to generate ASMT-10 Notices in various formats."""
    
    @staticmethod
    def generate_asmt10_preview(taxpayer, case_data, issues):
        """Wrapper for UI: Merges taxpayer and case data for preview generation."""
        # Merge data sources
        data = {}
        if taxpayer:
            data.update(taxpayer)
            # Ensure keys match template expectations
            data['legal_name'] = taxpayer.get('Legal Name', 'Unknown')
            data['address'] = taxpayer.get('Address', '')
            
        if case_data:
            data.update(case_data)
            
        return ASMT10Generator.generate_html(data, issues)

    @staticmethod
    def generate_issue_table_html(issue):
        """Generates the HTML table for a single issue based on its template type."""
        # DEBUG LOG for SOP-5 UI
        i_id = issue.get('issue_id', 'Unknown')
        stat = issue.get('status', 'Unknown')
        has_tbl = "YES" if ("tables" in issue and issue["tables"]) or ("summary_table" in issue and issue["summary_table"]) else "NO"
        print(f"DEBUG UI: issue_id={i_id}, status={stat}, tables_present={has_tbl}")

        template_type = issue.get('template_type')
        rows = issue.get('rows', [])
        grid_data = issue.get('grid_data') # New authoritative model
        summary_table = issue.get('summary_table')
        
        # Priority 0: Multi-Table Support (SOP-5 Dual Layout)
        if "tables" in issue and isinstance(issue["tables"], list):
            html = ""
            for tbl in issue["tables"]:
                title = tbl.get("title", "")
                if title:
                    html += f"<p><strong>{title}</strong></p>"
                # Render using grid table generator
                html += ASMT10Generator._generate_grid_table(tbl)
            return html

        # Priority 1: If grid_data is present (Master-aligned structure)
        # Priority 1: If grid_data is valid (Master-aligned structure)
        # SUPPORTS: Dict (Canonical) ONLY
        if grid_data and isinstance(grid_data, dict) and "rows" in grid_data:
            return ASMT10Generator._generate_grid_table(grid_data)
        elif grid_data and isinstance(grid_data, list):
             # Legacy List Support (Auto-wrap)
             return ASMT10Generator._generate_grid_table({"columns": [], "rows": grid_data})

        # Priority 2: Summary Table (Treated as Grid Data)
        if summary_table and isinstance(summary_table, dict) and ("rows" in summary_table or "columns" in summary_table):
            return ASMT10Generator._generate_grid_table(summary_table)

        # Priority 3: Legacy List Support in grid_data (Auto-wrap)
        # (This block is redundant if covered above, but ensuring flow)
        
        # Priority 4: Specific Templates (Legacy Fallback - Should be migrated eventually)
        if (template_type == 'liability_monthly' or template_type == 'liability_monthwise' or template_type == 'liability_mismatch') and rows:
            return ASMT10Generator._generate_liability_table(rows, issue.get('labels'))
        elif template_type == 'itc_yearly_summary' and rows:
            return ASMT10Generator._generate_itc_yearly_table(rows)
        elif template_type == 'ineligible_itc' and rows:
            return ASMT10Generator._generate_generic_list_table(rows, ["GSTIN", "Supplier Name", "ITC Availed"])

        # Default Hard Guard: Data Unavailable
        return """
        <div style="border: 1px dashed #bdc3c7; padding: 10px; margin: 10px 0; background-color: #f8f9fa;">
            <p style="margin: 0; color: #7f8c8d; font-style: italic; text-align: center;">
                Detailed calculation data is not available for this issue.<br>
                (Source: Legacy Data or Missing Analysis Payload)
            </p>
        </div>
        """

    @staticmethod
    def _generate_grid_table(grid_data_dict):
        """Generates HTML table from grid_data dict {'columns':..., 'rows':...}"""
        if not grid_data_dict: return ""
        
        rows = grid_data_dict.get('rows', [])
        columns = grid_data_dict.get('columns', []) # Header cells (dicts)
        
        # Guard: Empty table
        if not rows and not columns: return ""
        
        html = '<table class="data-table">'
        
        # 1. Header Row
        if columns:
             html += "<tr>"
             for col_cell in columns:
                 # Support both dict and string headers (though dict is canonical)
                 if isinstance(col_cell, dict):
                     val = col_cell.get('label') or col_cell.get('value', '')
                     width = col_cell.get('width', '')
                     style_attr = f"width: {width};" if width else ""
                 else:
                     val = str(col_cell)
                     style_attr = ""
                     
                 html += f'<th style="{style_attr}">{val}</th>'
             html += "</tr>"
        
        # 2. Data Rows
        for r_index, row in enumerate(rows):
            html += "<tr>"
            
            # Determine how to iterate (Dict vs List)
            # Scenario A: Columns defined -> Iterate columns to get keys
            if columns:
                 for c_index, col_def in enumerate(columns):
                     col_id = col_def.get('id') if isinstance(col_def, dict) else f"col{c_index}"
                     if not col_id: col_id = f"col{c_index}"
                     
                     # Extract Cell
                     if isinstance(row, dict):
                         cell = row.get(col_id, {})
                     elif isinstance(row, list) and c_index < len(row):
                         cell = row[c_index]
                     else:
                         cell = {}
                         
                     # Unwrap Cell (Canonical Dict vs Scalar)
                     if isinstance(cell, dict):
                         val = cell.get('value', '')
                         style = cell.get('style', 'normal')
                         ctype = cell.get('type', 'text')
                     else:
                         val = cell
                         style = 'normal'
                         ctype = 'text'

                     # Detect Type/Formatting
                     is_numeric = isinstance(val, (int, float))
                     val_str = str(val)
                     
                     if is_numeric:
                         # Round floats, use Indian Format, No decimals if integer-ish
                         val_str = format_indian_number(val, prefix_rs=False)
                     
                     # Alignment Logic
                     align = "left"
                     if is_numeric or val_str == "0" or val_str == "0.0":
                         align = "right"
                     
                     # CSS Building
                     css = f"text-align: {align}; padding: 4px;"
                     if style == "bold" or style == "header": css += " font-weight: bold;"
                     if style == "red_bold": css += " font-weight: bold; color: red;"
                     if style == "red": css += " color: red;"
                     
                     html += f'<td style="{css}">{val_str}</td>'
            
            # Scenario B: No Columns defined (Legacy List of Lists)
            else:
                 iter_items = row.values() if isinstance(row, dict) else row
                 for cell in iter_items:
                     # Unwrap Cell
                     if isinstance(cell, dict):
                         val = cell.get('value', '')
                         style = cell.get('style', 'normal')
                     else:
                         val = cell
                         style = 'normal'
                     
                     is_numeric = isinstance(val, (int, float))
                     val_str = str(val)
                     if is_numeric:
                          val_str = format_indian_number(val, prefix_rs=False)
                     
                     align = "right" if is_numeric else "left"
                     css = f"text-align: {align}; padding: 4px;"
                     if style == "bold": css += " font-weight: bold;"
                     
                     html += f'<td style="{css}">{val_str}</td>'

            html += "</tr>"
        html += "</table>"
        
        # 3. Source Metadata (Provenance)
        if rows and len(rows) > 0 and columns:
            first_col_id = columns[0].get('id') if isinstance(columns[0], dict) else "col0"
            if isinstance(rows[0], dict):
                first_cell = rows[0].get(first_col_id)
                # If cell is dict and has source
                if isinstance(first_cell, dict) and first_cell.get("source"):
                    src = first_cell.get("source")
                    origin = src.get("origin", "Unknown")
                    asmt_id = src.get("asmt_id", "N/A")
                    dt = src.get("converted_on", "")
                    if dt and "T" in dt:
                        dt = dt.split("T")[0] # Just the date
                    
                    html += f'<div style="font-size: 8pt; color: #7f8c8d; margin-top: 5px; font-style: italic;">'
                    html += f'Source: {origin} (Case: {asmt_id}) | Converted on: {dt}'
                    html += f'</div>'

        return html



    @staticmethod
    def _generate_generic_list_table(rows, headers):
        """Generates a simple table for list-based data (e.g., Cancelled Suppliers)."""
        html = """
        <table class="data-table">
            <thead>
                <tr>
        """
        for h in headers:
            html += f"<th>{h}</th>"
        html += """
                </tr>
            </thead>
            <tbody>
        """
        for row in rows:
            html += "<tr>"
            # Flexible row handling
            if isinstance(row, dict):
                for key in ["gstin", "name", "itc_availed", "status"]: # Priority order
                    if key in row:
                        val = row[key]
                        if key == "itc_availed":
                             try: val = format_indian_number(float(val), prefix_rs=False)
                             except: pass
                        html += f"<td>{val}</td>"
            html += "</tr>"
            
        html += """
            </tbody>
        </table>
        """
        return html

    @staticmethod
    def _generate_liability_table(rows, labels=None):
        if not labels:
            labels = {
                "3b": "Liability Declared in GSTR-3B",
                "ref": "Liability as per GSTR-1/RCM",
                "diff": "Short Payment (Difference)"
            }
            
        html = f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th rowspan="2">Tax Period</th>
                    <th colspan="4">{labels.get('3b', 'Liability Declared in GSTR-3B')}</th>
                    <th colspan="4">{labels.get('ref', 'Liability as per GSTR-1/RCM')}</th>
                    <th colspan="4">{labels.get('diff', 'Short Payment (Difference)')}</th>
                </tr>
                <tr>
                    <th>IGST</th><th>CGST</th><th>SGST</th><th>Cess</th>
                    <th>IGST</th><th>CGST</th><th>SGST</th><th>Cess</th>
                    <th>IGST</th><th>CGST</th><th>SGST</th><th>Cess</th>
                </tr>
            </thead>
            <tbody>
        """
        # Sum totals for Difference columns
        totals = {"igst": 0, "cgst": 0, "sgst": 0, "cess": 0}
        for r in rows:
            p = r['period']
            d3 = r['3b']
            d1 = r['ref']
            dd = r['diff']
            
            for head in totals:
                totals[head] += dd.get(head, 0)

            html += f"""
            <tr>
                <td>{p}</td>
                <td>{format_indian_number(d3['igst'], prefix_rs=False)}</td><td>{format_indian_number(d3['cgst'], prefix_rs=False)}</td><td>{format_indian_number(d3['sgst'], prefix_rs=False)}</td><td>{format_indian_number(d3['cess'], prefix_rs=False)}</td>
                <td>{format_indian_number(d1['igst'], prefix_rs=False)}</td><td>{format_indian_number(d1['cgst'], prefix_rs=False)}</td><td>{format_indian_number(d1['sgst'], prefix_rs=False)}</td><td>{format_indian_number(d1['cess'], prefix_rs=False)}</td>
                <td style="color:red; font-weight:bold;">{format_indian_number(dd['igst'], prefix_rs=False)}</td>
                <td style="color:red; font-weight:bold;">{format_indian_number(dd['cgst'], prefix_rs=False)}</td>
                <td style="color:red; font-weight:bold;">{format_indian_number(dd['sgst'], prefix_rs=False)}</td>
                <td style="color:red; font-weight:bold;">{format_indian_number(dd['cess'], prefix_rs=False)}</td>
            </tr>"""
        
        # Add summary row
        html += f"""
            </tbody>
            <tfoot>
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td colspan="9" style="text-align: right;">Liability Detected</td>
                    <td style="color:red;">{format_indian_number(totals['igst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['cgst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['sgst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['cess'], prefix_rs=False)}</td>
                </tr>
            </tfoot>
        </table>"""
        return html

    @staticmethod
    def _generate_itc_yearly_table(rows):
        """Generates the yearly ITC summary table (Group B)."""
        if not rows: return ""
        
        html = """
        <table class="data-table">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>IGST</th><th>CGST</th><th>SGST</th><th>Cess</th>
                </tr>
            </thead>
            <tbody>
        """
        
        totals = {"igst": 0, "cgst": 0, "sgst": 0, "cess": 0}
        for row in rows:
            desc = row.get('description', '')
            vals = row.get('vals', {})
            style = "background-color: #ffebee;" if row.get('highlight') else ""
            desc_style = "text-align:left; font-weight:bold;" if row.get('highlight') else "text-align:left;"
            val_style = "color:red; font-weight:bold;" if row.get('highlight') else ""
            
            # Use the highlighted row (Difference) for totals (Only positive demand)
            if row.get('highlight'):
                for head in totals:
                    val = vals.get(head, 0)
                    totals[head] = max(0, val)

            html += f"""
                <tr style="{style}">
                    <td style="{desc_style}">{desc}</td>
                    <td style="{val_style}">{format_indian_number(vals.get('igst', 0), prefix_rs=False)}</td>
                    <td style="{val_style}">{format_indian_number(vals.get('cgst', 0), prefix_rs=False)}</td>
                    <td style="{val_style}">{format_indian_number(vals.get('sgst', 0), prefix_rs=False)}</td>
                    <td style="{val_style}">{format_indian_number(vals.get('cess', 0), prefix_rs=False)}</td>
                </tr>
            """
            
        # Add summary row
        html += f"""
            </tbody>
            <tfoot>
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td style="text-align: right;">Liability Detected</td>
                    <td style="color:red;">{format_indian_number(totals['igst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['cgst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['sgst'], prefix_rs=False)}</td>
                    <td style="color:red;">{format_indian_number(totals['cess'], prefix_rs=False)}</td>
                </tr>
            </tfoot>
        </table>"""
        return html

    @staticmethod
    def generate_html(data, issues, for_preview=True, show_letterhead=True, style_mode="legacy"):
        """
        Generates the HTML content for ASMT-10 with specific layout and formatting.
        
        Args:
            data (dict): Case data
            issues (list): List of selected issues
            for_preview (bool): Optimized for screen preview if True
            show_letterhead (bool): Whether to include letterhead image
            style_mode (str): "legacy" (Scrutiny Tab default) or "professional" (Adjudication Tab)
        """
        from src.utils.config_manager import ConfigManager
        import re
        import os
        import base64
        from datetime import datetime
        
        config = ConfigManager()
        
        def robust_float(val):
            if val is None: return 0.0
            if isinstance(val, (int, float)): return float(val)
            try:
                clean_val = str(val).replace(',', '').strip()
                return float(clean_val)
            except (ValueError, TypeError):
                return 0.0

        # 1. Filter active issues
        active_issues = [i for i in issues if robust_float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)]
        total_tax = sum(robust_float(i.get('total_shortfall', 0)) for i in active_issues)
        issues_count = len(active_issues)

        # [STABILIZATION] Zero-Demand Feedback
        if for_preview and issues_count == 0:
            return """
            <div style="font-family: 'Segoe UI', sans-serif; color: #64748b; background: #f8fafc; padding: 40px; text-align: center;">
                <div style="font-size: 48px; margin-bottom: 20px;">✅</div>
                <h2 style="color: #1e293b; margin-bottom: 10px;">No Discrepancies with Tax Shortfall</h2>
                <p style="line-height: 1.6;">Based on the analysis of provided files, no SOP compliance issues with a quantifiable tax shortfall have been identified for this tax period.</p>
                <div style="margin-top: 20px; font-size: 13px; color: #94a3b8; font-style: italic;">ASMT-10 drafting is only required for cases with detected liabilities.</div>
            </div>
            """
        
        # 2. Fetch Letterhead
        lh_content = ""
        try:
            if show_letterhead:
                lh_filename = config.get_pdf_letterhead()
                lh_path = os.path.join(config.letterheads_dir, lh_filename)
                
                if lh_path and os.path.exists(lh_path):
                    ext = os.path.splitext(lh_path)[1][1:].lower()
                    
                    # Fetch visual adjustments for this specific letterhead
                    adj = config.get_letterhead_adjustments(lh_filename)
                    # [RENDER-TIME CAP] Prevent extreme width adjustments (e.g. 623%) from breaking layout
                    width_val = adj.get('width', 100)
                    if width_val > 100: width_val = 100
                    
                    lh_style = f"width: {width_val}%; padding-top: {adj.get('padding_top', 0)}px; margin-bottom: {adj.get('margin_bottom', 20)}px;"
                    
                    if ext == "html":
                        # Case 1: HTML letterhead - read as text
                        with open(lh_path, 'r', encoding='utf-8') as f:
                            lh_full = f.read()
                            # Extract body content if present, otherwise use full content
                            import re
                            match = re.search(r"<body[^>]*>(.*?)</body>", lh_full, re.DOTALL | re.IGNORECASE)
                            inner_html = match.group(1) if match else lh_full
                            lh_content = f'<div style="{lh_style} text-align: center;">{inner_html}</div>'
                    else:
                        # Case 2: Image letterhead - read as binary and base64 encode
                        with open(lh_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        if ext == "jpg": ext = "jpeg"
                        lh_content = f'<div style="{lh_style} text-align: center;"><img src="data:image/{ext};base64,{encoded_string}" alt="Letterhead" style="max-width: 100%; height: auto;"></div>'
                else:
                    print(f"Letterhead file not found: {lh_path}")
        except Exception as e:
            print(f"Letterhead Error: {e}")
            
        # Fallback if image load failed but letterhead matching requested
        if show_letterhead and not lh_content:
             lh_content = """
             <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="margin:0; padding:0;">GOVERNMENT OF INDIA</h3>
                <h4 style="margin:5px 0 0 0; padding:0;">GOODS AND SERVICES TAX DEPARTMENT</h4>
             </div>
             """

        display_lh = lh_content if show_letterhead else '<div style="height: 100px;"></div>'

        # 3. Helpers
        def format_date(dt_str):
            if not dt_str: return "-"
            try:
                # Handle YYYY-MM-DD
                d = datetime.strptime(str(dt_str)[:10], "%Y-%m-%d")
                return d.strftime("%d/%m/%Y")
            except:
                return str(dt_str)

        oc_number = data.get('oc_number', 'DRAFT')
        notice_date = format_date(data.get('notice_date') or datetime.now().date())
        reply_date = data.get('last_date_to_reply', 'Within 30 Days')
        
        legal_name = data.get('taxpayer_details', {}).get('legal_name', data.get('legal_name', 'N/A'))
        gstin = data.get('taxpayer_details', {}).get('gstin', data.get('gstin', 'N/A'))
        addr = data.get('taxpayer_details', {}).get('address', 'Address not available')
        addr_clean = addr.replace('\n', '<br>')
        
        # 4. Generate Body
        issue_sections = ""
        issue_intro_parts = []
        
        for idx, issue in enumerate(active_issues, 1):
            shortfall = robust_float(issue.get('total_shortfall', 0))
            name = issue.get('category') or issue.get('issue_name') or "Unknown Discrepancy"
            desc = issue.get('brief_facts') or issue.get('description') or "Details as per attached calculation sheet."
            
            # Intro text builder
            issue_intro_parts.append(f"{idx} discrepancies") # Just a placeholder count really
            
            # Issue Table
            table_html = ASMT10Generator.generate_issue_table_html(issue)
            
            issue_sections += f"""
            <div class="issue-block">
                <div style="font-weight: bold; margin-bottom: 5px; font-size: 11pt;">Issue {idx} – {name}</div>
                <div style="font-weight: bold; color: #b91c1c; margin-bottom: 10px;">Estimated Tax: ₹ {format_indian_number(shortfall, prefix_rs=False)}</div>
                
                <div style="margin-bottom: 10px; text-align: justify;">{desc}</div>
                
                {table_html}
            </div>
            """
            
        intro_text = f"the following {len(active_issues)} discrepancies"

        # 5. CSS Styling Selection
        padding = "40px" if for_preview else "25mm 15mm"
        
        if style_mode == "professional":
            # --- PROFESSIONAL STYLE (Adjudication Tab) ---
            # Used for the read-only view in Proceedings Workspace
            page_width = "794px" # A4 width approx at 96dpi
            
            css = f"""
                body {{ 
                    font-family: 'Times New Roman', serif; 
                    background-color: #525659; 
                    color: black;
                    margin: 0;
                    padding: 20px;
                }}
                .page-wrapper {{
                    width: 100%;
                    text-align: center;
                }}
                .page-container {{
                    display: inline-block;
                    text-align: left;
                    width: {page_width}; 
                    min-height: {"1000px" if for_preview else "297mm"}; 
                    padding: {padding}; 
                    background-color: white; 
                    border: 1px solid #ccc;
                    box-shadow: 0 0 10px rgba(0,0,0,0.5);
                }}
                .letterhead-area {{ margin-bottom: 20px; width: 100%; text-align: center; }}
                .letterhead-area img {{ width: 100%; max-height: 120px; object-fit: contain; }}
                .oc-header {{ width: 100%; margin-bottom: 15px; font-weight: bold; font-size: 11pt; }}
                .form-title-area {{ text-align: center; margin-bottom: 25px; }}
                .form-title {{ font-size: 14pt; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }}
                .form-rule {{ font-size: 10pt; font-style: italic; }}
                .recipient {{ margin-bottom: 25px; font-size: 12pt; text-align: left; line-height: 1.4; }}
                .tax-period {{ margin-bottom: 15px; font-size: 12pt; font-weight: bold; }}
                .subject {{ text-align: center; font-weight: bold; margin-bottom: 20px; font-size: 12pt; text-decoration: underline; }}
                .content-main {{ font-size: 12pt; line-height: 1.5; }}
                .justify-text {{ text-align: justify; }}
                .issue-block {{ margin-bottom: 30px; border-bottom: 1px dashed #ccc; padding-bottom: 20px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 15px; border: 1px solid black; }}
                .data-table th, .data-table td {{ border: 1px solid black; padding: 5px; font-size: 10pt; text-align: center; }}
                .data-table th {{ background-color: #f2f2f2; font-weight: bold; }}
                .footer-sign {{ margin-top: 60px; text-align: right; font-size: 12pt; font-weight: bold; }}
            """
            
            body_content = f"""
            <div class="page-wrapper">
                <div class="page-container">
                    <div class="letterhead-area">{display_lh}</div>
                    <table class="oc-header" width="100%">
                        <tr><td align="left">O.C. No.: {oc_number}</td><td align="right">Date: {notice_date}</td></tr>
                    </table>
                    <div class="form-title-area">
                        <div class="form-title">FORM GST ASMT-10</div>
                        <div class="form-rule">[See rule 99(1)]</div>
                    </div>
                    <div class="recipient">To,<br><strong>{legal_name}</strong><br>GSTIN: {gstin}<br>{addr_clean}</div>
                    <div class="tax-period">Tax period: {data.get('financial_year', 'N/A')}</div>
                    <div class="subject">Sub: Notice for intimating discrepancies in the return after scrutiny</div>
                    <div class="content-main">
                        <p class="justify-text">This is to inform that during the scrutiny of the returns for the financial year {data.get('financial_year')}, {intro_text} have been noticed:</p>
                        {issue_sections}
                        <p style="margin-top: 20px; font-size: 13pt;"><strong>Total Tax Liability Identified: ₹ {format_indian_number(total_tax, prefix_rs=False)}</strong></p>
                        <p class="justify-text">You are hereby directed to explain the reasons for the aforesaid discrepancies by <strong>{reply_date}</strong>.</p>
                        <p class="justify-text">Failing which, proceedings in accordance with law may be initiated against you without further reference.</p>
                        <div class="footer-sign"><br><br>Signature of Proper Officer<br>(Name)<br>Designation</div>
                </div>
            </div>
            """

        else:
            # --- LEGACY STYLE (Original Scrutiny Tab) ---
            # Restored to exact previous configuration
            bg_color = "#f1f5f9" if for_preview else "#525659"
            page_width = "820px" if for_preview else "210mm" 
            page_margin = "30px auto"
            page_border = "1px solid #e2e8f0" if for_preview else "none"
            page_shadow = "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)" if for_preview else "0 0 10px rgba(0,0,0,0.5)"
            old_padding = "60px" if for_preview else "25mm 15mm"

            css = f"""
                body {{ 
                    font-family: 'Bookman Old Style', 'Times New Roman', serif; 
                    margin: 0; 
                    padding: 0;
                    color: black; 
                    font-size: 11pt; 
                    background-color: {bg_color}; 
                    -webkit-font-smoothing: antialiased;
                }}
                .page-wrapper {{
                    width: 100%;
                    text-align: center;
                }}
                .page-container {{
                    width: {page_width}; 
                    min-height: {"1000px" if for_preview else "297mm"}; 
                    padding: {old_padding}; 
                    margin: 30px auto !important; 
                    background: white; 
                    border: {page_border};
                    box-shadow: {page_shadow}; 
                    box-sizing: border-box;
                    display: inline-block; /* Support margin:auto and text-align:center fallback */
                    text-align: left;
                }}
                .letterhead-area {{ margin-bottom: 20px; width: 100%; text-align: center; }}
                .letterhead-area img {{ max-width: 100%; height: auto; object-fit: contain; }}
                .oc-header {{ width: 100% !important; margin-bottom: 15px; font-weight: bold; font-size: 11pt; border-collapse: collapse; }}
                .oc-header td {{ border: none !important; padding: 0 !important; }}
                .form-title-area {{ text-align: center; margin-bottom: 25px; }}
                .form-title {{ font-size: 12pt; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }}
                .form-rule {{ font-size: 10pt; font-style: italic; }}
                .recipient {{ margin-bottom: 25px; font-size: 11pt; text-align: left; line-height: 1.3; max-width: 100%; }}
                .recipient p {{ margin: 0; padding: 0; }}
                .recipient td {{ border: none !important; padding: 0 !important; }}
                .tax-period {{ margin-bottom: 15px; font-size: 11pt; font-weight: bold; }}
                .subject {{ text-align: center; font-weight: bold; margin-bottom: 30px; font-size: 11pt; margin-top: 20px; text-decoration: underline; width: 100%; }}
                .content-main {{ font-size: 11pt; line-height: 1.5; width: 100%; }}
                .justify-text {{ text-align: justify; }}
                .issue-block {{ margin-bottom: 30px; width: 100%; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 15px; margin-left: 0; margin-right: 0; table-layout: fixed; border: 1px solid black; }}
                /* Reduced font and padding to fit 9 columns */
                .data-table th, .data-table td {{ border: 1px solid black !important; padding: 3px 2px !important; font-size: 8pt; text-align: center; word-wrap: break-word; overflow-wrap: break-word; }}
                .data-table th {{ background-color: #f2f2f2 !important; font-weight: bold; font-size: 8pt; vertical-align: middle; }}
                .footer-sign {{ margin-top: 50px; text-align: right; font-size: 11pt; }}
            """
            
            body_content = f"""
            <div class="page-wrapper">
                <div class="page-container">
                    <div class="letterhead-area">
                        {display_lh}
                    </div>

                    <table class="oc-header" style="border: none;">
                        <tr style="border: none;">
                            <td align="left" style="border: none; width: 50%;">O.C. No.: {oc_number}</td>
                            <td align="right" style="border: none; width: 50%;">Date: {notice_date}</td>
                        </tr>
                    </table>

                    <div class="form-title-area">
                        <div class="form-title">FORM GST ASMT-10</div>
                        <div class="form-rule">[See rule 99(1)]</div>
                    </div>
                    
                    <table class="recipient" style="width: 65%; border: none;">
                        <tr style="border: none;">
                            <td style="border: none; text-align: left; padding: 0;">
                                To,<br>
                                <strong>{legal_name}</strong><br>
                                GSTIN: {gstin}<br>
                                {addr_clean}
                            </td>
                        </tr>
                    </table>

                    <div class="tax-period">
                        Tax period: {data.get('financial_year', 'N/A')}
                    </div>
                    
                    <div class="subject">
                        Sub: Notice for intimating discrepancies in the return after scrutiny
                    </div>

                    <div class="content-main">
                        <p class="justify-text">This is to inform that during the scrutiny of the returns for the financial year {data.get('financial_year')}, {intro_text} have been noticed:</p>
                        
                        {issue_sections}
                        
                        <p style="margin-top: 20px;"><strong>Total Tax Liability Identified: ₹ {format_indian_number(total_tax, prefix_rs=False)}</strong></p>
                        
                        <p class="justify-text">You are hereby directed to explain the reasons for the aforesaid discrepancies by <strong>{reply_date}</strong>.</p>
                        <p class="justify-text">Failing which, proceedings in accordance with law may be initiated against you without further reference.</p>
                        
                        <div class="footer-sign">
                            Signature of Proper Officer<br>
                            (Name)<br>
                            Designation
                        </div>
                    </div>
                </div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{css}</style>
        </head>
        <body>
            {body_content}
        </body>
        </html>
        """
        return html

    @staticmethod
    def save_pdf(html_content, output_path):
        """Generates PDF using Qt's internal printer"""
        try:
            doc = QTextDocument()
            doc.setHtml(html_content)
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_path)
            
            # PyQt6 way to set page size and margins
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0)
            )
            printer.setPageLayout(layout)
            
            doc.print(printer)
            return True, "PDF generated successfully."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def save_docx(html_content, output_path):
        """Generates 'Docx' (Word-Ready HTML)"""
        try:
            word_html = f"""
            <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word'>
            <head>
                <meta charset="utf-8">
                <style>
                    @page Section1 {{ size:595.45pt 841.9pt; margin:1.0in 1.0in 1.0in 1.0in; mso-header-margin:0.5in; mso-footer-margin:0.5in; mso-paper-source:0; }}
                    div.Section1 {{ page:Section1; }}
                    body {{ font-family: 'Times New Roman', serif; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    td, th {{ border: 1px solid black; padding: 5px; }}
                </style>
            </head>
            <body>
            <div class="Section1">
                {html_content}
            </div>
            </body>
            </html>
            """
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(word_html)
            return True, "Docx (Word-Ready HTML) generated successfully."
        except Exception as e:
            return False, str(e)
