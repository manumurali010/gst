from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QTextBrowser, QFileDialog, QMessageBox, QTabWidget, QLineEdit,
                             QProgressBar, QFrame, QListWidget, QListWidgetItem, QSplitter, QApplication,
                             QSlider, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QColor
from src.utils.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
import os
import shutil
import base64

import base64

class FileUploaderWidget(QFrame):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.file_path = ""
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        lbl = QLabel(label_text)
        lbl.setFixedWidth(140)
        lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(lbl)
        
        self.path_lbl = QLabel("No file selected")
        self.path_lbl.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.path_lbl)
        
        layout.addStretch()
        
        self.browse_btn = QPushButton("Select File")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet("""
            QPushButton { background-color: #ecf0f1; color: #2c3e50; border: 1px solid #bdc3c7; padding: 5px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #bdc3c7; }
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        layout.addWidget(self.browse_btn)
        
        self.setFixedHeight(40)
        
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.file_path = file_path
            self.path_lbl.setText(os.path.basename(file_path))
            self.path_lbl.setStyleSheet("color: #2c3e50; font-weight: bold;")
            
    def text(self):
        """Compatibility with QLineEdit for existing logic"""
        return self.file_path
        
    def clear(self):
        self.file_path = ""
        self.path_lbl.setText("No file selected")
        self.path_lbl.setStyleSheet("color: #7f8c8d; font-style: italic;")

class LetterheadListItem(QWidget):
    def __init__(self, filename, is_default, set_default_cb, delete_cb):
        super().__init__()
        self.filename = filename
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Icon/Name
        icon = "📄" if filename.endswith('.pdf') else "🖼️"
        name_lbl = QLabel(f"{icon} {filename}")
        name_lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(name_lbl)
        
        layout.addStretch()
        
        # Badges/Buttons
        if is_default:
            badge = QLabel("Default")
            badge.setStyleSheet("background-color: #27ae60; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;")
            layout.addWidget(badge)
        else:
            set_btn = QPushButton("Set Default")
            set_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            set_btn.setStyleSheet("""
                QPushButton { background-color: #ecf0f1; border: none; padding: 4px 8px; border-radius: 4px; color: #2c3e50; }
                QPushButton:hover { background-color: #bdc3c7; }
            """)
            set_btn.clicked.connect(lambda: set_default_cb(filename))
            layout.addWidget(set_btn)
            
        del_btn = QPushButton("🗑️")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Delete Letterhead")
        del_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #e74c3c; font-size: 14px; border: none; }
            QPushButton:hover { background-color: #fae5e3; border-radius: 3px; }
        """)
        del_btn.clicked.connect(lambda: delete_cb(filename))
        layout.addWidget(del_btn)

class SettingsTab(QWidget):
    def __init__(self, check_nav_callback=None):
        super().__init__()
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.check_nav_callback = check_nav_callback
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; background: white; border-radius: 5px; }
            QTabBar::tab { padding: 10px 20px; font-weight: bold; color: #555; }
            QTabBar::tab:selected { color: #2c3e50; border-bottom: 2px solid #3498db; }
        """)
        
        # Letterhead tab
        letterhead_tab = self.create_letterhead_tab()
        self.tabs.addTab(letterhead_tab, "Letterhead")
        
        # General settings tab
        general_tab = self.create_general_tab()
        self.tabs.addTab(general_tab, "General")
        
        # Data Management tab
        data_tab = self.create_data_management_tab()
        self.tabs.addTab(data_tab, "Data Management")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Go Home")
        close_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        close_btn.clicked.connect(self.go_home)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def go_home(self):
        if self.check_nav_callback:
            self.check_nav_callback()

    def create_letterhead_tab(self):
        """Create the modernized split-pane letterhead tab"""
        widget = QWidget()
        # widget.setStyleSheet("background-color: #f8f9fa;")
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # === LEFT PANE: Manager (Compact) ===
        left_pane = QFrame()
        left_pane.setFixedWidth(280)
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. Compact Header & Add Button
        head_layout = QHBoxLayout()
        list_header = QLabel("My Letterheads")
        list_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        head_layout.addWidget(list_header)
        
        head_layout.addStretch()
        
        add_btn = QPushButton("⊕ Upload")
        add_btn.setFixedWidth(80)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.upload_png_letterhead)
        add_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 4px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        head_layout.addWidget(add_btn)
        left_layout.addLayout(head_layout)

        # 2. List Widget
        self.lh_list = QListWidget()
        self.lh_list.setStyleSheet("""
            QListWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; }
            QListWidget::item { border-bottom: 1px solid #f1f5f9; padding: 2px; }
            QListWidget::item:selected { background-color: #f0f9ff; border: 1px solid #3498db; border-radius: 4px; }
        """)
        self.lh_list.itemClicked.connect(self.on_letterhead_selected)
        left_layout.addWidget(self.lh_list)
        
        tip = QLabel("Select a letterhead to adjust its size and position directly in the preview.")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        left_layout.addWidget(tip)

        main_layout.addWidget(left_pane)

        # === RIGHT PANE: Interactive Canvas ===
        right_pane = QFrame()
        right_pane.setStyleSheet("background-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Action Bar (Top)
        self.action_bar = QFrame()
        self.action_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #e2e8f0;")
        self.action_bar.setFixedHeight(50)
        ab_layout = QHBoxLayout(self.action_bar)
        ab_layout.setContentsMargins(20, 0, 20, 0)
        
        ab_title = QLabel("🎨 Visual Designer")
        ab_title.setStyleSheet("font-weight: bold; color: #1e293b; font-size: 14px;")
        ab_layout.addWidget(ab_title)
        
        ab_layout.addStretch()
        
        self.save_adj_btn = QPushButton("💾 Save Designer Changes")
        self.save_adj_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_adj_btn.setStyleSheet("""
            QPushButton { background-color: #059669; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #047857; }
        """)
        self.save_adj_btn.clicked.connect(self.save_letterhead_adjustments)
        self.save_adj_btn.setVisible(False)
        ab_layout.addWidget(self.save_adj_btn)
        
        right_layout.addWidget(self.action_bar)
        
        self.preview_browser = QWebEngineView()
        self.preview_browser.setStyleSheet("background-color: #525659;")
        right_layout.addWidget(self.preview_browser)
        
        main_layout.addWidget(right_pane)
        
        # Initialize List
        self.refresh_letterhead_list()
        
        return widget

    def refresh_letterhead_list(self):
        """Populate the list of letterheads"""
        self.lh_list.clear()
        
        # Explicitly clear preview first to avoid stale state
        self.preview_browser.setHtml("") 
        
        # Get all files
        all_files = self.config.get_available_letterheads()
        # Get current default (checking PDF as primary source of truth, but they should sync)
        current_default = self.config.get_pdf_letterhead()
        
        found_default_in_list = False
        
        for fname in all_files:
            # We filter for HTML mainly, as PNGs are converted to HTML
            if not fname.endswith('.html'): continue 
            
            is_def = (fname == current_default)
            
            item = QListWidgetItem(self.lh_list)
            item.setSizeHint(QSize(400, 60))
            
            # Create custom widget
            widget = LetterheadListItem(fname, is_def, self.set_as_default, self.delete_letterhead)
            self.lh_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, fname) # Store filename
            
            if is_def:
                item.setSelected(True)
                self.preview_letterhead(fname)
                found_default_in_list = True

        # If the default file was not found (e.g. missing 'default.html'), select the first item if available
        if not found_default_in_list and self.lh_list.count() > 0:
            first_item = self.lh_list.item(0)
            first_item.setSelected(True)
            fname = first_item.data(Qt.ItemDataRole.UserRole)
            self.preview_letterhead(fname)

    def on_letterhead_selected(self, item):
        fname = item.data(Qt.ItemDataRole.UserRole)
        self.preview_letterhead(fname)

    def preview_letterhead(self, filename):
        self.current_preview_lh = filename
        
        # Show designer save button only for HTML (which we generated from PNG)
        is_designer_format = filename.endswith('.html')
        self.save_adj_btn.setVisible(is_designer_format)
        
        path = os.path.join(self.config.letterheads_dir, filename)
        
        # Read the file content and extract body
        letterhead_body = ""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                match = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL | re.IGNORECASE)
                if match:
                    letterhead_body = match.group(1)
                else:
                    letterhead_body = content
        except Exception as e:
            letterhead_body = f"<div style='color:red;'>Error loading letterhead: {str(e)}</div>"

        # A4 High-Fidelity Simulator HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    background-color: #525659;
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    justify-content: center;
                    font-family: Arial, sans-serif;
                }}
                .page {{
                    background-color: white;
                    width: 210mm;
                    min-height: 297mm;
                    padding: 0;
                    box-shadow: 0 0 20px rgba(0,0,0,0.5);
                    position: relative;
                    overflow: hidden;
                }}
                .designer-surface {{
                    width: 100%;
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="designer-surface">
                    {letterhead_body}
                </div>
            </div>
            <script>
                // Use a slight delay to ensure DOM is ready
                setTimeout(() => {{
                    const container = document.querySelector('.letterhead-container');
                    const img = document.querySelector('.letterhead-img');
                    if(!img || !container) return;

                    // Setup Designer Visuals
                    container.style.border = '2px dashed #3498db';
                    container.style.position = 'relative';
                    container.style.cursor = 'ns-resize';
                    container.title = 'Drag up/down to adjust vertical position';

                    // Add Resize Handle
                    const handle = document.createElement('div');
                    Object.assign(handle.style, {{
                        width: '18px', height: '18px', background: '#3498db',
                        position: 'absolute', right: '0', bottom: '0',
                        cursor: 'nwse-resize', borderRadius: '50%',
                        border: '3px solid white', boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
                        zIndex: '1000'
                    }});
                    handle.title = 'Drag to resize logo';
                    container.appendChild(handle);

                    let isResizing = false;
                    let isDragging = false;
                    let startX, startY, startWidth, startPaddingTop;

                    document.onmousedown = (e) => {{
                        if(e.target === handle) {{
                            isResizing = true;
                            startX = e.clientX;
                            startWidth = img.offsetWidth;
                            e.preventDefault();
                        }} else if(container.contains(e.target)) {{
                            isDragging = true;
                            startY = e.clientY;
                            startPaddingTop = parseInt(window.getComputedStyle(container).paddingTop) || 0;
                            e.preventDefault();
                        }}
                    }};

                    document.onmousemove = (e) => {{
                        if(isResizing) {{
                            const delta = e.clientX - startX;
                            img.style.width = (startWidth + delta) + 'px';
                        }} else if(isDragging) {{
                            const delta = e.clientY - startY;
                            container.style.paddingTop = Math.max(0, startPaddingTop + delta) + 'px';
                        }}
                    }};

                    document.onmouseup = () => {{
                        isResizing = false;
                        isDragging = false;
                    }};
                    
                    // Expose data getter
                    window.getVisualState = function() {{
                        return {{
                            width: img.offsetWidth,
                            padding_top: parseInt(window.getComputedStyle(container).paddingTop) || 0
                        }};
                    }};
                }}, 100);
            </script>
        </body>
        </html>
        """
        self.preview_browser.setHtml(html)


    def save_letterhead_adjustments(self):
        """Fetch values from the JS designer and persist to config/files"""
        if not hasattr(self, 'current_preview_lh') or not self.current_preview_lh:
            return
            
        def on_callback(js_val):
            if not js_val: return
            
            filename = self.current_preview_lh
            width = js_val.get('width', 800)
            pt = js_val.get('padding_top', 0)
            mb = 20 # Keep margin bottom stable
            
            # 1. Save to settings.json
            self.config.set_letterhead_adjustments(filename, width, pt, mb)
            
            # 2. Update the HTML file Source
            path = os.path.join(self.config.letterheads_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                import re
                if '.letterhead-container' in content and 'data:image/png;base64,' in content:
                    b64_match = re.search(r'data:image/png;base64,([^"]+)', content)
                    if b64_match:
                        png_data = b64_match.group(1)
                        new_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
    <div class="letterhead-container" style="text-align: center; padding-top: {pt}px; margin-bottom: {mb}px;">
        <img src="data:image/png;base64,{png_data}" class="letterhead-img" style="max-width: 100%; width: {width}px; height: auto; display: block; margin: 10px auto;" alt="Letterhead">
    </div>
    <div id="form-header-placeholder"></div>
</body>
</html>'''
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_html)
                
                QMessageBox.information(self, "Success", "Designer changes successfully applied to documents!")
                self.preview_letterhead(filename)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save adjustments: {str(e)}")

        self.preview_browser.page().runJavaScript("window.getVisualState()", on_callback)

    def set_as_default(self, filename):
        """Set as default for BOTH PDF and Word"""
        self.config.set_pdf_letterhead(filename)
        self.config.set_word_letterhead(filename)
        QMessageBox.information(self, "Updated", f"'{filename}' set as default letterhead.")
        self.refresh_letterhead_list()

    def delete_letterhead(self, filename):
        if filename == 'default.html':
            QMessageBox.warning(self, "Stop", "Cannot delete the system default letterhead.")
            return

        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete '{filename}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            path = os.path.join(self.config.letterheads_dir, filename)
            try:
                os.remove(path)
                # Also try to remove original png if exists
                png_name = filename.replace('_png.html', '.png')
                png_path = os.path.join(self.config.letterheads_dir, png_name)
                if os.path.exists(png_path):
                    os.remove(png_path)
                    
                self.refresh_letterhead_list()
                QMessageBox.information(self, "Deleted", "Letterhead deleted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

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
            
            # Create HTML with embedded PNG (Using Inline Styles for Generator Compatibility)
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
    <div class="letterhead-container" style="text-align: center; padding-top: 0px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{png_data}" class="letterhead-img" style="max-width: 100%; width: 800px; height: auto; display: block; margin: 10px auto;" alt="Letterhead">
    </div>
    <div id="form-header-placeholder"></div>
</body>
</html>'''
            
            # Save PNG file (backup)
            png_dest = os.path.join(self.config.letterheads_dir, png_filename)
            shutil.copy2(file_path, png_dest)
            
            # Save HTML file
            html_filename = f"{base_name}_png.html"
            html_dest = os.path.join(self.config.letterheads_dir, html_filename)
            
            with open(html_dest, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            QMessageBox.information(self, "Success", "Letterhead uploaded successfully!")
            self.refresh_letterhead_list()
            
            # Auto-select/preview new file
            # find item... or just let refresh handle it
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload PNG letterhead: {e}")
    
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
        
    def create_data_management_tab(self):
        """Create the data management tab with Split View"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === TOP SECTION: Upload Controls (Fixed Height) ===
        top_container = QFrame()
        top_container.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #ddd;")
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header Row
        header_layout = QHBoxLayout()
        title = QLabel("📦 Data Import")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Reset Button (Compact)
        reset_btn = QPushButton("Reset DB")
        reset_btn.clicked.connect(self.reset_database)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #e74c3c; padding: 5px 10px; font-weight: bold; border: 1px solid #e74c3c; border-radius: 4px; }
            QPushButton:hover { background-color: #fae5e3; }
        """)
        header_layout.addWidget(reset_btn)
        
        # Import Button (Compact)
        import_btn = QPushButton("Run Import")
        import_btn.clicked.connect(self.import_taxpayers_bulk)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        header_layout.addWidget(import_btn)
        
        top_layout.addLayout(header_layout)
        
        # Inputs Row
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(20)
        
        # 1. Active
        self.active_file_input = FileUploaderWidget("Active Taxpayers")
        inputs_layout.addWidget(self.active_file_input)
        
        # 2. Suspended
        self.suspended_file_input = FileUploaderWidget("Suspended Taxpayers")
        inputs_layout.addWidget(self.suspended_file_input)
        
        # 3. Cancelled
        self.cancelled_file_input = FileUploaderWidget("Cancelled Taxpayers")
        inputs_layout.addWidget(self.cancelled_file_input)
        
        top_layout.addLayout(inputs_layout)
        
        # Progress & Status
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        self.import_progress.setFixedHeight(4)
        self.import_progress.setStyleSheet("QProgressBar { border: none; background: #e0e0e0; } QProgressBar::chunk { background-color: #27ae60; }")
        top_layout.addWidget(self.import_progress)
        
        self.import_status = QLabel("")
        self.import_status.setStyleSheet("font-size: 11px; margin-top: 5px;")
        self.import_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.import_status)
        
        layout.addWidget(top_container)
        
        # === BOTTOM SECTION: Taxpayer Table ===
        bottom_container = QFrame()
        bottom_container.setStyleSheet("background-color: white;")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        lbl_table = QLabel("Taxpayer Database")
        lbl_table.setStyleSheet("font-size: 14px; font-weight: bold; color: #7f8c8d; margin-bottom: 5px;")
        bottom_layout.addWidget(lbl_table)
        
        self.taxpayer_table = QTableWidget()
        self.taxpayer_table.setAlternatingRowColors(True)
        self.taxpayer_table.setShowGrid(False)
        self.taxpayer_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.taxpayer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.taxpayer_table.verticalHeader().setVisible(False)
        self.taxpayer_table.setStyleSheet("""
            QTableWidget { border: 1px solid #e0e0e0; border-radius: 4px; background-color: white; }
            QHeaderView::section { background-color: #f1f5f9; padding: 6px; border: none; font-weight: bold; color: #555; }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background-color: #e3f2fd; color: black; }
        """)
        
        columns = ["GSTIN", "Trade Name", "Legal Name", "Status", "Address", "Constitution"]
        self.taxpayer_table.setColumnCount(len(columns))
        self.taxpayer_table.setHorizontalHeaderLabels(columns)
        self.taxpayer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.taxpayer_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # GSTIN
        
        bottom_layout.addWidget(self.taxpayer_table)
        
        layout.addWidget(bottom_container)
        
        # Initial Load
        self.refresh_taxpayer_table()
        
        return widget

    def refresh_taxpayer_table(self):
        """Reload taxpayer data into the table"""
        taxpayers = self.db.get_all_taxpayers()
        self.taxpayer_table.setRowCount(0)
        
        # Status Colors
        status_colors = {
            'Active': '#d4edda',
            'Suspended': '#fff3cd',
            'Cancelled': '#f8d7da'
        }
        
        for row_idx, tp in enumerate(taxpayers):
            self.taxpayer_table.insertRow(row_idx)
            
            # Helper to create item
            def create_item(text):
                item = QTableWidgetItem(str(text))
                return item
                
            self.taxpayer_table.setItem(row_idx, 0, create_item(tp.get('GSTIN', '')))
            self.taxpayer_table.setItem(row_idx, 1, create_item(tp.get('Trade Name', '')))
            self.taxpayer_table.setItem(row_idx, 2, create_item(tp.get('Legal Name', '')))
            
            # Status badge-like item
            status = tp.get('Status', '')
            status_item = create_item(status)
            if status in status_colors:
                status_item.setBackground(QColor(status_colors[status])) # Need QColor import?
                # Actually, simple background is easier with setBackground or just let it be text for now
            self.taxpayer_table.setItem(row_idx, 3, status_item)
            
            self.taxpayer_table.setItem(row_idx, 4, create_item(tp.get('Address', '')))
            self.taxpayer_table.setItem(row_idx, 5, create_item(tp.get('Constitution', '')))

    # Removed browse_file as it is handled by FileUploaderWidget now (or used by other tabs? No, only Data Tab uses it)
    
    
    def reset_database(self):
        """Clear the taxpayer database"""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to delete ALL taxpayer data?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.db.reset_taxpayers_database()
            if success:
                QMessageBox.information(self, "Success", msg)
                self.import_status.setText("Database cleared.")
                self.refresh_taxpayer_table() # REFRESH TABLE
            else:
                QMessageBox.critical(self, "Error", msg)

    def import_taxpayers_bulk(self):
        """Import taxpayers from all inputs"""
        files_map = {
            'Active': self.active_file_input.text(),
            'Suspended': self.suspended_file_input.text(),
            'Cancelled': self.cancelled_file_input.text()
        }
        
        # Check if at least one file is selected
        if not any(files_map.values()):
            QMessageBox.warning(self, "No Files", "Please select at least one file to import.")
            return
            
        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "This will update the database with the selected files.\nExisting records for the same GSTIN will be overwritten.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # UI Update
        self.import_progress.setVisible(True)
        self.import_progress.setRange(0, 0) # Indeterminate
        self.import_status.setText("Importing data... Please wait.")
        self.import_status.setStyleSheet("color: blue; font-weight: bold;")
        
        # Process (Ideally in thread, but simple enough here)
        QApplication.processEvents() # Force UI update
        
        try:
            success, msg = self.db.import_taxpayers_bulk(files_map)
            
            self.import_progress.setVisible(False)
            if success:
                self.import_status.setText(msg)
                self.import_status.setStyleSheet("color: #27ae60; font-weight: bold;")
                QMessageBox.information(self, "Success", msg)
                
                # Clear inputs
                self.active_file_input.clear()
                self.suspended_file_input.clear()
                self.cancelled_file_input.clear()
                
                self.refresh_taxpayer_table() # REFRESH TABLE
            else:
                self.import_status.setText("Import Failed.")
                self.import_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
                QMessageBox.critical(self, "Error", msg)
                
        except Exception as e:
            self.import_progress.setVisible(False)
            self.import_status.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Critical Error", str(e))
    
    def save_general_settings(self):
        """Save general settings"""
        self.config.set_setting('office_name', self.office_input.text())
        self.config.set_setting('jurisdiction', self.jurisdiction_input.text())
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
