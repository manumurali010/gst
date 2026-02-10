import os
import sys
import argparse
import base64

# [STABILIZATION] isolated imports
# These are only imported when this script is run as a separate process.
# This prevents the main GUI process from ever touching these native dependencies.

def render_html_to_png(html_content, output_path):
    """
    Renders HTML content to a PNG image using WeasyPrint.
    [FIX] Enforces continuous scrolling (no pagination) for PNGs.
    """
    try:
        from weasyprint import HTML, CSS
        
        # [FIX] Inject CSS to force continuous page height
        # This ensures the PNG captures the full content height instead of just one A4 page.
        continuous_css = CSS(string="@page { size: 1000px auto; margin: 0; }")
        
        # Render HTML to PNG with stylesheets
        HTML(string=html_content).write_png(output_path, stylesheets=[continuous_css])
        return True, "Success"
    except OSError as e:
        # Catch Windows DLL errors (missing GTK)
        if "gobject" in str(e).lower() or "module" in str(e).lower() or "126" in str(e):
             return False, "MISSING_GTK_DEPENDENCY"
        return False, str(e)
    except Exception as e:
        return False, str(e)

def render_html_to_pdf(html_content, output_path):
    """
    Renders HTML content to a PDF file using WeasyPrint.
    """
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return True, "Success"
    except OSError as e:
        if "gobject" in str(e).lower() or "module" in str(e).lower() or "126" in str(e):
             return False, "MISSING_GTK_DEPENDENCY"
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Isolated Rendering Worker")
    parser.add_argument("--input", required=True, help="Path to input HTML file")
    parser.add_argument("--output", required=True, help="Path to output image/pdf file")
    parser.add_argument("--format", choices=["png", "pdf"], default="png", help="Output format")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)
        
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        if args.format == "png":
            success, msg = render_html_to_png(html_content, args.output)
        else:
            success, msg = render_html_to_pdf(html_content, args.output)
            
        if success:
            print(f"Result: SUCCESS")
            sys.exit(0)
        else:
            if msg == "MISSING_GTK_DEPENDENCY":
                 print("Result: FAILED - MISSING_GTK_DEPENDENCY")
                 sys.exit(5) # [STABILIZATION] Specific code for missing DLLs
            print(f"Result: FAILED - {msg}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Result: CRITICAL - {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()
