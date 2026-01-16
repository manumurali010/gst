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
        has_tbl = "YES" if "tables" in issue and issue["tables"] else "NO"
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
                    if key in row: html += f"<td>{row[key]}</td>"
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
                <td>{d3['igst']:,.0f}</td><td>{d3['cgst']:,.0f}</td><td>{d3['sgst']:,.0f}</td><td>{d3['cess']:,.0f}</td>
                <td>{d1['igst']:,.0f}</td><td>{d1['cgst']:,.0f}</td><td>{d1['sgst']:,.0f}</td><td>{d1['cess']:,.0f}</td>
                <td style="color:red; font-weight:bold;">{dd['igst']:,.0f}</td>
                <td style="color:red; font-weight:bold;">{dd['cgst']:,.0f}</td>
                <td style="color:red; font-weight:bold;">{dd['sgst']:,.0f}</td>
                <td style="color:red; font-weight:bold;">{dd['cess']:,.0f}</td>
            </tr>"""
        
        # Add summary row
        html += f"""
            </tbody>
            <tfoot>
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td colspan="9" style="text-align: right;">Liability Detected</td>
                    <td style="color:red;">{totals['igst']:,.0f}</td>
                    <td style="color:red;">{totals['cgst']:,.0f}</td>
                    <td style="color:red;">{totals['sgst']:,.0f}</td>
                    <td style="color:red;">{totals['cess']:,.0f}</td>
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
                    <td style="{val_style}">{vals.get('igst', 0):,.0f}</td>
                    <td style="{val_style}">{vals.get('cgst', 0):,.0f}</td>
                    <td style="{val_style}">{vals.get('sgst', 0):,.0f}</td>
                    <td style="{val_style}">{vals.get('cess', 0):,.0f}</td>
                </tr>
            """
            
        # Add summary row
        html += f"""
            </tbody>
            <tfoot>
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td style="text-align: right;">Liability Detected</td>
                    <td style="color:red;">{totals['igst']:,.0f}</td>
                    <td style="color:red;">{totals['cgst']:,.0f}</td>
                    <td style="color:red;">{totals['sgst']:,.0f}</td>
                    <td style="color:red;">{totals['cess']:,.0f}</td>
                </tr>
            </tfoot>
        </table>"""
        return html

    @staticmethod
    def generate_html(data, issues, for_preview=True, show_letterhead=True):
        """Generates the HTML content for ASMT-10 with specific layout and formatting."""
        # Note: for_preview arg is kept for compatibility but logic is unified for WYSIWYG
        from src.utils.config_manager import ConfigManager
        """Generates the HTML content for ASMT-10 with specific layout and formatting."""
        from src.utils.config_manager import ConfigManager
        import re
        
        config = ConfigManager()
        # Filter issues to only show those with detected discrepancies in the draft AND included by user
        active_issues = [i for i in issues if float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)]
        total_tax = sum(float(i.get('total_shortfall', 0)) for i in active_issues)
        
        # 1. Fetch Letterhead
        lh_content = ""
        try:
            lh_path = config.get_letterhead_path('pdf')
            if os.path.exists(lh_path):
                with open(lh_path, 'r', encoding='utf-8') as f:
                    lh_full = f.read()
                    # Extract content inside body if present
                    match = re.search(r"<body[^>]*>(.*?)</body>", lh_full, re.DOTALL | re.IGNORECASE)
                    if match:
                        lh_content = match.group(1)
                        # Remove placeholders and strip problematic internal margins
                        lh_content = lh_content.replace('<div id="form-header-placeholder"></div>', '')
                        lh_content = lh_content.replace('<div id="content-placeholder"></div>', '')
                        # Strip hardcoded margins and paddings that interfere with global layout
                        lh_content = lh_content.replace('margin: 10px auto;', 'margin: 0 auto;')
                        lh_content = lh_content.replace('margin-bottom: 20px;', 'margin-bottom: 5px;')
                        lh_content = lh_content.replace('padding-top: 0px;', 'padding-top: 0;')
                    else:
                        lh_content = lh_full
        except Exception as e:
            print(f"Error loading letterhead: {e}")
            lh_content = "<div style='text-align:center;'><h3>GST DEPARTMENT</h3></div>"

        # 2. Preparation of Metadata & Formatting
        def fmt_date(d_str):
            if not d_str or str(d_str).upper() == "N/A": return "N/A"
            try:
                from datetime import datetime
                d_str = str(d_str).split()[0] if ' ' in str(d_str) else str(d_str)
                dt = datetime.strptime(d_str, '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except:
                return str(d_str)

        notice_date = fmt_date(data.get('notice_date') or data.get('created_at', ''))
        reply_date = fmt_date(data.get('last_date_to_reply', ''))
        oc_number = data.get('oc_number', 'N/A')

        issue_sections = ""
        for idx, issue in enumerate(active_issues, 1):
            # Semantic Correction: Issue <n> – <Issue Name>
            import re
            raw_name = issue.get('category') or issue.get('issue_name') or "Unknown Issue"
            # Strip "Point X- " prefix if present
            issue_name = re.sub(r'^Point \d+- ?', '', raw_name, flags=re.IGNORECASE)
            
            section_html = f"""

            <div class="issue-block">
                <p><strong>Issue {idx} – {issue_name}</strong></p>
                <p class="justify-text">{issue.get('brief_facts') or issue.get('description')}</p>
            """
            section_html += ASMT10Generator.generate_issue_table_html(issue)
            section_html += "</div>"
            issue_sections += section_html


        # 3. Recipient Details & Address Wrapping
        raw_address = (data.get('address') or data.get('Address of Principal Place of Business') or 
                       data.get('taxpayer_details', {}).get('Address') or 
                       data.get('taxpayer_details', {}).get('Address of Principal Place of Business') or '')
        
        # Clean address for professional wrapping: ensure one space after commas and no double spaces
        if raw_address:
            addr_clean = ' '.join(str(raw_address).replace(',', ', ').split()).replace('  ', ' ').strip()
        else:
            addr_clean = "Address not found"
        
        gstin = data.get('gstin') or data.get('taxpayer_details', {}).get('GSTIN') or 'N/A'
        legal_name = data.get('legal_name') or data.get('taxpayer_details', {}).get('Legal Name') or 'Unknown'

        # Apply Letterhead suppression
        display_lh = lh_content if show_letterhead else ""

        html = f"""
        <html>
        <head>
            <style>
                /* Print-Ready CSS */
                @media print {{
                    @page {{ size: A4 portrait; margin: 15mm; }}
                    body {{ 
                        background-color: white !important; 
                        -webkit-print-color-adjust: exact; 
                        width: 100%;
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                    .page-container {{
                        width: 100%;
                        margin: 0 !important;
                        padding: 0 !important;
                        border: none !important;
                        box-shadow: none !important;
                        min-height: auto !important;
                        background-color: white !important;
                    }}
                    .footer-sign {{ page-break-inside: avoid; }}
                    .issue-block {{ page-break-inside: avoid; }}
                    tr {{ page-break-inside: avoid; }}
                    thead {{ display: table-header-group; }}
                    tfoot {{ display: table-footer-group; }}
                    .letterhead-area {{ margin-top: 0 !important; }} 
                }}

                @page {{ size: A4; margin: 15mm; }}
                body {{ 
                    font-family: 'Bookman Old Style', serif; 
                    margin: 0; 
                    padding: 0;
                    color: black; 
                    font-size: 11pt; 
                    background-color: #525659; /* Acrobat gray background for preview */
                }}
                .page-container {{
                    width: 210mm; 
                    min-height: 297mm; 
                    padding: 15mm 20mm; 
                    margin: 20px auto; 
                    background: white; 
                    box-shadow: 0 0 10px rgba(0,0,0,0.5); 
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                }}
                .letterhead-area {{ margin-bottom: 5px; }}
                .oc-header {{ width: 100%; margin-bottom: 15px; font-weight: bold; font-size: 11pt; border-collapse: collapse; }}
                .oc-header td {{ border: none; padding: 0; }}
                .form-title-area {{ text-align: center; margin-bottom: 20px; }}
                .form-title {{ font-size: 11pt; font-weight: bold; margin-bottom: 2px; }}
                .form-rule {{ font-size: 10pt; font-style: italic; }}
                .recipient {{ margin-bottom: 20px; font-size: 11pt; text-align: left; line-height: 1.2; max-width: 380px; }}
                .recipient p {{ margin: 0; padding: 0; }}
                .tax-period {{ margin-bottom: 15px; font-size: 11pt; font-weight: bold; }}
                .subject {{ text-align: center; font-weight: bold; margin-bottom: 25px; font-size: 11pt; margin-top: 20px; text-decoration: underline; }}
                .content-main {{ font-size: 11pt; line-height: 1.4; }}
                .justify-text {{ text-align: justify; }}
                .issue-block {{ margin-bottom: 25px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; margin-left: auto; margin-right: auto; table-layout: fixed; border: 1px solid black; }}
                .data-table th, .data-table td {{ border: 1px solid black; padding: 5px; font-size: 9pt; text-align: center; word-wrap: break-word; }}
                .data-table th {{ background-color: #f2f2f2; font-weight: bold; }}
                .footer-sign {{ margin-top: 50px; text-align: right; font-size: 11pt; }}
            </style>
        </head>
        <body>
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
                <p class="justify-text">This is to inform that during the scrutiny of the returns for the financial year {data.get('financial_year')}, the following discrepancies have been noticed:</p>
                
                {issue_sections}
                
                <p style="margin-top: 20px;"><strong>Total Tax Liability Identified: ₹ {total_tax:,.0f}</strong></p>
                
                <p class="justify-text">You are hereby directed to explain the reasons for the aforesaid discrepancies by <strong>{reply_date}</strong>.</p>
                <p class="justify-text">If no explanation is received by the said date, it will be presumed that you have nothing to say in the matter and proceedings in accordance with law may be initiated against you without making any further reference to you.</p>
                
                <div class="footer-sign">
                    Signature of Proper Officer<br>
                    (Name)<br>
                    Designation
                </div>
            </div>
            </div>
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
