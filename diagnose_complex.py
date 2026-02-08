
import sys
import io
import six
# Patch for xhtml2pdf
sys.modules['sklearn.externals.six'] = six
from xhtml2pdf import pisa

print("Diagnosing Complex HTML Rendering with xhtml2pdf...")

complex_html = """
<html>
<head>
<style>
    @page { size: A4; margin: 1cm; }
    body { font-family: 'Helvetica', sans-serif; font-size: 10pt; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    th, td { border: 1px solid #000; padding: 5px; text-align: left; }
    th { background-color: #f2f2f2; }
    .header { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .meta-table td { border: none; padding: 2px; }
</style>
</head>
<body>

<div class="header">FORM GST ASMT-10</div>

<table class="meta-table">
    <tr><td>Reference No.:</td><td><b>OC12345</b></td></tr>
    <tr><td>Date:</td><td><b>2023-11-30</b></td></tr>
    <tr><td>GSTIN:</td><td><b>29ABCDE1234F1Z5</b></td></tr>
</table>

<p><b>Subject: Scrutiny of Returns for FY 2022-23 - Reg.</b></p>

<p>This is to inform that...</p>

<table>
    <thead>
        <tr>
            <th>Sr. No.</th>
            <th>Description</th>
            <th>IGST</th>
            <th>CGST</th>
            <th>SGST</th>
            <th>Cess</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td>
            <td>Tax Liability (Declar)</td>
            <td>1000.00</td>
            <td>500.00</td>
            <td>500.00</td>
            <td>0.00</td>
        </tr>
        <tr>
            <td>2</td>
            <td>Tax Liability (Report)</td>
            <td>800.00</td>
            <td>500.00</td>
            <td>500.00</td>
            <td>0.00</td>
        </tr>
        <tr>
            <td>3</td>
            <td>Difference</td>
            <td>200.00</td>
            <td>0.00</td>
            <td>0.00</td>
            <td>0.00</td>
        </tr>
    </tbody>
</table>

</body>
</html>
"""

pdf_buffer = io.BytesIO()

try:
    pisa_status = pisa.CreatePDF(complex_html, dest=pdf_buffer)
    if pisa_status.err:
         print(f"[FAILURE] xhtml2pdf returned error code: {pisa_status.err}")
    else:
         print(f"[SUCCESS] xhtml2pdf rendered complex HTML. PDF Size: {pdf_buffer.getbuffer().nbytes} bytes")
except Exception as e:
    print(f"[CRITICAL FAILURE] xhtml2pdf crashed: {e}")
