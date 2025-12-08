import sys
import os
from src.database.db_manager import DatabaseManager

def save_drc01a_template():
    print("Saving DRC-01A Template...")
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
    .center-bold {
        text-align: center;
        font-weight: bold;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }
    th, td {
        border: 1px solid black;
        padding: 8px;
        text-align: center;
    }
    .header-table td {
        border: none;
        text-align: left;
        padding: 0;
    }
    .address-block {
        margin: 20px 0;
    }
</style>
</head>
<body>

<div class="center-bold">&lt;letter head&gt;</div>
<br>

<table class="header-table">
    <tr>
        <td style="width: 50%; font-weight: bold;">O.C. No. &lt;o.c. No.&gt;</td>
        <td style="width: 50%; text-align: right; font-weight: bold;">Date: &lt;date&gt;</td>
    </tr>
</table>

<div class="center-bold">
    [FORM GST DRC-01A]<br>
    Intimation of tax ascertained as being payable under section 73(5)/74(5)<br>
    [See Rule 142 (1A)]<br>
    Part A
</div>
<br>

<table class="header-table">
    <tr>
        <td>No.: &lt;number&gt;</td>
        <td style="text-align: right;">Date: &lt;date&gt;</td>
    </tr>
    <tr>
        <td colspan="2">Case ID No. &lt;case_id&gt;</td>
    </tr>
</table>

<div class="address-block">
    To<br>
    &lt;GSTIN&gt;<br>
    &lt;Name &gt;<br>
    &lt;Address &gt;
</div>

<p><strong>Sub.: Intimation of liability under section 73(5)/section 74(5) – reg.</strong></p>

<p>Please refer to the above proceedings. In this regard, the amount of tax/interest/penalty payable by you under section 73(5) / 74(5) with reference to the said case as ascertained by the undersigned in terms of the available information, as is given below:</p>

<table>
    <thead>
        <tr>
            <th>ACT</th>
            <th>PERIOD</th>
            <th>TAX</th>
            <th>INTEREST</th>
            <th>PENALTY</th>
            <th>TOTAL</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>CGST ACT</td>
            <td>&lt;drop down of financial year&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;auto calculated&gt;</td>
        </tr>
        <tr>
            <td>SGST ACT</td>
            <td>&lt;drop down of financial year&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;auto calculated&gt;</td>
        </tr>
        <tr>
            <td>IGST ACT</td>
            <td>&lt;drop down of financial year&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;auto calculated&gt;</td>
        </tr>
        <tr>
            <td>CESS</td>
            <td>&lt;drop down of financial year&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;insert amount details&gt;</td>
            <td>&lt;auto calculated&gt;</td>
        </tr>
        <tr style="font-weight: bold;">
            <td>TOTAL</td>
            <td></td>
            <td>&lt;auto calculated&gt;</td>
            <td>&lt;auto calculated&gt;</td>
            <td>&lt;auto calculated&gt;</td>
            <td>&lt;auto calculated&gt;</td>
        </tr>
    </tbody>
</table>

<p>The grounds and quantification are attached / given below:</p>

<p>You are hereby advised to pay the amount of tax as ascertained above along with the amount of applicable interest in full by &lt;date&gt;, failing which Show Cause Notice will be issued under section 73(1).</p>

<p style="text-align: center;"><strong>&lt;OR&gt;</strong></p>

<p>You are hereby advised to pay the amount of tax as ascertained above along with the amount of applicable interest and penalty under section 74(5) by &lt;date&gt;, failing which Show Cause Notice will be issued under section 74(1).</p>

<p>In case you wish to file any submissions against the above ascertainment, the same may be furnished by &lt;date&gt; in Part B of this Form</p>

<br><br>

<div style="text-align: right;">
    &lt;Name &gt;<br>
    &lt;Designation&gt;
</div>

</body>
</html>
"""

    data = {
        "name": "DRC-01A",
        "type": "DRC-01A",
        "content": html_content,
        "description": "Intimation of tax ascertained as being payable under section 73(5)/74(5)"
    }
    
    try:
        template_id = db.save_template(data)
        print(f"SUCCESS: DRC-01A Template saved with ID {template_id}")
    except Exception as e:
        print(f"ERROR: Failed to save template. {e}")

if __name__ == "__main__":
    save_drc01a_template()
