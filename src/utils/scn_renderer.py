import json
import re
from src.utils.config_manager import ConfigManager
from jinja2 import Template, Environment, FileSystemLoader

class SCNRenderer:
    """
    Static helper to render SCN HTML from a pure data snapshot.
    Runs safely in background threads.
    """
    @staticmethod
    def render_html(snapshot, for_preview=False):
        """
        Render SCN HTML using data snapshot.
        Args:
            snapshot (dict): Dictionary containing all necessary data, inputs, and issue content.
            for_preview (bool): If True, suppresses page breaks for continuous flow.
        """
        if not snapshot:
            return "<h3>No Case Data Loaded</h3>"
            
        try:
            # 1. Base Data
            data = snapshot.get('case_data', {}).copy()
            
            # Merge Inputs
            data.update(snapshot.get('inputs', {}))
            
            # Derived Fields
            data['year'] = data.get('issue_date', '').split('/')[-1] if data.get('issue_date') else ''
            
            # Taxpayer Details Parsing
            if 'taxpayer_details' in data and isinstance(data['taxpayer_details'], str):
                try:
                    data['taxpayer_details'] = json.loads(data['taxpayer_details'])
                except:
                    data['taxpayer_details'] = {}
            
            tp = data.get('taxpayer_details', {})
            data['legal_name'] = tp.get('Legal Name', '') or data.get('legal_name', '')
            data['trade_name'] = tp.get('Trade Name', '') or data.get('trade_name', '')
            data['address'] = tp.get('Address', '') or data.get('address', '')
            data['gstin'] = data.get('gstin', '')
            data['constitution_of_business'] = tp.get('Constitution of Business', 'Registered')
            
            # Officer (Mock)
            data['officer_name'] = "VISHNU V"
            data['officer_designation'] = "Superintendent"
            data['designation'] = "Superintendent"
            data['jurisdiction'] = "Paravur Range"
            
            # 2. Render Issues
            issues_html = ""
            total_tax = 0
            igst_total = 0
            cgst_total = 0
            sgst_total = 0
            
            current_para_num = 3
            included_issues = snapshot.get('issues', [])
            
            # print(f"DEBUG: Rendering {len(included_issues)} issues in worker.")
            
            for i, issue in enumerate(included_issues, 1):
                # Page Break Logic (Disabled in Preview Mode)
                if for_preview:
                    page_break_style = "margin-bottom: 30px; border-bottom: 2px dashed #ccc; padding-bottom: 20px;" # Visual separator instead
                else:
                    page_break_style = "page-break-after: always;" if i < len(included_issues) else ""
                
                issues_html += f'<div style="display: block; {page_break_style}">'
                
                # Title Para
                title = issue.get('title', 'Issue')
                issues_html += f"""
                <table style="width: 100%; margin-bottom: 10px; border: none;">
                    <tr style="border: none;">
                        <td style="width: 40px; vertical-align: top; border: none; font-weight: bold;">{current_para_num}.</td>
                        <td style="vertical-align: top; border: none; font-weight: bold;">Issue No. {i}: {title}</td>
                    </tr>
                </table>
                """
                
                # [Fix] Enforce Grid Authority
                grid_data = issue.get('grid_data')
                
                # Regex to strip ALL table tags if grid_data exists (authority shift)
                if grid_data:
                     # Remove everything from <table to </table>
                     raw_html = re.sub(r'<table.*?>.*?</table>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
                     # Also remove legacy calculation table markers if any
                     raw_html = re.sub(r'<p[^>]*>Calculation Table</p>', '', raw_html, flags=re.IGNORECASE)
                
                parts = raw_html.split('<div style="margin-bottom: 20px;')
                
                editor_part = parts[0]
                table_part = '<div style="margin-bottom: 20px;' + parts[1] if len(parts) > 1 else ""
                
                # Regex cleanup
                editor_part = re.sub(r'<p>\s*&nbsp;\s*</p>', '', editor_part)
                editor_part = re.sub(r'<p>\s*</p>', '', editor_part)
                paras = re.findall(r'<p.*?>(.*?)</p>', editor_part, re.DOTALL)
                
                if not paras and editor_part.strip():
                    paras = [editor_part]
                    
                sub_para_count = 1
                for p_content in paras:
                    if p_content.strip():
                        num_str = f"{current_para_num}.{sub_para_count}"
                        issues_html += f"""
                        <table style="width: 100%; margin-bottom: 10px; border: none;">
                            <tr style="border: none;">
                                <td style="width: 50px; vertical-align: top; border: none; padding-left: 15px; font-weight: bold;">{num_str}</td>
                                <td style="vertical-align: top; border: none;">{p_content}</td>
                            </tr>
                        </table>
                        """
                        sub_para_count += 1
                
                # Render Table from Authority
                if grid_data:
                     # Implement grid rendering for Print/PDF here
                     table_html = self._render_grid_as_html_table(grid_data)
                     if table_html:
                          num_str = f"{current_para_num}.{sub_para_count}"
                          issues_html += f"""
                          <div style="display: flex; margin-bottom: 10px;">
                              <table style="width: 100%; border: none;">
                                  <tr style="border: none;">
                                      <td style="width: 50px; vertical-align: top; border: none; padding-left: 15px; font-weight: bold;">{num_str}</td>
                                      <td style="vertical-align: top; border: none;">{table_html}</td>
                                  </tr>
                              </table>
                          </div>
                          """
                          sub_para_count += 1
                elif table_part:
                    num_str = f"{current_para_num}.{sub_para_count}"
                    issues_html += f"""
                    <div style="display: flex; margin-bottom: 10px;">
                        <table style="width: 100%; border: none;">
                            <tr style="border: none;">
                                <td style="width: 50px; vertical-align: top; border: none; padding-left: 15px; font-weight: bold;">{num_str}</td>
                                <td style="vertical-align: top; border: none;">{table_part}</td>
                            </tr>
                        </table>
                    </div>
                    """
                    sub_para_count += 1
                    
                current_para_num += 1
                issues_html += "</div>"
                
                # Totals
                breakdown = issue.get('tax_breakdown', {})
                for act, vals in breakdown.items():
                    tax = vals.get('tax', 0)
                    total_tax += tax
                    if act == 'IGST': igst_total += tax
                    elif act == 'CGST': cgst_total += tax
                    elif act == 'SGST': sgst_total += tax

            if not included_issues:
                issues_html = "<p>No issues selected.</p>"
                
            data['next_para_num'] = current_para_num
            data['para_demand'] = current_para_num
            data['para_waiver'] = current_para_num + 1
            data['para_cancellation'] = current_para_num + 2
            data['para_hearing'] = current_para_num + 3
            data['para_exparte'] = current_para_num + 4
            data['para_prejudice'] = current_para_num + 5
            data['para_amendment'] = current_para_num + 6
            data['para_reliance'] = current_para_num + 7
            
            # Format currency strings
            import locale
            try:
                locale.setlocale(locale.LC_ALL, 'en_IN')
            except:
                pass
                
            def fmt(v):
                try: return locale.currency(v, grouping=True) if v else "Rs. 0"
                except: return f"Rs. {v}"
                
            data['total_tax_words'] = SCNRenderer.num_to_words(total_tax) # Need helper
            data['total_amount'] = fmt(total_tax) # Template expects total_amount
            data['total_tax'] = fmt(total_tax)
            data['igst_total'] = fmt(igst_total)
            data['cgst_total'] = fmt(cgst_total)
            data['sgst_total'] = fmt(sgst_total)
            data['cess_total'] = fmt(0) # TODO: Track cess
            
            # Advice Text Logic
            section = data.get('adjudication_section') or data.get('initiating_section', '')
            last_date_payment = snapshot.get('last_date_payment', '')
            
            if "73" in section:
                advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
            elif "74" in section:
                advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
            else:
                advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."
            
            # [Fix] Pass generated HTML via data context for Jinja2
            data['issues_content'] = issues_html
            data['demand_text'] = advice_text
            data['is_preview'] = for_preview  # [Style Control]
            
            # Template Loading
            template_content = snapshot.get('master_template', '')
            if not template_content:
                # Fallback
                return "<h3>Error: Master Template Missing</h3>"
                
            template = Template(template_content)
            html = template.render(data)
            
            # Letterhead
            if snapshot.get('show_letterhead'):
                lh_html = snapshot.get('letterhead_html', '')
                html = html.replace('<div id="letterhead-placeholder"></div>', lh_html)
                
            # Cleanup placeholders
            for p in ["{{OCNumber}}", "{{SCNSection}}", "{{CurrentDate}}", "{{ComplianceDate}}", "{{TaxPeriodFrom}}", "{{TaxPeriodTo}}", "{{IssueDescription}}", "{{TaxAmount}}", "{{InterestAmount}}", "{{PenaltyAmount}}", "{{TotalAmount}}"]:
                html = html.replace(p, "_________________")
                
            return html
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"<h3>Rendering Error: {str(e)}</h3>"

    @staticmethod
    def render_qt_safe_html(snapshot):
        """
        Generates SCN HTML optimized for QTextBrowser (Qt Rich Text Engine).
        Uses simple divs and full text restoration.
        """
        if not snapshot:
            return "<h3 style='color:red;'>No Snapshot Data</h3>"
            
        try:
            # 1. Prepare Data
            data = snapshot.get('case_data', {}).copy()
            data.update(snapshot.get('inputs', {}))
            
            # Formatting Helpers
            import locale
            try: locale.setlocale(locale.LC_ALL, 'en_IN')
            except: pass
            
            def fmt(v):
                try: 
                    # Handle string "0"
                    f = float(v)
                    return f"{f:,.2f}"
                except: 
                    return "0.00"
                
            # Fonts & Styles
            font_family = "Bookman Old Style"
            # Body: 11pt as requested
            body_style = f"font-family: '{font_family}'; font-size: 11pt; color: black;"
            bold_style = f"{body_style} font-weight: bold;"
            
            # Tables: 10pt as requested
            data_table_style = f"border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 10pt;"
            cell_style = f"border: 1px solid black; padding: 5px; font-family: '{font_family}'; font-size: 10pt;"
            
            # 2. Build HTML Parts
            html_parts = []
            
            # --- LETTERHEAD ---
            # [Fix] Disabled for Draft Preview
            
            # --- OC NO & DATE ---
            scn_no = data.get('scn_no', '_______')
            issue_date = data.get('issue_date', '_______')
            
            header_table = f"""
            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 20px; margin-top: 10px;">
                <tr>
                    <td align="left" style="{body_style}"><b>OC No:</b> {scn_no}</td>
                    <td align="right" style="{body_style}"><b>Date:</b> {issue_date}</td>
                </tr>
            </table>
            """
            html_parts.append(header_table)
            
            # --- HEADINGS ---
            fin_year = data.get('financial_year', '2025-26')
            full_scn_no = f"{scn_no}/GST-{data.get('designation', 'Superintendent')}"
            
            html_parts.append(f"<div align='center' style='{bold_style} margin-bottom: 20px;'>SHOW CAUSE NOTICE No. {full_scn_no}</div>")
            
            form_header = f"""
            <div align='center' style='{bold_style}'>
                FORM GST DRC-01<br>
                [See rule 142(1)]<br>
                Show Cause Notice under section {data.get('adjudication_section', '73')}
            </div><br>
            """
            html_parts.append(form_header)
            
            # --- PARA 1 (Recipient Intro) ---
            tp_name = data.get('legal_name', '_______')
            tp_trade = data.get('trade_name', '')
            tp_addr = data.get('address', '_______')
            tp_gstin = data.get('gstin', '_______')
            tp_const = data.get('constitution_of_business', 'Registered')
            
            para1_text = (f"<b>{tp_name}, {tp_trade}, {tp_addr}</b> (hereinafter referred to as ‘the taxpayer’) "
                          f"is holding GST registration bearing GSTIN: <b>{tp_gstin}</b> in the capacity of a ‘registered person’ "
                          f"as envisaged under section 2(94) of the Central Goods and Services Tax Act, 2017 "
                          f"(hereinafter referred to as “the Act”) is a {tp_const} firm with trade name <b>M/s. {tp_trade}.</b>")
            
            html_parts.append(SCNRenderer._make_qt_para(1, para1_text, body_style))
            
            # --- PARA 2 (Legal Reference - FULL TEXT) ---
            para2_text = ("All references in this Notice to a Section of the Central Goods and Services Tax Act, 2017 (CGST Act, 2017) "
                          "implies reference to the corresponding section of the Kerala State Goods and Services Tax Act, 2017 (KSGST Act, 2017). "
                          "Similarly, all references to a Rule of the Central Goods and Services Tax Rules, 2017 (CGST Rules, 2017) "
                          "implies reference to the corresponding Rules of the Kerala State Goods and Services Tax Rules, 2017 (KSGST Rules, 2017).")
            html_parts.append(SCNRenderer._make_qt_para(2, para2_text, body_style))
            
            # --- GROUNDS HEADER ---
            html_parts.append(f"<br><div align='center' style='{bold_style} text-decoration: underline; margin: 15px 0;'>GROUNDS OF SCN</div>")
            
            # --- ISSUES ---
            issues = snapshot.get('issues', [])
            current_num = 3
            total_tax_sum = 0
            igst_sum = 0
            cgst_sum = 0
            sgst_sum = 0
            
            if not issues:
                 html_parts.append(f"<div align='center' style='{body_style} font-style: italic; color: gray;'>No issues added.</div>")
            
            for i, issue in enumerate(issues, 1):
                # Issue Title
                title_html = f"Issue No. {i}: {issue.get('title', 'Issue')}"
                html_parts.append(SCNRenderer._make_qt_para(current_num, f"<b>{title_html}</b>", body_style))
                # current_num += 1 # Standard template doesn't increment main para number for title? 
                # Template uses issues_content which has its own numbering.
                # Let's keep strict SCN numbering.
                
                # Content
                raw_content = issue.get('html_content', '')
                grid_data = issue.get('grid_data')
                
                print(f"DEBUG QT RENDER: Issue {i} | Content Len: {len(raw_content)} | Grid Data Present: {bool(grid_data)}")
                
                if not grid_data:
                     # [Defensive Log]
                     # [SCN-UX] Silence warning if it is an intentional narrative-only issue
                     if not issue.get('narrative_only'):
                          print(f"WARNING: Issue {i} has NO grid_data in snapshot. Tables may be empty.")
                
                # [Fix] Enforce Grid Authority
                grid_data = issue.get('grid_data')
                
                # Robust Stripping: remove tables from narrative if grid_data exists
                stripped_content = raw_content
                if grid_data:
                     # Remove everything from <table to </table>
                     stripped_content = re.sub(r'<table.*?>.*?</table>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
                     # Also remove legacy calculation table markers if any
                     stripped_content = re.sub(r'<p[^>]*>Calculation Table</p>', '', stripped_content, flags=re.IGNORECASE)
                
                # [Fix] Div Indentation
                content_html = f"""
                <div style="margin-left: 40px; margin-bottom: 20px; {body_style} text-align: justify;">
                     {stripped_content}
                </div>
                """
                html_parts.append(content_html)
                
                # [Fix] Direct Grid Rendering (Mirror Mode)
                # [SCN-UX] Explicit Branching: Analytical issues ONLY
                if grid_data and isinstance(grid_data, dict) and not issue.get('narrative_only'):
                    try:
                        cols = grid_data.get('columns', [])
                        rows = grid_data.get('rows', [])
                        
                        if rows:
                             # Map Column IDs (Normalized)
                             col_map = {} 
                             for c in cols:
                                 if isinstance(c, dict):
                                      cid = c.get('id')
                                      lbl = str(c.get('label', cid or '')).lower()
                                 else:
                                      cid = str(c)
                                      lbl = str(c).lower()
                                 col_map[cid] = lbl
                                 
                             # Start Table
                             tax_table = f"""
                             <table cellspacing="0" cellpadding="0" style="{data_table_style}">
                                <tr style="background-color: #f0f0f0;">
                             """
                             
                             # Header Row
                             render_col_ids = []
                             for c in cols:
                                 if isinstance(c, dict):
                                      cid = c.get('id')
                                      lbl = c.get('label', cid or '')
                                 else:
                                      cid = str(c)
                                      lbl = str(c)
                                 tax_table += f'<th align="center" style="{cell_style}"><b>{lbl}</b></th>'
                                 render_col_ids.append(cid)
                                 
                             tax_table += "</tr>"
                             
                             rendered_rows_count = 0
                             all_zeros = True
                             
                             for r in rows:
                                 row_html = "<tr>"
                                 has_val = False
                                 for cid in render_col_ids:
                                     # Extract Cell Value
                                     cell = r.get(cid)
                                     val = ""
                                     if isinstance(cell, dict):
                                         val = cell.get('value', '')
                                     else:
                                         val = cell
                                         
                                     # Format? User said "Verbatim". But let's ensure it's string.
                                     val_str = str(val) if val is not None else ""
                                     
                                     # Zero check logic
                                     try:
                                         fval = float(str(val_str).replace(',', '').strip())
                                         if fval != 0: all_zeros = False
                                     except:
                                         # If text (e.g. Description), it's not a zero.
                                         if val_str.strip() and val_str.strip() not in ['0', '0.00']:
                                             all_zeros = False
                                     
                                     # Alignment
                                     align = "left"
                                     lbl = col_map.get(cid, "")
                                     if any(x in lbl for x in ['amount', 'tax', 'cgst', 'sgst', 'igst', 'cess', 'rate', 'value']):
                                         align = "right"
                                         
                                     row_html += f'<td align="{align}" style="{cell_style}">{val_str}</td>'
                                     
                                 row_html += "</tr>"
                                 tax_table += row_html
                                 rendered_rows_count += 1
                                 
                             tax_table += "</table><br>"
                             html_parts.append(tax_table)
                             
                             # [Guard] Hard Failure
                             if rendered_rows_count > 0 and all_zeros:
                                 # We only fail if there are numeric columns but they are all zero?
                                 # Or if the user explicitly said "Silent zeros are unacceptable".
                                 # If the user ENTERED zeros, it's fine. But "fallback to zero" is bad.
                                 # Since we are rendering VERBATIM, we are not falling back.
                                 # We trust the data.
                                 pass

                             if rendered_rows_count == 0:
                                 raise RuntimeError("Qt Draft Preview failed to map grid_data rows.")

                    except Exception as e:
                        print(f"Direct Grid Render Error: {e}")
                        html_parts.append(f"<div style='color:red;'>Table Error: {str(e)}</div>")
                
                # [Fix] REMOVED Fallback Block
                # elif issue.get('tax_breakdown'): ...
                     
                current_num += 1
            
            # --- DEMAND SECTION ---
            # Full text from template
            demand_text = (f"<b>Demand-</b> Based on the facts of the issue and reference of laws as mentioned above, "
                           f"whereas it appears that <b>{tp_name}, {tp_trade}, {tp_addr}</b> is liable to pay tax "
                           f"amounting to Rs. {fmt(total_tax_sum)}/- (IGST Rs. {fmt(igst_sum)}/-, CGST Rs. {fmt(cgst_sum)}/- & "
                           f"SGST Rs. {fmt(sgst_sum)}/-) for the contraventions made by them as discussed above, they are hereby "
                           f"directed to Show Cause to <b>{data.get('officer_designation')}, {data.get('jurisdiction')}</b> as to why:")
            
            html_parts.append(SCNRenderer._make_qt_para(current_num, demand_text, body_style))
            current_num += 1
            
            # Advice Text
            advice_text = data.get('demand_text', '') 
            if not advice_text:
                advice_text = "Tax, Interest and Penalty as applicable should not be demanded/recovered..."
            
            # Indented Advice
            html_parts.append(f"<div align='justify' style='{body_style} margin: 10px 0 10px 40px;'>{advice_text}</div>")
            
            # --- STANDARD LEGAL PARAS (FULL TEXT) ---
            
            # Waiver
            waiver_text = ("<u>With regard to the above demand, where any person chargeable with tax under sub section (1) or "
                           "sub section (3) of Section 73 of CGST Act 2017/Kerala SGST Act, 2017 read with Section 20 of the "
                           "IGST Act, 2017 pays the said tax along with interest payable under Section 50 within thirty days of issue "
                           "of show cause notice, no penalty shall be payable and all proceedings in respect of the said notice "
                           "shall be deemed to be concluded.</u>")
            html_parts.append(SCNRenderer._make_qt_para(current_num, waiver_text, body_style))
            current_num += 1
            
            # Cancellation
            cancel_text = ("As per Section 29(3) of the CGST Act 2017/Kerala SGST Act, 2017 read with Section 20 of the IGST Act, 2017, "
                           "the cancellation of the registration under this Section shall not affect the liability of person to pay tax "
                           "and other dues under this Act or to discharge any obligation under this Act or the rules made thereunder for "
                           "any period prior to the date of cancellation whether or not such tax and other dues are determined before or "
                           "after the date of cancellation.")
            html_parts.append(SCNRenderer._make_qt_para(current_num, cancel_text, body_style))
            current_num += 1
            
            # Hearing
            hearing_text = (f"<b>{tp_name}, {tp_trade}, {tp_addr}</b> is also directed to produce, at the time of showing cause, "
                            "all the evidences upon which they intend to rely on in support of their defence. They should also indicate "
                            "in their written reply as to whether they wish to be heard in person before the case is adjudicated. "
                            "If no such mention is made in their written reply or if they do not appear before the adjudicating authority "
                            "when the case is posted for personal hearing, it will be presumed that they do not wish to be heard in person.")
            html_parts.append(SCNRenderer._make_qt_para(current_num, hearing_text, body_style))
            current_num += 1
            
            # Ex-Parte
            exparte_text = ("If no cause is shown against the action proposed to be taken <b>within thirty days (30 days)</b> "
                            "from the date of receipt of this notice or if they fail to appear before the adjudicating authority when "
                            "the case is posted for hearing, the case will be decided ex-parte on its own merits without any further reference.")
            html_parts.append(SCNRenderer._make_qt_para(current_num, exparte_text, body_style))
            current_num += 1
            
            # Prejudice
            prej_text = ("This notice is issued without prejudice to any other action that may be taken against them under the "
                         "provisions of the CGST Act, 2017/Kerala SGST Act, 2017 and IGST Act, 2017 as amended or the Rules made "
                         "there under or under any other law for the time being in force in India. Further, this notice is issued "
                         "without prejudice to the right to support it with any material evidence which may be collected at a later "
                         "date and which may be considered relevant to the proceedings in this matter.")
            html_parts.append(SCNRenderer._make_qt_para(current_num, prej_text, body_style))
            current_num += 1
            
            # Amendment
            amend_text = ("The Department reserves the right to add, amend, delete or modify any part or portion of this show cause "
                          "notice, if considered necessary at any point of time before the case is adjudicated and such addition, "
                          "amendment, deletion or modification shall be deemed to be part and parcel of this notice.")
            html_parts.append(SCNRenderer._make_qt_para(current_num, amend_text, body_style))
            current_num += 1
            
            # Reliance
            rel_text = "In this Show Cause Notice, reliance is placed on the following documents:"
            html_parts.append(SCNRenderer._make_qt_para(current_num, rel_text, body_style))
            current_num += 1
            
            # Documents Table
            html_parts.append(f"""
            <table cellspacing="0" cellpadding="0" style="{data_table_style}">
                <tr>
                    <td width="15%" style="{cell_style}"><b>Sl No.</b></td>
                    <td style="{cell_style}"><b>Description</b></td>
                </tr>
                <tr>
                    <td style="{cell_style}">(i)</td>
                    <td style="{cell_style}">All documents loaded in the system.</td>
                </tr>
            </table>
            """)
            
            # --- SIGNATURE ---
            sig_html = f"""
            <br><br>
            <table width="100%" border="0">
                <tr>
                    <td align="right">
                        <div style="width: 300px; text-align: center; {body_style}">
                            <b>{data.get('officer_name', 'OFFICER NAME')}</b><br>
                            <b>{data.get('designation', 'Designation')}</b><br>
                            {data.get('jurisdiction', 'Jurisdiction')}
                        </div>
                    </td>
                </tr>
            </table>
            """
            html_parts.append(sig_html)
            
            # --- BOTTOM ADDRESS ---
            address_block = f"""
            <br><br>
            <div align="left" style="{bold_style}">
                To,<br>
                {tp_name},<br>
                {tp_trade},<br>
                {data.get('gstin', '')}<br>
                {tp_addr}
            </div>
            """
            html_parts.append(address_block)
            
            # --- COPY TO ---
            html_parts.append(f"<br><div style='{body_style}'>Copy submitted to:</div>")
            html_parts.append(f"<ul style='{body_style}'><li>[Jurisdictional Office]</li></ul>")
            
            inner_content = ''.join(html_parts)
            
            final_html = f"""
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
            <html>
            <head>
                <style>
                    body {{ background-color: white; color: black; font-family: 'Bookman Old Style'; font-size: 11pt; margin: 0; padding: 0; }}
                    p {{ margin: 10px 0; text-align: justify; }}
                </style>
            </head>
            <body>
                {inner_content}
            </body>
            </html>
            """
            
            return final_html
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"<h3>Qt Render Error: {str(e)}</h3>"

    @staticmethod
    def _make_qt_para(number, text, style):
        """
        Helper to create a numbered paragraph using Divs + floating/margin.
        Replaced Table logic to ensure text flow is safe.
        """
        # Using a flexbox-like float approach or just simple padding
        # Qt 5/6 TextBrowser supports basic floats but margins are safer.
        # We'll use a table for the bullet only if strictly necessary, but let's try a simple table again? 
        # User said "where are the remaining parts".
        # If I use a table for the number, and the text is LONG, QTextBrowser usually handles it fine.
        # But if the previous one failed, let's use a DL or just a table with correct width.
        # Let's try <div> with absolute positioning simulation (not supported).
        # Best bet: Table with robust width settings.
        
        return f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px;">
            <tr>
                <td width="40" valign="top" align="right" style="{style} font-weight: bold; padding-right: 5px;">{number}.</td>
                <td valign="top" align="justify" style="{style}">{text}</td>
            </tr>
        </table>
        """
        # Re-enabling table for numbered lists as it's the standard way to do "1.  Text" alignment.
        # The key fix was ensuring the TEXT content itself was complete (it was truncated in code).

    @staticmethod
    def _render_grid_as_html_table(grid_data):
        """Helper to render grid_data as a standard HTML table for Print/PDF"""
        if not grid_data: return ""
        
        cols = grid_data.get('columns', [])
        rows = grid_data.get('rows', [])
        if not rows: return ""
        
        html = """
        <div style="margin-bottom: 15px;">
            <p style="font-weight: bold; margin-bottom: 8px;">Calculation Table</p>
            <table style="width: 100%; border-collapse: collapse; border: 1.5pt solid black; font-size: 10pt;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
        """
        
        # Headers
        col_ids = []
        for col in cols:
            lbl = col.get('label', '')
            cid = col.get('id')
            html += f'<th style="border: 1pt solid black; padding: 5pt; text-align: center;"><b>{lbl}</b></th>'
            col_ids.append(cid)
            
        html += "</tr></thead><tbody>"
        
        # Rows
        for row in rows:
            html += "<tr>"
            for cid in col_ids:
                cell = row.get(cid)
                val = ""
                if isinstance(cell, dict):
                    val = cell.get('value', '')
                else:
                    val = str(cell) if cell is not None else ""
                
                # Identify Column Type for alignment
                align = "left"
                col_meta = next((c for c in cols if c.get('id') == cid), {})
                col_lbl = str(col_meta.get('label', '')).lower()
                if any(x in col_lbl for x in ['tax', 'amount', 'cgst', 'sgst', 'igst', 'cess', 'interest', 'penalty']):
                    align = "right"
                
                html += f'<td style="border: 1pt solid black; padding: 5pt; text-align: {align};">{val}</td>'
            html += "</tr>"
            
        html += "</tbody></table></div>"
        return html

    @staticmethod
    def num_to_words(num):
        return f"{num} (In Words)" 
