from weasyprint import HTML
import sys

try:
    html = "<h1>Test</h1><p>WeasyPrint check</p>"
    HTML(string=html).write_pdf("test_weasy.pdf")
    print("WeasyPrint success")
except Exception as e:
    print(f"WeasyPrint failed: {e}")
    # Fallback check for xhtml2pdf
    try:
        from xhtml2pdf import pisa
        print("xhtml2pdf available")
    except ImportError:
        print("xhtml2pdf not installed")
