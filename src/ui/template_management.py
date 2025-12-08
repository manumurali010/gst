from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QTextEdit, QMessageBox, QInputDialog, QComboBox,
                             QStackedWidget, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from src.database.db_manager import DatabaseManager
from src.utils.preview_generator import PreviewGenerator
from src.ui.styles import Theme
from src.utils.config_manager import ConfigManager
import os
import re

class TemplateManagement(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.db = DatabaseManager()
        self.db.init_sqlite()
        self.current_template_id = None
        
        self.init_ui()
        self.load_letterheads()
        self.load_templates()
        
    def load_letterheads(self):
        self.lh_combo.blockSignals(True)
        self.lh_combo.clear()
        
        config = ConfigManager()
        letterheads = config.get_available_letterheads()
        current_lh = config.get_pdf_letterhead()
        
        # Filter for HTML only
        html_lhs = [lh for lh in letterheads if lh.endswith('.html')]
        
        for lh in html_lhs:
            self.lh_combo.addItem(lh, lh)
            
        # Select current
        index = self.lh_combo.findData(current_lh)
        if index >= 0:
            self.lh_combo.setCurrentIndex(index)
            
        self.lh_combo.blockSignals(False)

    def on_letterhead_changed(self):
        lh_name = self.lh_combo.currentData()
        if lh_name:
            # Update global config
            config = ConfigManager()
            config.set_pdf_letterhead(lh_name)
            
            # Regenerate preview if a template is selected
            if self.current_template_id:
                template = self.db.get_template(self.current_template_id)
                if template:
                    self.generate_preview(template['content'])
        
    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Sidebar ---
        sidebar_layout = QVBoxLayout()
        
        sidebar_label = QLabel("Templates")
        sidebar_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Theme.PRIMARY};")
        sidebar_layout.addWidget(sidebar_label)
        
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.on_template_selected)
        sidebar_layout.addWidget(self.template_list)
        
        new_btn = QPushButton("+ New Template")
        new_btn.clicked.connect(self.create_new_template)
        sidebar_layout.addWidget(new_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet(f"background-color: {Theme.DANGER}; color: white;")
        delete_btn.clicked.connect(self.delete_template)
        sidebar_layout.addWidget(delete_btn)
        
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(250)
        self.layout.addWidget(sidebar_widget)
        
        # --- Main Area (Stacked: View vs Edit) ---
        self.main_stack = QStackedWidget()
        
        # 1. View Mode (Index 0)
        self.view_widget = QWidget()
        self.setup_view_mode()
        self.main_stack.addWidget(self.view_widget)
        
        # 2. Edit Mode (Index 1)
        self.edit_widget = QWidget()
        self.setup_edit_mode()
        self.main_stack.addWidget(self.edit_widget)
        
        self.layout.addWidget(self.main_stack)
        
    def setup_view_mode(self):
        layout = QVBoxLayout(self.view_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        self.view_title = QLabel("Select a template")
        self.view_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {Theme.PRIMARY};")
        header_layout.addWidget(self.view_title)
        
        header_layout.addStretch()
        
        # Letterhead Selector
        lh_layout = QHBoxLayout()
        lh_layout.setSpacing(5)
        lh_label = QLabel("Letterhead:")
        lh_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-weight: bold;")
        lh_layout.addWidget(lh_label)
        
        self.lh_combo = QComboBox()
        self.lh_combo.setMinimumWidth(200)
        self.lh_combo.currentIndexChanged.connect(self.on_letterhead_changed)
        lh_layout.addWidget(self.lh_combo)
        
        header_layout.addLayout(lh_layout)
        header_layout.addSpacing(20)
        
        self.edit_btn = QPushButton("Edit Template")
        self.edit_btn.setStyleSheet(f"background-color: {Theme.SECONDARY}; color: white; font-weight: bold; padding: 8px 16px;")
        self.edit_btn.clicked.connect(self.switch_to_edit_mode)
        self.edit_btn.setEnabled(False)
        header_layout.addWidget(self.edit_btn)
        
        layout.addLayout(header_layout)
        
        # Preview Area
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("background-color: #525659; border: 1px solid #ccc;")
        
        # Container for pages
        self.preview_container = QWidget()
        self.preview_container.setStyleSheet("background-color: #525659;")
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.preview_layout.setSpacing(20)
        self.preview_layout.setContentsMargins(20, 20, 20, 20)
        
        self.preview_scroll.setWidget(self.preview_container)
        
        layout.addWidget(self.preview_scroll)
        
    def setup_edit_mode(self):
        layout = QVBoxLayout(self.edit_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Edit Template")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {Theme.PRIMARY};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"background-color: {Theme.DANGER}; color: white; padding: 6px 12px;")
        cancel_btn.clicked.connect(self.cancel_edit)
        header_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"background-color: {Theme.SUCCESS}; color: white; font-weight: bold; padding: 6px 12px;")
        save_btn.clicked.connect(self.save_current_template)
        header_layout.addWidget(save_btn)
        
        layout.addLayout(header_layout)
        
        # Metadata
        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["DRC-01A", "DRC-01", "SCN", "Order", "PH", "Other"])
        meta_layout.addWidget(self.type_combo)
        
        meta_layout.addWidget(QLabel("Name:"))
        self.name_edit = QTextEdit() 
        # For now, keeping name fixed or editable via dialog. Let's just allow Type editing here.
        
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        # Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("HTML Content...")
        layout.addWidget(self.editor)

    def load_templates(self):
        self.template_list.clear()
        templates = self.db.get_all_templates()
        for t in templates:
            self.template_list.addItem(f"{t['name']} ({t['type']})")
            item = self.template_list.item(self.template_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, t['id'])

    def on_template_selected(self, current, previous):
        if not current:
            return
            
        template_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_template_id = template_id
        
        # Load data
        template = self.db.get_template(template_id)
        if template:
            # Update View Mode
            self.view_title.setText(template['name'])
            self.edit_btn.setEnabled(True)
            self.generate_preview(template['content'])
            
            # Update Edit Mode (pre-fill)
            self.editor.setPlainText(template['content'])
            self.type_combo.setCurrentText(template['type'])
            
            # Ensure we are in View Mode
            self.main_stack.setCurrentIndex(0)

    def generate_preview(self, html_content):
        if not html_content:
            # Clear preview
            while self.preview_layout.count():
                child = self.preview_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            return
            
        # --- Letterhead Injection ---
        try:
            config = ConfigManager()
            lh_name = config.get_pdf_letterhead()
            if lh_name:
                lh_path = os.path.join(config.letterheads_dir, lh_name)
                if os.path.exists(lh_path):
                    with open(lh_path, 'r', encoding='utf-8') as f:
                        lh_content = f.read()
                        
                    # Extract body content if it's a full HTML file
                    if "<body>" in lh_content:
                        match = re.search(r"<body[^>]*>(.*?)</body>", lh_content, re.DOTALL | re.IGNORECASE)
                        if match:
                            lh_content = match.group(1)
                            
                    # Replace placeholders
                    # Handle both <letter head> and encoded &lt;letter head&gt;
                    html_content = html_content.replace("<letter head>", lh_content)
                    html_content = html_content.replace("&lt;letter head&gt;", lh_content)
        except Exception as e:
            print(f"Letterhead Injection Error: {e}")

        # --- Generate Preview ---
        # Pass all_pages=True to get list of images
        img_bytes_list = PreviewGenerator.generate_preview_image(html_content, all_pages=True)
        
        # Clear existing preview
        while self.preview_layout.count():
            child = self.preview_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if img_bytes_list:
            for img_bytes in img_bytes_list:
                pixmap = PreviewGenerator.get_qpixmap_from_bytes(img_bytes)
                if pixmap:
                    label = QLabel()
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    label.setStyleSheet("background-color: white; margin-bottom: 20px; border: 1px solid #ddd;")
                    
                    # Scale to fit width
                    width = self.preview_scroll.width() - 60 # Margin for scrollbar and padding
                    if width > 0:
                        scaled_pixmap = pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
                        label.setPixmap(scaled_pixmap)
                    else:
                        label.setPixmap(pixmap)
                        
                    self.preview_layout.addWidget(label)
        else:
            error_label = QLabel("Preview Generation Failed")
            error_label.setStyleSheet("color: white; font-size: 16px;")
            self.preview_layout.addWidget(error_label)

    def switch_to_edit_mode(self):
        self.main_stack.setCurrentIndex(1)

    def cancel_edit(self):
        # Revert changes by reloading from DB (or just switching back if we trust on_select)
        # Better to reload to be safe
        if self.current_template_id:
            template = self.db.get_template(self.current_template_id)
            if template:
                self.editor.setPlainText(template['content'])
                self.type_combo.setCurrentText(template['type'])
        self.main_stack.setCurrentIndex(0)

    def save_current_template(self):
        if not self.current_template_id:
            return
            
        content = self.editor.toPlainText()
        type_val = self.type_combo.currentText()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE templates SET content = ?, type = ? WHERE id = ?", 
                               (content, type_val, self.current_template_id))
                conn.commit()
            
            QMessageBox.information(self, "Success", "Template saved successfully!")
            
            # Refresh View Mode
            self.generate_preview(content)
            self.main_stack.setCurrentIndex(0)
            
            # Refresh List (in case type changed)
            # Need to preserve selection
            current_row = self.template_list.currentRow()
            self.load_templates()
            self.template_list.setCurrentRow(current_row)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def create_new_template(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template Name:")
        if ok and name:
            data = {
                "name": name,
                "type": "Other",
                "content": "<html><body><p>New Template</p></body></html>",
                "description": ""
            }
            self.db.save_template(data)
            self.load_templates()
            # Select new
            self.template_list.setCurrentRow(self.template_list.count() - 1)

    def delete_template(self):
        if not self.current_template_id:
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this template?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_template(self.current_template_id)
            self.load_templates()
            self.current_template_id = None
            self.view_title.setText("Select a template")
            # Clear preview
            while self.preview_layout.count():
                child = self.preview_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.edit_btn.setEnabled(False)
            self.main_stack.setCurrentIndex(0)
