
import sys
try:
    import weasyprint
    print(f"WeasyPrint Version: {weasyprint.__version__}")
    from weasyprint import HTML
    if hasattr(HTML, 'write_png'):
        print("write_png: AVAILABLE")
    else:
        print("write_png: MISSING (Newer WeasyPrint detected)")
except ImportError:
    print("WeasyPrint: NOT INSTALLED")
except Exception as e:
    print(f"Error checking WeasyPrint: {e}")
