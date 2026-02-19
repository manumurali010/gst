
def generate_intro_narrative(grounds_data: dict) -> str:
    """
    Pure function to generate SCN introductory narrative (Grounds of SCN).
    Handles:
    - Manual Override (Returns stored manual text directly)
    - Automated Template (Fills placeholders, handles missing data with graceful omission)
    - Precision Grammar (Branching logic for issuance sentence)
    
    Returns:
        str: Clean HTML formatted string ready for insertion into SCN template.
    """
    if not grounds_data:
        return ""
    
    # 1. Manual/Rich Text: Return text as-is if available
    # Note: Logic has shifted to grounds_forms handling this, but keep for safety/backend use
    if grounds_data.get('is_intro_modified_by_user') or grounds_data.get('manual_override'):
        return grounds_data.get('manual_text', '')
        
    # 2. Automated Generation
    data = grounds_data.get('data', {})
    
    # Extract Fields with Semantic fallbacks (omit if missing)
    fy = data.get('financial_year')
    fy_fmt = f"<b>{fy}</b>" if fy else ""
    
    docs = data.get('docs_verified', [])
    if isinstance(docs, str): 
        docs = [d.strip() for d in docs.split(',')]
    docs_str = ", ".join(docs) if docs else ""
    docs_fmt = f"<b>{docs_str}</b>" if docs_str else ""
    
    asmt = data.get('asmt10_ref', {})
    asmt_oc = asmt.get('oc_no')
    asmt_date = asmt.get('date')
    officer = asmt.get('officer_designation')
    address = asmt.get('office_address')

    # Formatting Dates to dd-MM-yyyy if possible
    def _fmt_dt(dt_str):
        if not dt_str: return ""
        try:
            from datetime import datetime
            return datetime.strptime(dt_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
             try: return datetime.strptime(dt_str, "%Y-%m-%d").strftime("%d-%m-%Y")
             except: return dt_str

    asmt_dt_fmt = _fmt_dt(asmt_date)

    # Building Narratives
    p1 = f"Scrutiny of returns under Section 61 of CGST Act 2017"
    if fy_fmt:
        p1 += f" for the tax period {fy_fmt}"
    p1 += ", in respect of the said taxpayer was undertaken. "
    
    if docs_fmt:
        p1 += f"The said scrutiny of returns involved verification of {docs_fmt} and other relevant data available on the GST BO Portal"
        if fy_fmt: p1 += f" for the period {fy_fmt}"
        p1 += "."

    # Precision Grammar for Issuance Sentence
    asmt_ref = f"form GST ASMT-10"
    if asmt_oc:
        asmt_ref += f" vide O.C. No. <b>{asmt_oc}</b>"
    if asmt_dt_fmt:
        asmt_ref += f" dated <b>{asmt_dt_fmt}</b>"

    p2 = f"During the course of verification of the GST Returns furnished by the taxpayer, certain anomalies were noticed. "
    p2 += f"The said anomalies/discrepancies were communicated to the taxpayer in {asmt_ref}"

    # Branching for Case A, B, C
    if officer and address:
        # Case A
        p2 += f" issued by the <b>{officer}</b> of <b>{address}</b>."
    elif officer:
        # Case B
        p2 += f" issued by the <b>{officer}</b>."
    else:
        # Case C
        p2 += "."

    # Reply Logic
    reply = data.get('reply_ref', {})
    reply_received = reply.get('received', False)
    reply_date = _fmt_dt(reply.get('date'))
    
    p3 = ""
    if reply_received:
        if reply_date:
            p3 = f"In this regard, reply dated <b>{reply_date}</b> have been received from them."
        else:
            p3 = "In this regard, reply have been received from them."
    else:
        p3 = "In this regard, no reply has been received from them."
    
    # Standard Closing
    p4 = "The details of the discrepancies noticed are as under-"
    
    # Construct final Semantic HTML
    return f"<p>{p1}</p><p>{p2} {p3}</p><p>{p4}</p>"
