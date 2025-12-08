from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QTextBrowser, QFileDialog, QMessageBox, QTabWidget, QWidget, QLineEdit,
                             QProgressBar)
from PyQt6.QtCore import Qt
from src.utils.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
import os
import shutil
import base64

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Letterhead tab
        letterhead_tab = self.create_letterhead_tab()
        tabs.addTab(letterhead_tab, "Letterhead")
        
        # General settings tab
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Data Management tab
        data_tab = self.create_data_management_tab()
        tabs.addTab(data_tab, "Data Management")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_letterhead_tab(self):
        """Create the letterhead management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Letterhead Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        desc = QLabel("Configure separate letterheads for PDF and Word documents")
        desc.setStyleSheet("color: #7f8c8d; margin-bottom: 20px;")
        layout.addWidget(desc)
        
        # PDF Letterhead Section
        pdf_section = QLabel("PDF Letterhead (HTML only)")
        pdf_section.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px; color: #e74c3c;")
        layout.addWidget(pdf_section)
        
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(QLabel("Select:"))
        
        self.pdf_letterhead_combo = QComboBox()
        self.pdf_letterhead_combo.setMinimumWidth(300)
        self.populate_pdf_letterheads()
        self.pdf_letterhead_combo.currentIndexChanged.connect(self.preview_pdf_letterhead)
        pdf_layout.addWidget(self.pdf_letterhead_combo)
        
        set_pdf_btn = QPushButton("Set for PDF")
        set_pdf_btn.clicked.connect(self.set_pdf_letterhead)
        set_pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 16px; font-weight: bold;")
        pdf_layout.addWidget(set_pdf_btn)
        
        pdf_layout.addStretch()
        layout.addLayout(pdf_layout)
        
        # Word Letterhead Section
        word_section = QLabel("Word Letterhead (HTML or DOCX)")
        word_section.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px; color: #27ae60;")
        layout.addWidget(word_section)
        
        word_layout = QHBoxLayout()
        word_layout.addWidget(QLabel("Select:"))
        
        self.word_letterhead_combo = QComboBox()
        self.word_letterhead_combo.setMinimumWidth(300)
        self.populate_word_letterheads()
        self.word_letterhead_combo.currentIndexChanged.connect(self.preview_word_letterhead)
        word_layout.addWidget(self.word_letterhead_combo)
        
        set_word_btn = QPushButton("Set for Word")
        set_word_btn.clicked.connect(self.set_word_letterhead)
        set_word_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 16px; font-weight: bold;")
        word_layout.addWidget(set_word_btn)
        
        word_layout.addStretch()
        layout.addLayout(word_layout)
        
        # Upload section
        upload_layout = QHBoxLayout()
        upload_layout.addWidget(QLabel("Manage:"))
        
        upload_btn = QPushButton("Upload Letterhead (HTML/DOCX)")
        upload_btn.clicked.connect(self.upload_letterhead)
        upload_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 16px; font-weight: bold;")
        upload_layout.addWidget(upload_btn)
        
        upload_png_btn = QPushButton("Upload PNG Letterhead")
        upload_png_btn.clicked.connect(self.upload_png_letterhead)
        upload_png_btn.setStyleSheet("background-color: #9b59b6; color: white; padding: 8px 16px; font-weight: bold;")
        upload_layout.addWidget(upload_png_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_letterhead)
        delete_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 16px; font-weight: bold;")
        upload_layout.addWidget(delete_btn)
        
        upload_layout.addStretch()
        layout.addLayout(upload_layout)
        
        # Preview section
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(preview_label)
        
        self.preview_browser = QTextBrowser()
        self.preview_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #dadce0;
                border-radius: 4px;
                background-color: white;
            }
        """)
        layout.addWidget(self.preview_browser)
        
        # Load initial preview
        self.preview_pdf_letterhead()
        
        return widget
    
    def create_general_tab(self):
        """Create the general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("General Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Office Name
        office_layout = QHBoxLayout()
        office_layout.addWidget(QLabel("Office Name:"))
        self.office_input = QLineEdit()
        self.office_input.setText(self.config.get_setting('office_name', ''))
        self.office_input.setPlaceholderText("e.g., GST Department - Paravur Range")
        office_layout.addWidget(self.office_input)
        layout.addLayout(office_layout)
        
        # Jurisdiction
        jurisdiction_layout = QHBoxLayout()
        jurisdiction_layout.addWidget(QLabel("Jurisdiction:"))
        self.jurisdiction_input = QLineEdit()
        self.jurisdiction_input.setText(self.config.get_setting('jurisdiction', ''))
        self.jurisdiction_input.setPlaceholderText("e.g., Kerala")
        jurisdiction_layout.addWidget(self.jurisdiction_input)
        layout.addLayout(jurisdiction_layout)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_general_settings)
        save_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 16px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return widget
    
    def populate_pdf_letterheads(self):
        """Populate the PDF letterhead dropdown (HTML only)"""
        self.pdf_letterhead_combo.clear()
        letterheads = self.config.get_available_letterheads()
        
        # Filter to HTML only
        html_letterheads = [lh for lh in letterheads if lh.endswith('.html')]
        
        if not html_letterheads:
            self.pdf_letterhead_combo.addItem("No HTML letterheads found")
            return
            
        current_pdf = self.config.get_pdf_letterhead()
        
        for letterhead in html_letterheads:
            display_name = letterhead
            if letterhead == current_pdf:
                display_name += " (Current)"
            self.pdf_letterhead_combo.addItem(display_name, letterhead)
        
        # Select the current PDF letterhead
        index = self.pdf_letterhead_combo.findData(current_pdf)
        if index >= 0:
            self.pdf_letterhead_combo.setCurrentIndex(index)
    
    def populate_word_letterheads(self):
        """Populate the Word letterhead dropdown (HTML or DOCX)"""
        self.word_letterhead_combo.clear()
        letterheads = self.config.get_available_letterheads()
        
        if not letterheads:
            self.word_letterhead_combo.addItem("No letterheads found")
            return
            
        current_word = self.config.get_word_letterhead()
        
        for letterhead in letterheads:
            display_name = letterhead
            if letterhead == current_word:
                display_name += " (Current)"
            self.word_letterhead_combo.addItem(display_name, letterhead)
        
        # Select the current Word letterhead
        index = self.word_letterhead_combo.findData(current_word)
        if index >= 0:
            self.word_letterhead_combo.setCurrentIndex(index)
    
    def preview_pdf_letterhead(self):
        """Preview the selected PDF letterhead"""
        if self.pdf_letterhead_combo.count() == 0 or self.pdf_letterhead_combo.currentData() is None:
            return
            
        letterhead_name = self.pdf_letterhead_combo.currentData()
        letterhead_path = os.path.join(self.config.letterheads_dir, letterhead_name)
        
        try:
            with open(letterhead_path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.preview_browser.setHtml(html)
        except Exception as e:
            self.preview_browser.setPlainText(f"Error loading letterhead: {e}")
    
    def preview_word_letterhead(self):
        """Preview the selected Word letterhead"""
        if self.word_letterhead_combo.count() == 0 or self.word_letterhead_combo.currentData() is None:
            return
            
        letterhead_name = self.word_letterhead_combo.currentData()
        letterhead_path = os.path.join(self.config.letterheads_dir, letterhead_name)
        
        # Check if DOCX
        if letterhead_name.endswith('.docx'):
            self.preview_browser.setHtml("""
                <html>
                <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h2 style="color: #27ae60;">📄 DOCX Letterhead for Word Documents</h2>
                    <p style="color: #7f8c8d; font-size: 14px;">
                        Preview not available for Word documents.<br>
                        The letterhead will be applied when generating Word documents.
                    </p>
                    <p style="margin-top: 30px; padding: 20px; background-color: #ecf0f1; border-radius: 5px;">
                        <strong>File:</strong> {}<br>
                        <strong>Type:</strong> Microsoft Word Document (.docx)
                    </p>
                </body>
                </html>
            """.format(letterhead_name))
            return
        
        # HTML letterhead - show preview
        try:
            with open(letterhead_path, 'r', encoding='utf-8') as f:
                html = f.read()
            self.preview_browser.setHtml(html)
        except Exception as e:
            self.preview_browser.setPlainText(f"Error loading letterhead: {e}")
    
    def set_pdf_letterhead(self):
        """Set the selected letterhead for PDF generation"""
        if self.pdf_letterhead_combo.currentData() is None:
            return
            
        letterhead_name = self.pdf_letterhead_combo.currentData()
        
        if self.config.set_pdf_letterhead(letterhead_name):
            QMessageBox.information(self, "Success", f"'{letterhead_name}' set for PDF generation.")
            self.populate_pdf_letterheads()  # Refresh to show (Current) marker
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")
    
    def set_word_letterhead(self):
        """Set the selected letterhead for Word generation"""
        if self.word_letterhead_combo.currentData() is None:
            return
            
        letterhead_name = self.word_letterhead_combo.currentData()
        
        if self.config.set_word_letterhead(letterhead_name):
            QMessageBox.information(self, "Success", f"'{letterhead_name}' set for Word generation.")
            self.populate_word_letterheads()  # Refresh to show (Current) marker
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")
    
    def upload_letterhead(self):
        """Upload a custom letterhead HTML or DOCX file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Letterhead File",
            "",
            "Letterhead Files (*.html *.htm *.docx);;HTML Files (*.html *.htm);;Word Files (*.docx)"
        )
        
        if not file_path:
            return
        
        # Determine file type
        is_docx = file_path.endswith('.docx')
        
        # Validate file
        try:
            if is_docx:
                # For DOCX, just check if it's a valid file
                # No specific validation needed - Word will handle it
                pass
            else:
                # For HTML, check for required placeholders
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                if 'form-header-placeholder' not in html_content:
                    QMessageBox.warning(
                        self,
                        "Invalid Letterhead",
                        "The HTML letterhead must contain a <div id=\"form-header-placeholder\"> element.\n\n"
                        "Please refer to the template documentation."
                    )
                    return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read file: {e}")
            return
        
        # Copy to letterheads directory
        filename = os.path.basename(file_path)
        dest_path = os.path.join(self.config.letterheads_dir, filename)
        
        # Check if file already exists
        if os.path.exists(dest_path):
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"'{filename}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        try:
            shutil.copy2(file_path, dest_path)
            QMessageBox.information(self, "Success", f"Letterhead '{filename}' uploaded successfully!")
            self.populate_letterheads()
            
            # Select the newly uploaded letterhead
            index = self.pdf_letterhead_combo.findData(filename)
            if index >= 0:
                self.pdf_letterhead_combo.setCurrentIndex(index)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload letterhead: {e}")
    
    def upload_png_letterhead(self):
        """Upload a PNG letterhead and convert to HTML"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PNG Letterhead Image",
            "",
            "PNG Images (*.png)"
        )
        
        if not file_path:
            return
        
        try:
            # Read PNG and convert to Base64
            with open(file_path, 'rb') as f:
                png_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Get filename without extension
            png_filename = os.path.basename(file_path)
            base_name = os.path.splitext(png_filename)[0]
            
            # Create HTML with embedded PNG
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        .letterhead-container {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .letterhead-img {{
            max-width: 100%;
            width: 800px;
            height: auto;
            display: block;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="letterhead-container">
        <img src="data:image/png;base64,{png_data}" class="letterhead-img" alt="Letterhead">
    </div>
    
    <!-- REQUIRED: Form content placeholder -->
    <div id="form-header-placeholder"></div>
</body>
</html>'''
            
            # Save PNG file
            png_dest = os.path.join(self.config.letterheads_dir, png_filename)
            shutil.copy2(file_path, png_dest)
            
            # Save HTML file
            html_filename = f"{base_name}_png.html"
            html_dest = os.path.join(self.config.letterheads_dir, html_filename)
            
            with open(html_dest, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            QMessageBox.information(
                self,
                "Success",
                f"PNG letterhead uploaded successfully!\n\n"
                f"Saved as:\n"
                f"- {png_filename} (original PNG)\n"
                f"- {html_filename} (for PDF generation)\n\n"
                f"You can now set it for PDF and/or Word generation."
            )
            
            # Refresh dropdowns
            self.populate_pdf_letterheads()
            self.populate_word_letterheads()
            
            # Auto-select the new HTML letterhead for PDF
            index = self.pdf_letterhead_combo.findData(html_filename)
            if index >= 0:
                self.pdf_letterhead_combo.setCurrentIndex(index)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload PNG letterhead: {e}")
    
    def delete_letterhead(self):
        """Delete the selected letterhead"""
        # Get the currently selected letterhead from whichever combo is active
        letterhead_name = None
        if self.pdf_letterhead_combo.currentData():
            letterhead_name = self.pdf_letterhead_combo.currentData()
        elif self.word_letterhead_combo.currentData():
            letterhead_name = self.word_letterhead_combo.currentData()
        
        if not letterhead_name:
            return
        
        # Prevent deleting default.html
        if letterhead_name == 'default.html':
            QMessageBox.warning(self, "Cannot Delete", "The default letterhead cannot be deleted.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{letterhead_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        letterhead_path = os.path.join(self.config.letterheads_dir, letterhead_name)
        
        try:
            os.remove(letterhead_path)
            QMessageBox.information(self, "Success", f"'{letterhead_name}' deleted successfully.")
            
            # If deleted letterhead was in use, reset to default.html
            if self.config.get_pdf_letterhead() == letterhead_name:
                self.config.set_pdf_letterhead('default.html')
            if self.config.get_word_letterhead() == letterhead_name:
                self.config.set_word_letterhead('default.html')
            
            # Refresh both dropdowns
            self.populate_pdf_letterheads()
            self.populate_word_letterheads()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete letterhead: {e}")
    
    
    def create_data_management_tab(self):
        """Create the data management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Data Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Update Taxpayers Section
        taxpayer_section = QLabel("Update Taxpayer Database")
        taxpayer_section.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(taxpayer_section)
        
        desc = QLabel("Import taxpayer data from Excel file to update the database.")
        desc.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Excel File:"))
        
        self.taxpayer_file_input = QLineEdit()
        self.taxpayer_file_input.setPlaceholderText("Select Excel file...")
        self.taxpayer_file_input.setReadOnly(True)
        file_layout.addWidget(self.taxpayer_file_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_taxpayer_file)
        browse_btn.setStyleSheet("padding: 8px 16px;")
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Progress bar
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        layout.addWidget(self.import_progress)
        
        # Import button
        import_btn = QPushButton("Import Taxpayers")
        import_btn.clicked.connect(self.import_taxpayers)
        import_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px 20px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(import_btn)
        
        # Status label
        self.import_status = QLabel("")
        self.import_status.setStyleSheet("margin-top: 10px; font-weight: bold;")
        layout.addWidget(self.import_status)
        
        layout.addStretch()
        
        return widget
    
    def browse_taxpayer_file(self):
        """Browse for taxpayer Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Taxpayer Excel File",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.taxpayer_file_input.setText(file_path)
    
    def import_taxpayers(self):
        """Import taxpayers from Excel file"""
        file_path = self.taxpayer_file_input.text()
        
        if not file_path:
            QMessageBox.warning(self, "No File Selected", "Please select an Excel file first.")
            return
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The selected file does not exist.")
            return
        
        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "This will update the taxpayer database. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Show progress
        self.import_progress.setVisible(True)
        self.import_progress.setValue(0)
        self.import_status.setText("Importing...")
        
        try:
            # Import taxpayers
            self.db.import_taxpayers(file_path)
            
            self.import_progress.setValue(100)
            self.import_status.setText("✓ Import completed successfully!")
            self.import_status.setStyleSheet("margin-top: 10px; font-weight: bold; color: #27ae60;")
            
            QMessageBox.information(self, "Success", "Taxpayer database updated successfully!")
            
        except Exception as e:
            self.import_progress.setValue(0)
            self.import_status.setText(f"✗ Import failed: {str(e)}")
            self.import_status.setStyleSheet("margin-top: 10px; font-weight: bold; color: #e74c3c;")
            
            QMessageBox.critical(self, "Import Failed", f"Failed to import taxpayers:\n{str(e)}")
        
        finally:
            self.import_progress.setVisible(False)
    
    def save_general_settings(self):
        """Save general settings"""
        self.config.set_setting('office_name', self.office_input.text())
        self.config.set_setting('jurisdiction', self.jurisdiction_input.text())
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
