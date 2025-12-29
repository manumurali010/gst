try:
    from xhtml2pdf import pisa
    print("xhtml2pdf available")
except ImportError:
    print("xhtml2pdf not available")
except Exception as e:
    print(f"xhtml2pdf error: {e}")
