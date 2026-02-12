
def generate_intro_narrative(grounds_data: dict) -> str:
    """
    Pure function to generate SCN introductory narrative (Grounds of SCN).
    Handles:
    - Manual Override (Returns stored manual text directly)
    - Automated Template (Fills placeholders, handles missing data with [TAGS])
    - Conditional Logic (Reply received/not received)
    
    Returns:
        str: HTML formatted string ready for insertion into SCN template.
    """
    if not grounds_data:
        return ""
    
    # 1. Manual Override: Return text as-is (User is responsible for content)
    if grounds_data.get('manual_override'):
        text = grounds_data.get('manual_text', '')
        # Basic safety: Convert newlines to <br> if it's plain text? 
        # Assuming QTextEdit input might be HTML or plain text. 
        # For now, return as-is.
        return text or ""
        
    # 2. Automated Generation
    data = grounds_data.get('data', {})
    
    # Extract Fields with Bold Placeholders for Missing Data
    def _safe_get(val, placeholder):
        return f"<b>{val}</b>" if val else f"<b>[{placeholder}]</b>"

    fy = _safe_get(data.get('financial_year'), "FINANCIAL YEAR")
    
    docs = data.get('docs_verified', [])
    if isinstance(docs, str): 
        # specific fix for legacy string data
        docs = [d.strip() for d in docs.split(',')]
    
    docs_str = ", ".join(docs) if docs else "[DOCUMENTS VERIFIED]"
    docs_fmt = f"<b>{docs_str}</b>"
    
    asmt = data.get('asmt10_ref', {})
    asmt_oc = _safe_get(asmt.get('oc_no'), "ASMT-10 OC NO")
    asmt_date = _safe_get(asmt.get('date'), "ASMT-10 DATE")
    officer = _safe_get(asmt.get('officer_designation'), "OFFICER DESIGNATION")
    address = _safe_get(asmt.get('office_address'), "OFFICE ADDRESS")
    
    reply = data.get('reply_ref', {})
    reply_received = reply.get('received', False)
    reply_date = reply.get('date')
    
    # Construct Narrative
    # Note: Using <p> tags might interfere with SCN CSS. 
    # Use plain text with <br> as per existing template style.
    
    narrative = (
        f"Scrutiny of returns under Section 61 of CGST Act 2017 for the tax period {fy}, "
        f"in respect of the said taxpayer was undertaken. The said scrutiny of returns involved verification of "
        f"{docs_fmt} and other relevant data available on the GST BO Portal for the period {fy}.<br><br>"
        
        f"During the course of verification of the GST Returns furnished by the taxpayer, certain anomalies were noticed. "
        f"The said anomalies/discrepancies were communicated to the taxpayer in form GST ASMT-10 vide O.C. No. "
        f"{asmt_oc} dated {asmt_date} issued by the {officer} of {address}. "
    )
    
    if reply_received:
        r_date = _safe_get(reply_date, "REPLY DATE")
        narrative += f"In this regard, reply dated {r_date} have been received from them."
    else:
        narrative += "In this regard, no reply has been received from them."
        
    # Standard closing transition
    narrative += "<br>The details of the discrepancies noticed are as under-"
    
    return narrative
