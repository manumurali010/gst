from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import QSizeF, QMarginsF
import os

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
        template_type = issue.get('template_type')
        rows = issue.get('rows', [])
        
        if (template_type == 'liability_monthly' or template_type == 'liability_monthwise' or template_type == 'liability_mismatch') and rows:
            return ASMT10Generator._generate_liability_table(rows, issue.get('labels'))
        elif template_type == 'itc_yearly_summary' and rows:
            return ASMT10Generator._generate_itc_yearly_table(rows)
            
        return "<p><em>No detailed table available for this issue type.</em></p>"

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
    def generate_html(data, issues, for_preview=False):
        """Generates the HTML content for ASMT-10 with specific layout and formatting."""
        from src.utils.config_manager import ConfigManager
        import re
        
        config = ConfigManager()
        total_tax = sum(float(i.get('total_shortfall', 0)) for i in issues)
        
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
                        # Remove placeholders if they exist in the letterhead template
                        lh_content = lh_content.replace('<div id="form-header-placeholder"></div>', '')
                        lh_content = lh_content.replace('<div id="content-placeholder"></div>', '')
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
        for idx, issue in enumerate(issues, 1):
            section_html = f"""
            <div class="issue-block">
                <p><strong>{idx}. {issue.get('category')}</strong></p>
                <p class="justify-text">{issue.get('description')}</p>
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

        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 15mm; }}
                body {{ 
                    font-family: 'Bookman Old Style', serif; 
                    margin: 0; 
                    padding: 0;
                    color: black; 
                    font-size: 11pt; 
                    background-color: {"#f4f7f9" if for_preview else "white"};
                }}
                .page-container {{
                    {"width: 210mm; min-height: 297mm; padding: 15mm 20mm; margin: 20px auto; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); border-radius: 2px;" if for_preview else "padding: 0mm;"}
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                }}
                .letterhead-area {{ {"margin-top: -15mm;" if not for_preview else ""} margin-bottom: 5px; }}
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
                {lh_content}
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
            
            <div class="recipient">
                To,<br>
                <p><strong>{legal_name}</strong></p>
                <p>GSTIN: {gstin}</p>
                <p>{addr_clean}</p>
            </div>

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
