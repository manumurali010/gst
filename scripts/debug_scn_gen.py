import sys
import os
import tempfile
sys.path.append(os.getcwd())
from src.services.asmt10_generator import ASMT10Generator 
from src.utils.preview_generator import PreviewGenerator

def test_scn_pdf_generation():
    print("Testing SCN/Preview PDF Generation...")
    
    # Mock HTML content that is long enough to span multiple pages
    long_content = "<h1>SCN Preview Test</h1>"
    long_content += "<p>Start of Document</p>"
    for i in range(50):
        long_content += f"<p>Paragraph {i}: This is filler text to ensure we span multiple pages. We need to verify that the PDF generation handles pagination correctly and does not truncate content. This is line {i} of the long document test.</p>"
    long_content += "<h2>Page 2 Content (Expected)</h2>"
    for i in range(50):
        long_content += f"<p>Paragraph {i+50}: More filler text for page 2. This content should be visible in the multi-page preview.</p>"
    
    html = f"""
    <html>
    <head><style>
        @page {{ size: A4; margin: 20mm; }}
        body {{ font-family: sans-serif; }}
        p {{ margin-bottom: 10px; }}
    </style></head>
    <body>{long_content}</body>
    </html>
    """
    
    print("Generating PDF...")
    try:
        # Request all_pages=True, which invokes the PDF path
        images = PreviewGenerator.generate_preview_image(html, all_pages=True)
        
        if images and len(images) > 0:
            pdf_bytes = images[0]
            print(f"Success! Generated {len(pdf_bytes)} bytes of PDF data.")
            
            # Save for inspection
            with open("debug_scn_preview.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Saved debug_scn_preview.pdf")
            
            # Basic validation
            if len(pdf_bytes) > 1000:
                print("PDF size looks reasonable.")
            else:
                print("WARNING: PDF size is suspiciously small.")
                
        else:
            print("FAILED: No output generation.")
            
    except Exception as e:
        print(f"Error during generation: {e}")

if __name__ == "__main__":
    test_scn_pdf_generation()
