import io
import fitz  # PyMuPDF
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    from xhtml2pdf import pisa
    WEASYPRINT_AVAILABLE = False

from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice

class PreviewGenerator:
    """
    Generates a live preview of the PDF document by:
    1. Converting HTML to PDF in-memory (using WeasyPrint or xhtml2pdf)
    2. Rendering the first page of the PDF to an image (using PyMuPDF)
    3. Returning the image bytes/QPixmap for display
    """
    
    @staticmethod
    def generate_preview_image(html_content, width=None, all_pages=False):
        """
        Generates a preview image from HTML content.
        
        Args:
            html_content (str): The HTML content to render.
            width (int, optional): Target width for the image. If None, uses original PDF width.
            all_pages (bool): If True, returns a list of bytes for all pages. If False, returns bytes for the first page.
            
        Returns:
            bytes or List[bytes]: PNG image bytes.
        """
        # 1. Generate PDF in-memory
        pdf_buffer = io.BytesIO()
        
        # Add basic styling if missing (similar to DocumentGenerator)
        if "<style>" not in html_content:
            style = """
            <style>
                @page { size: A4; margin: 1cm; }
                body { font-family: 'Bookman Old Style', serif; font-size: 11pt; text-align: justify; }
                table { border-collapse: collapse; width: 90%; margin: 0 auto; font-size: 10pt; }
                td, th { border: 1px solid black; padding: 2px 5px; text-align: center; }
            </style>
            """
            html_content = style + html_content
            
        # Try WeasyPrint first if available
        pdf_generated = False
        if WEASYPRINT_AVAILABLE:
            try:
                HTML(string=html_content).write_pdf(pdf_buffer)
                pdf_generated = True
            except Exception as e:
                print(f"WeasyPrint runtime error (switching to fallback): {e}")
        
        # Fallback to xhtml2pdf if WeasyPrint failed or is unavailable
        if not pdf_generated:
            try:
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
                if pisa_status.err:
                    print(f"PDF Generation Error (xhtml2pdf): {pisa_status.err}")
                    return [] if all_pages else None
            except Exception as e:
                print(f"Fallback PDF Generation Error: {e}")
                return [] if all_pages else None
            
        pdf_buffer.seek(0)
        
        # 2. Convert PDF page to Image (PyMuPDF)
        try:
            doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
            if doc.page_count == 0:
                return [] if all_pages else None
                
            # Set zoom factor for better resolution (e.g., 2.0 = 200% DPI)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            
            if all_pages:
                images = []
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    images.append(img_bytes)
                return images
            else:
                page = doc.load_page(0)  # Load first page
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                return img_bytes
            
        except Exception as e:
            print(f"Preview Rendering Error: {e}")
            return [] if all_pages else None

    @staticmethod
    def get_qpixmap_from_bytes(img_bytes):
        """Helper to convert bytes to QPixmap for PyQt"""
        if not img_bytes:
            return None
        
        image = QImage.fromData(img_bytes)
        return QPixmap.fromImage(image)

# Example Usage:
# html = "<html><body><h1>Hello World</h1></body></html>"
# png_bytes = PreviewGenerator.generate_preview_image(html)
# pixmap = PreviewGenerator.get_qpixmap_from_bytes(png_bytes)
# label.setPixmap(pixmap)
