from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QSplitter, QLineEdit, QComboBox, QTabWidget, 
                             QMessageBox, QFormLayout, QCheckBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QPlainTextEdit, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import uuid
from src.database.db_manager import DatabaseManager
from src.ui.rich_text_editor import RichTextEditor
from src.ui.rich_text_editor import RichTextEditor
from src.ui.developer.table_builder import TableBuilderWidget

class IssueManager(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_issue_id = None
        self.init_ui()
        self.load_issue_list()

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        
        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # Left Pane: Issue List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_header = QLabel("Issues Repository")
        left_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(left_header)
        
        self.issue_list = QListWidget()
        self.issue_list.currentRowChanged.connect(self.on_issue_selected)
        left_layout.addWidget(self.issue_list)
        
        new_btn = QPushButton("+ Create New Issue")
        new_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px;")
        new_btn.clicked.connect(self.create_new_issue)
        left_layout.addWidget(new_btn)
        
        self.splitter.addWidget(left_widget)
        
        # Right Pane: Editor
        self.editor_container = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_container)
        
        # Editor Header
        header_layout = QHBoxLayout()
        self.editor_title = QLabel("Edit Issue")
        self.editor_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.editor_title)
        
        header_layout.addStretch()
        
        self.active_cb = QCheckBox("Active / Published")
        header_layout.addWidget(self.active_cb)
        
        save_btn = QPushButton("Save Issue")
        save_btn.setStyleSheet("background-color: #3498db; color: white; padding: 5px 15px;")
        save_btn.clicked.connect(self.save_issue)
        header_layout.addWidget(save_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px 15px;")
        delete_btn.clicked.connect(self.delete_issue)
        header_layout.addWidget(delete_btn)
        
        self.editor_layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.editor_layout.addWidget(self.tabs)
        
        # 1. Metadata Tab
        self.metadata_tab = QWidget()
        self.init_metadata_tab()
        self.tabs.addTab(self.metadata_tab, "Metadata")
        
        # 2. Templates Tab
        self.templates_tab = QWidget()
        self.init_templates_tab()
        self.tabs.addTab(self.templates_tab, "Templates")
        
        # 3. Tables Tab
        self.tables_tab = QWidget()
        self.init_tables_tab()
        self.tabs.addTab(self.tables_tab, "Tables")
        
        # 4. Placeholders Tab
        self.placeholders_tab = QWidget()
        self.init_placeholders_tab()
        self.tabs.addTab(self.placeholders_tab, "Placeholders")
        
        # 5. Logic Tab REMOVED as per user request
        # self.logic_tab = QWidget()
        # self.init_logic_tab()
        # self.tabs.addTab(self.logic_tab, "Calculation Logic")
        
        # 6. Preview Tab
        self.preview_tab = QWidget()
        self.init_preview_tab()
        self.tabs.addTab(self.preview_tab, "Preview")
        
        self.splitter.addWidget(self.editor_container)
        self.splitter.setSizes([250, 750])
        
        # Initially disable editor until issue selected
        self.editor_container.setEnabled(False)

    def init_metadata_tab(self):
        layout = QFormLayout(self.metadata_tab)
        layout.setSpacing(15)
        
        self.issue_id_input = QLineEdit()
        self.issue_id_input.setReadOnly(True)
        self.issue_id_input.setPlaceholderText("Auto-generated ID")
        layout.addRow("Issue ID:", self.issue_id_input)
        
        self.issue_name_input = QLineEdit()
        layout.addRow("Issue Name:", self.issue_name_input)
        
        self.category_input = QComboBox()
        self.category_input.addItems(["Outward Liability", "ITC Mismatch", "RCM", "Ineligible ITC", "Other"])
        self.category_input.setEditable(True)
        layout.addRow("Category:", self.category_input)
        
        self.severity_input = QComboBox()
        self.severity_input.addItems(["High", "Medium", "Low"])
        layout.addRow("Severity:", self.severity_input)
        
        self.version_input = QLineEdit("1.0")
        layout.addRow("Version:", self.version_input)
        
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma separated tags (e.g. gstr1, gstr3b)")
        layout.addRow("Tags:", self.tags_input)

    def init_templates_tab(self):
        layout = QVBoxLayout(self.templates_tab)
        
        # Sub-tabs for each template section
        self.template_subtabs = QTabWidget()
        
        self.brief_facts_editor = RichTextEditor("Brief Facts...")
        self.template_subtabs.addTab(self.brief_facts_editor, "Brief Facts")
        
        self.grounds_editor = RichTextEditor("Grounds...")
        self.template_subtabs.addTab(self.grounds_editor, "Grounds")
        
        self.legal_editor = RichTextEditor("Legal Provisions...")
        self.template_subtabs.addTab(self.legal_editor, "Legal")
        
        self.conclusion_editor = RichTextEditor("Conclusion...")
        self.template_subtabs.addTab(self.conclusion_editor, "Conclusion")
        
        layout.addWidget(self.template_subtabs)
        
        help_lbl = QLabel("Tip: Use {{placeholder_name}} to insert dynamic values.")
        help_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_lbl)

    def init_tables_tab(self):
        layout = QVBoxLayout(self.tables_tab)
        
        # For now, support single table configuration as per schema (list of tables, but UI needs to handle it)
        # Let's assume 1 main table for simplicity in V1, or a list of tables.
        # Schema says "tables": [ ... ]
        
        self.table_builder = TableBuilderWidget()
        layout.addWidget(QLabel("Table Design & Logic:"))
        layout.addWidget(self.table_builder)

    def init_placeholders_tab(self):
        layout = QVBoxLayout(self.placeholders_tab)
        
        self.placeholders_table = QTableWidget()
        self.placeholders_table.setColumnCount(4)
        self.placeholders_table.setHorizontalHeaderLabels(["Name", "Type", "Required", "Computed"])
        self.placeholders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.placeholders_table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Placeholder")
        add_btn.clicked.connect(self.add_placeholder_row)
        btn_layout.addWidget(add_btn)
        
        detect_btn = QPushButton("Auto-Detect from Templates")
        detect_btn.clicked.connect(self.detect_placeholders)
        btn_layout.addWidget(detect_btn)
        
        layout.addLayout(btn_layout)

    def init_logic_tab(self):
        layout = QVBoxLayout(self.logic_tab)
        
        self.logic_editor = QPlainTextEdit()
        self.logic_editor.setPlaceholderText("def compute(v):\n    return {}")
        self.logic_editor.setFont(QFont("Consolas", 10))
        layout.addWidget(QLabel("Calculation Logic (Python):"))
        layout.addWidget(self.logic_editor)
        
        # Test Section
        test_layout = QHBoxLayout()
        self.test_input_editor = QPlainTextEdit()
        self.test_input_editor.setPlaceholderText("Test Input JSON:\n{\n  'val1': 100\n}")
        self.test_input_editor.setMaximumHeight(100)
        
        self.test_output_lbl = QLabel("Result will appear here...")
        self.test_output_lbl.setWordWrap(True)
        self.test_output_lbl.setStyleSheet("border: 1px solid #ccc; padding: 5px;")
        
        test_layout.addWidget(self.test_input_editor, 1)
        test_layout.addWidget(self.test_output_lbl, 1)
        
        layout.addLayout(test_layout)
        
        test_btn = QPushButton("Test Run Logic")
        test_btn.clicked.connect(self.test_logic)
        layout.addWidget(test_btn)

    def init_preview_tab(self):
        layout = QVBoxLayout(self.preview_tab)
        
        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.clicked.connect(self.refresh_preview)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Scroll Area for Preview
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preview_content = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_content)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.preview_content)
        
        layout.addWidget(scroll)

    def refresh_preview(self):
        # Clear previous
        for i in reversed(range(self.preview_layout.count())): 
            self.preview_layout.itemAt(i).widget().setParent(None)
            
        # Gather current data (simulate save)
        data = {
            "issue_id": self.current_issue_id or "preview_id",
            "issue_name": self.issue_name_input.text() or "Preview Issue",
            "templates": {
                "brief_facts": self.brief_facts_editor.toHtml(),
                "grounds": self.grounds_editor.toHtml(),
                "legal": self.legal_editor.toHtml(),
                "conclusion": self.conclusion_editor.toHtml()
            },
            "tables": self.table_builder.get_data(),
            "placeholders": []
        }
        
        # Placeholders
        for row in range(self.placeholders_table.rowCount()):
            name = self.placeholders_table.item(row, 0).text()
            if not name: continue
            p_type = self.placeholders_table.item(row, 1).text()
            req = self.placeholders_table.cellWidget(row, 2).isChecked()
            comp = self.placeholders_table.cellWidget(row, 3).isChecked()
            data["placeholders"].append({
                "name": name, "type": p_type, "required": req, "computed": comp
            })
            
        # Create IssueCard
        from src.ui.issue_card import IssueCard
        try:
            card = IssueCard(data)
            self.preview_layout.addWidget(card)
        except Exception as e:
            self.preview_layout.addWidget(QLabel(f"Error generating preview: {e}"))

    # ---------------- Actions ----------------

    def load_issue_list(self):
        self.issue_list.clear()
        issues = self.db.get_all_issues_metadata()
        for issue in issues:
            item_text = f"{issue['issue_name']} ({issue['issue_id']})"
            self.issue_list.addItem(item_text)
            # Store ID in item data? No, just use index or lookup. 
            # Better to store ID.
            item = self.issue_list.item(self.issue_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, issue['issue_id'])

    def create_new_issue(self):
        self.current_issue_id = str(uuid.uuid4())
        self.issue_id_input.setText(self.current_issue_id)
        self.issue_name_input.clear()
        self.category_input.setCurrentIndex(0)
        self.severity_input.setCurrentIndex(0)
        self.version_input.setText("1.0")
        self.tags_input.clear()
        self.active_cb.setChecked(False)
        
        # Clear Editors
        self.brief_facts_editor.setHtml("")
        self.grounds_editor.setHtml("")
        self.legal_editor.setHtml("")
        self.conclusion_editor.setHtml("")
        self.table_builder.set_data({})
        # self.logic_editor.setPlainText(LogicValidator.get_default_logic_template()) # Logic removed
        self.placeholders_table.setRowCount(0)
        
        self.editor_container.setEnabled(True)
        self.editor_title.setText("Create New Issue")

    def on_issue_selected(self, row):
        item = self.issue_list.item(row)
        if not item: return
        issue_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_issue(issue_id)

    def load_issue(self, issue_id):
        issue = self.db.get_issue(issue_id)
        if not issue:
            return
            
        self.current_issue_id = issue_id
        self.editor_container.setEnabled(True)
        self.editor_title.setText(f"Edit Issue: {issue.get('issue_name')}")
        
        # Populate Metadata
        self.issue_id_input.setText(issue_id)
        self.issue_name_input.setText(issue.get('issue_name', ''))
        self.category_input.setCurrentText(issue.get('category', ''))
        self.severity_input.setCurrentText(issue.get('severity', ''))
        self.version_input.setText(issue.get('version', '1.0'))
        self.tags_input.setText(", ".join(issue.get('tags', [])))
        
        # Active status is in master, but we loaded full JSON. 
        # Wait, get_issue returns JSON from issues_data. 
        # We need to check active status from master or if we stored it in JSON too.
        # My save_issue stores active in master only. 
        # Let's fetch metadata again or assume we passed it.
        # For now, let's default to unchecked and maybe fix get_issue to include active status if needed.
        # Actually, let's just fetch metadata for active status.
        meta = [m for m in self.db.get_all_issues_metadata() if m['issue_id'] == issue_id]
        if meta:
            self.active_cb.setChecked(bool(meta[0]['active']))
        
        # Populate Templates
        templates = issue.get('templates', {})
        self.brief_facts_editor.setHtml(templates.get('brief_facts', ''))
        self.grounds_editor.setHtml(templates.get('grounds', ''))
        self.legal_editor.setHtml(templates.get('legal', ''))
        self.conclusion_editor.setHtml(templates.get('conclusion', ''))
        
        # Populate Tables
        # Populate Tables
        self.table_builder.set_data(issue.get('tables', {}))
        
        # Populate Logic (Removed)
        # self.logic_editor.setPlainText(issue.get('calc_logic', ''))
        
        # Populate Placeholders
        self.placeholders_table.setRowCount(0)
        for p in issue.get('placeholders', []):
            self.add_placeholder_row(p)

    def add_placeholder_row(self, data=None):
        row = self.placeholders_table.rowCount()
        self.placeholders_table.insertRow(row)
        
        if not data: data = {}
        
        self.placeholders_table.setItem(row, 0, QTableWidgetItem(data.get('name', '')))
        self.placeholders_table.setItem(row, 1, QTableWidgetItem(data.get('type', 'string')))
        
        req_cb = QCheckBox()
        req_cb.setChecked(data.get('required', False))
        self.placeholders_table.setCellWidget(row, 2, req_cb)
        
        comp_cb = QCheckBox()
        comp_cb.setChecked(data.get('computed', False))
        self.placeholders_table.setCellWidget(row, 3, comp_cb)

    def detect_placeholders(self):
        import re
        text = (self.brief_facts_editor.toHtml() + self.grounds_editor.toHtml() + 
                self.legal_editor.toHtml() + self.conclusion_editor.toHtml())
        
        matches = set(re.findall(r'\{\{([^}]+)\}\}', text))
        
        current_names = []
        for row in range(self.placeholders_table.rowCount()):
            item = self.placeholders_table.item(row, 0)
            if item: current_names.append(item.text())
            
        for match in matches:
            if match not in current_names:
                self.add_placeholder_row({'name': match, 'type': 'string'})
                
        QMessageBox.information(self, "Detection Complete", f"Found {len(matches)} placeholders.")

    def test_logic(self):
        code = self.logic_editor.toPlainText()
        try:
            inputs = json.loads(self.test_input_editor.toPlainText() or "{}")
        except:
            self.test_output_lbl.setText("Error: Invalid JSON Input")
            return
            
        valid, result = LogicValidator.validate_logic(code, inputs)
        if valid:
            self.test_output_lbl.setText(f"Success:\n{json.dumps(result, indent=2)}")
            self.test_output_lbl.setStyleSheet("border: 1px solid green; padding: 5px;")
        else:
            self.test_output_lbl.setText(f"Failed:\n{result}")
            self.test_output_lbl.setStyleSheet("border: 1px solid red; padding: 5px;")

    def save_issue(self):
        if not self.current_issue_id:
            return
            
        # Collect Data
        data = {
            "issue_id": self.current_issue_id,
            "issue_name": self.issue_name_input.text(),
            "category": self.category_input.currentText(),
            "severity": self.severity_input.currentText(),
            "version": self.version_input.text(),
            "tags": [t.strip() for t in self.tags_input.text().split(',') if t.strip()],
            
            "templates": {
                "brief_facts": self.brief_facts_editor.toHtml(),
                "grounds": self.grounds_editor.toHtml(),
                "legal": self.legal_editor.toHtml(),
                "conclusion": self.conclusion_editor.toHtml()
            },
            
            # "calc_logic": self.logic_editor.toPlainText(), # Removed
            "active": self.active_cb.isChecked()
        }
        
        # Tables
        # Tables
        data["tables"] = self.table_builder.get_data()
            
        # Placeholders
        placeholders = []
        for row in range(self.placeholders_table.rowCount()):
            name = self.placeholders_table.item(row, 0).text()
            if not name: continue
            
            p_type = self.placeholders_table.item(row, 1).text()
            req = self.placeholders_table.cellWidget(row, 2).isChecked()
            comp = self.placeholders_table.cellWidget(row, 3).isChecked()
            
            placeholders.append({
                "name": name, "type": p_type, "required": req, "computed": comp
            })
        data["placeholders"] = placeholders
        
        # Save
        success, msg = self.db.save_issue(data)
        if success:
            # Update active status
            self.db.publish_issue(self.current_issue_id, self.active_cb.isChecked())
            
            QMessageBox.information(self, "Success", "Issue saved successfully!")
            self.load_issue_list()
        else:
            QMessageBox.critical(self, "Error", f"Failed to save: {msg}")

    def delete_issue(self):
        if not self.current_issue_id: return
        
        confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this issue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_issue(self.current_issue_id)
            self.load_issue_list()
            self.create_new_issue() # Reset
