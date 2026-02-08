
import sys
import io

print("Diagnosing ASMT-10 Preview Dependencies...")

# Check WeasyPrint
try:
    from weasyprint import HTML
    print("[SUCCESS] WeasyPrint is importable.")
    WEASYPRINT = True
except Exception as e:
    print(f"[FAILURE] WeasyPrint could not be imported: {e}")
    WEASYPRINT = False

# Check xhtml2pdf
try:
    from xhtml2pdf import pisa
    print("[SUCCESS] xhtml2pdf is importable.")
    XHTML2PDF = True
except Exception as e:
    print(f"[FAILURE] xhtml2pdf could not be imported: {e}")
    XHTML2PDF = False

# Check PyMuPDF
try:
    import fitz
    print("[SUCCESS] PyMuPDF (fitz) is importable.")
    FITZ = True
except Exception as e:
    print(f"[FAILURE] PyMuPDF (fitz) could not be imported: {e}")
    FITZ = False

if not WEASYPRINT and not XHTML2PDF:
    print("\n[CRITICAL] No PDF generation backend available!")
    sys.exit(1)

# Simulation
print("\nSimulating PDF Generation (Test)...")
html = "<html><body><h1>Test</h1></body></html>"
pdf_buffer = io.BytesIO()

success = False
if WEASYPRINT:
    try:
        HTML(string=html).write_pdf(pdf_buffer)
        print("WeasyPrint Generation: SUCCESS")
        success = True
    except Exception as e:
        print(f"WeasyPrint Generation: FAILED ({e})")

if not success and XHTML2PDF:
    try:
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
        if pisa_status.err:
             print(f"xhtml2pdf Generation: FAILED (Err: {pisa_status.err})")
        else:
             print("xhtml2pdf Generation: SUCCESS")
             success = True
    except Exception as e:
        print(f"xhtml2pdf Generation: FAILED ({e})")

if success:
    pdf_buffer.seek(0)
    if FITZ:
        try:
            doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
            print(f"PyMuPDF Open: SUCCESS (Pages: {doc.page_count})")
        except Exception as e:
            print(f"PyMuPDF Open: FAILED ({e})")
