import sys
import os
import tempfile
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

def create_dummy_pdf():
    # Create a dummy PDF file cleanly
    temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    # We'll use a known good PDF or try to just assume the file creation works.
    # Actually, let's copy a small empty PDF structure or just use text to see if browser fails safely.
    # Better: Use the PreviewGenerator logic if available, or just write "PDF-1.4..." dummy header
    # Minimal PDF:
    content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R/Resources<<>>>>endobj xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000111 00000 n\ntrailer<</Size 4/Root 1 0 R>>startxref\n190\n%%EOF"
    temp_pdf.write(content)
    temp_pdf.close()
    return temp_pdf.name

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Preview Debugger - Grey Screen Test")
        self.resize(800, 600)
        
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        
        self.webview = QWebEngineView()
        self.webview.settings().setAttribute(self.webview.settings().WebAttribute.PluginsEnabled, True)
        self.webview.settings().setAttribute(self.webview.settings().WebAttribute.PdfViewerEnabled, True)
        
        layout.addWidget(self.webview)
        
        # Test Load
        pdf_path = create_dummy_pdf()
        print(f"Loading PDF from: {pdf_path}")
        
        url = QUrl.fromLocalFile(pdf_path)
        print(f"URL: {url.toString()}")
        
        self.webview.setUrl(url)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
