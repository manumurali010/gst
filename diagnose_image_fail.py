
import sys
import io
import six
sys.modules['sklearn.externals.six'] = six
from xhtml2pdf import pisa

print("Diagnosing xhtml2pdf behavior with missing images...")

# HTML with a non-existent image
html_broken_img = """
<html>
<body>
    <h1>Testing Image Failure</h1>
    <img src="non_existent_image.png" />
    <p>Text after image.</p>
</body>
</html>
"""

pdf_buffer = io.BytesIO()

try:
    # Disable logging warnings to stdout to check return status purely
    pisa_status = pisa.CreatePDF(html_broken_img, dest=pdf_buffer)
    
    if pisa_status.err:
         print(f"[FAILURE] xhtml2pdf returned error code: {pisa_status.err}")
    else:
         print(f"[SUCCESS] xhtml2pdf ignored missing image. PDF Size: {pdf_buffer.getbuffer().nbytes} bytes")
         
    # Check log output manually if possible? xhtml2pdf prints to stdout/stderr
    
except Exception as e:
    print(f"[CRITICAL FAILURE] xhtml2pdf crashed: {e}")
