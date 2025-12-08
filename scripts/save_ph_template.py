import sys
import os
from src.database.db_manager import DatabaseManager

# Add src to path
sys.path.append(os.getcwd())

def save_ph_template():
    print("Saving PH Template...")
    
    db = DatabaseManager()
    db.init_sqlite()
    
    html_content = """
<html>
<head>
<style>
    @page {
        size: A4;
        margin: 2cm;
    }
    body {
        font-family: 'Bookman Old Style', serif;
        font-size: 14px;
        line-height: 1.5;
        text-align: justify;
    }
    table.header-table {
        width: 100%;
        border: none;
        margin-bottom: 20px;
        font-weight: bold;
    }
    table.header-table td {
        border: none;
        padding: 0;
    }
    .address-block {
        margin-bottom: 20px;
    }
    .subject {
        text-align: center;
        font-weight: bold;
        margin: 20px 0;
        text-decoration: underline;
    }
    ol {
        margin-left: 20px;
    }
    li {
        margin-bottom: 15px;
    }
    .signature-block {
        margin-top: 50px;
        text-align: right;
        font-weight: bold;
    }
    .footer {
        margin-top: 30px;
    }
</style>
</head>
<body>

<table class="header-table">
    <tr>
        <td style="text-align: left;">O.C.NO. &lt;place holder&gt;</td>
        <td style="text-align: right;">Date: as e-signed</td>
    </tr>
</table>

<div class="address-block">
    To,<br>
    &lt;legal name&gt;<br>
    &lt;trade name&gt;<br>
    &lt;gstin&gt;<br>
    &lt;address&gt;
</div>

<p>Gentlemen/Sir/Madam,</p>

<div class="subject">
    Subject: Intimation of Personal Hearings – reg
</div>

<p><strong>References:</strong> 1. SCN reference number: &lt;place holder&gt; dated &lt;place holder&gt;</p>

<ol>
    <li>Please refer to the above mentioned SCN number issued by Office of the &lt;place holder&gt;.</li>
    
    <li>In this connection, it is to inform you that personal hearing in this case will be held at <strong>&lt;time&gt;</strong> on <strong>&lt;date&gt;</strong> before the &lt;officer designation&gt;, &lt;office address&gt;.</li>
    
    <li>You may therefore appear in person or through an authorized representative for the personal hearing on the above mentioned date and time as per your convenience, at the above mentioned address, without fail along with records/documents/evidences, you wish to rely upon in support of your case.</li>
</ol>

<div class="signature-block">
    Digitally signed by &lt;officer name&gt;<br>
    Date: &lt;current date&gt;<br><br>
    &lt;officer name&gt;<br>
    &lt;designation&gt;
</div>

<div class="footer">
    Copy submitted to:<br>
    1. The Deputy Commissioner of Central Tax & Central Excise, Aluva Division
</div>

</body>
</html>
"""

    data = {
        "name": "Personal Hearing Intimation",
        "type": "PH",
        "content": html_content,
        "version": "1.0",
        "is_default": 1
    }
    
    tmpl_id = db.save_template(data)
    if tmpl_id:
        print(f"SUCCESS: PH Template saved with ID {tmpl_id}")
    else:
        print("FAILURE: Template save failed")

if __name__ == "__main__":
    save_ph_template()
