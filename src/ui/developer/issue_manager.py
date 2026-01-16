from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QSplitter, QLineEdit, QComboBox, QTabWidget, 
                             QMessageBox, QFormLayout, QCheckBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QPlainTextEdit, QFrame, QScrollArea, QListWidgetItem,
                             QButtonGroup)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QIcon
import json
import uuid
from src.database.db_manager import DatabaseManager
from src.ui.rich_text_editor import RichTextEditor
from src.ui.developer.table_builder import TableBuilderWidget
from src.ui.components.section_selector import SectionSelectorDialog
from src.ui.developer.logic_validator import LogicValidator

class IssueListItemWidget(QFrame):
    """Rich List Item for Issues (Card Style)"""
    def __init__(self, name, issue_id, active, category):
        super().__init__()
        self.active = active
        
        # styling for the card itself
        self.setStyleSheet(f"""
            IssueListItemWidget {{
                background-color: white;
                border-left: 4px solid {'#27ae60' if active else '#95a5a6'};
                border-bottom: 1px solid #f1f2f6;
            }}
            IssueListItemWidget:hover {{
                background-color: #f8f9fa;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Row 1: Name
        row1 = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #2c3e50;")
        name_lbl.setWordWrap(False)
        row1.addWidget(name_lbl)
        layout.addLayout(row1)
        
        # Row 2: Category & ID
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        cat_lbl = QLabel((category or "OTHER").upper()) # Uppercase for pill style
        cat_lbl.setStyleSheet("""
            background-color: #eef2f7; 
            color: #576574; 
            border-radius: 4px; 
            padding: 2px 6px; 
            font-size: 9px; 
            font-weight: bold;
        """)
        row2.addWidget(cat_lbl)
        
        row2.addStretch()
        
        layout.addLayout(row2)



class IssueManager(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_issue_id = None
        self.all_issues = [] # Cache
        self.init_ui()
        self.load_issue_list()

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")
        self.layout.addWidget(self.splitter)
        
        # ---------------- Left Pane: Explorer ----------------
        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #ffffff;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 1. Header Area
        header_container = QWidget()
        header_container.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #e0e0e0;")
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(10)
        
        top_row = QHBoxLayout()
        title = QLabel("Issue Explorer")
        title.setStyleSheet("font-size: 12px; font-weight: 800; color: #5f6c7b; text-transform: uppercase; letter-spacing: 0.5px;")
        top_row.addWidget(title)
        top_row.addStretch()
        # Counts could go here
        header_layout.addLayout(top_row)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter issues...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px; 
                border: 1px solid #dcdde1; 
                border-radius: 4px;
                background: white;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #3498db; }
        """)
        self.search_input.textChanged.connect(self.filter_issues)
        header_layout.addWidget(self.search_input)
        
        left_layout.addWidget(header_container)
        
        # 2. List Widget
        self.issue_list = QListWidget()
        self.issue_list.setFrameShape(QFrame.Shape.NoFrame)
        # We rely on widget styling now, so list item styling is minimal
        self.issue_list.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                outline: none;
            }
            QListWidget::item {
                padding: 0px; 
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: white; /* Widget handles selection look if needed, or we assume transparent overlay */
            }
        """)
        # Important: Remove focus rect
        self.issue_list.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.issue_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.issue_list.currentRowChanged.connect(self.on_issue_selected)
        left_layout.addWidget(self.issue_list)
        
        # 3. Bottom Toolbar
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color: #f8f9fa; border-top: 1px solid #e0e0e0; padding: 10px;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        new_btn = QPushButton("Create Issue")
        # new_btn.setIcon(QIcon("assets/icons/plus.png")) # Fallback if no icon system, text is fine
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; 
                color: #27ae60; 
                border: 1px solid #27ae60; 
                padding: 6px 12px; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #27ae60;
                color: white;
            }
        """)
        new_btn.clicked.connect(self.create_new_issue)
        bottom_layout.addWidget(new_btn)
        
        left_layout.addWidget(bottom_bar)
        
        self.splitter.addWidget(left_widget)
        
        # ---------------- Right Pane: Editor ----------------
        self.editor_container = QWidget()
        self.editor_container.setStyleSheet("background-color: #fff;")
        self.editor_layout = QVBoxLayout(self.editor_container)
        
        # Editor Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("border-bottom: 1px solid #eee; padding: 10px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor_title = QLabel("Edit Issue")
        self.editor_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        tb_layout.addWidget(self.editor_title)
        
        tb_layout.addStretch()
        
        self.active_cb = QCheckBox("Active / Published")
        tb_layout.addWidget(self.active_cb)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("background-color: #3498db; color: white; padding: 6px 15px; border: none; border-radius: 4px;")
        save_btn.clicked.connect(self.save_issue)
        tb_layout.addWidget(save_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 6px 15px; border: none; border-radius: 4px;")
        delete_btn.clicked.connect(self.delete_issue)
        tb_layout.addWidget(delete_btn)
        
        self.editor_layout.addWidget(toolbar)
        
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
        
        # 5. Preview Tab
        self.preview_tab = QWidget()
        self.init_preview_tab()
        self.tabs.addTab(self.preview_tab, "Preview")
        
        self.splitter.addWidget(self.editor_container)
        self.splitter.setSizes([300, 900]) # 300px sidebar
        
        # Initially disable editor until issue selected
        self.editor_container.setEnabled(False)

    def init_metadata_tab(self):
        layout = QFormLayout(self.metadata_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.issue_id_input = QLineEdit()
        self.issue_id_input.setReadOnly(True)
        self.issue_id_input.setStyleSheet("background-color: #f0f0f0; color: #555;")
        layout.addRow("Issue ID:", self.issue_id_input)
        
        self.issue_name_input = QLineEdit()
        layout.addRow("Issue Name:", self.issue_name_input)
        
        self.category_input = QComboBox()
        self.category_input.addItems(["Scrutiny Summary", "Tax Liability", "ITC Mismatch", "RCM", "Exports", "Ineligible ITC", "Other"])
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
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Sub-tabs for each template section
        self.template_subtabs = QTabWidget()
        self.template_subtabs.setStyleSheet("QTabBar::tab { min-width: 120px; }")
        
        # --- 1. Brief Facts (Sub-tabbed) ---
        brief_facts_container = QWidget()
        brief_facts_layout = QVBoxLayout(brief_facts_container)
        brief_facts_layout.setContentsMargins(0, 0, 0, 0)
        
        self.brief_facts_subtabs = QTabWidget()
        self.brief_facts_subtabs.setTabPosition(QTabWidget.TabPosition.North)
        
        self.brief_facts_drc_editor = RichTextEditor("Brief Facts for DRC-01A / ASMT-10...")
        self.brief_facts_subtabs.addTab(self.brief_facts_drc_editor, "DRC-01A / ASMT-10")
        
        self.brief_facts_scn_editor = RichTextEditor("Brief Facts / Specific Facts for SCN...")
        self.brief_facts_subtabs.addTab(self.brief_facts_scn_editor, "SCN")
        
        brief_facts_layout.addWidget(self.brief_facts_subtabs)
        self.template_subtabs.addTab(brief_facts_container, "Brief Facts")
        
        # --- 2. Grounds (Optional) ---
        grounds_container = QWidget()
        grounds_layout = QVBoxLayout(grounds_container)
        grounds_layout.setContentsMargins(0, 0, 0, 0)
        
        grounds_header = QFrame()
        grounds_header.setStyleSheet("background: #f8f9fa; border-bottom: 1px solid #ddd;")
        gh_layout = QHBoxLayout(grounds_header)
        self.include_grounds_cb = QCheckBox("Include Grounds in document")
        self.include_grounds_cb.setChecked(True)
        gh_layout.addWidget(self.include_grounds_cb)
        gh_layout.addStretch()
        grounds_layout.addWidget(grounds_header)
        
        self.grounds_editor = RichTextEditor("Grounds...")
        grounds_layout.addWidget(self.grounds_editor)
        self.template_subtabs.addTab(grounds_container, "Grounds")
        
        # --- 3. Legal Tab (Always included if content exists) ---
        legal_widget = QWidget()
        legal_layout = QVBoxLayout(legal_widget)
        legal_layout.setContentsMargins(0, 0, 0, 0)
        
        legal_toolbar = QHBoxLayout()
        legal_toolbar.addStretch()
        insert_legal_btn = QPushButton("Insert CGST Sections")
        insert_legal_btn.setStyleSheet("background-color: #9b59b6; color: white;")
        insert_legal_btn.clicked.connect(self.open_section_selector)
        legal_toolbar.addWidget(insert_legal_btn)
        legal_layout.addLayout(legal_toolbar)
        
        self.legal_editor = RichTextEditor("Legal Provisions...")
        legal_layout.addWidget(self.legal_editor)
        self.template_subtabs.addTab(legal_widget, "Legal")
        
        # --- 4. Conclusion (Optional) ---
        conclusion_container = QWidget()
        conclusion_layout = QVBoxLayout(conclusion_container)
        conclusion_layout.setContentsMargins(0, 0, 0, 0)
        
        conclusion_header = QFrame()
        conclusion_header.setStyleSheet("background: #f8f9fa; border-bottom: 1px solid #ddd;")
        ch_layout = QHBoxLayout(conclusion_header)
        self.include_conclusion_cb = QCheckBox("Include Conclusion in document")
        self.include_conclusion_cb.setChecked(True)
        ch_layout.addWidget(self.include_conclusion_cb)
        ch_layout.addStretch()
        conclusion_layout.addWidget(conclusion_header)
        
        self.conclusion_editor = RichTextEditor("Conclusion...")
        conclusion_layout.addWidget(self.conclusion_editor)
        self.template_subtabs.addTab(conclusion_container, "Conclusion")
        
        layout.addWidget(self.template_subtabs)
        
        help_lbl = QLabel("Tip: Use {{variable_name}} to insert dynamic values like {{total_shortfall}} or {{period}}.")
        help_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_lbl)

    def open_section_selector(self):
        dialog = SectionSelectorDialog(self)
        if dialog.exec():
            selected = dialog.get_selected_sections()
            if selected:
                html_fragments = []
                for item in selected:
                    title = item.get('title', '')
                    content = item.get('content', '')
                    fragment = f"<b>{title}</b><br>{content}<br><br>"
                    html_fragments.append(fragment)

                final_html = "".join(html_fragments)
                self.legal_editor.insertHtml(final_html)

    def init_tables_tab(self):
        layout = QVBoxLayout(self.tables_tab)
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

    def init_preview_tab(self):
        layout = QVBoxLayout(self.preview_tab)
        
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.clicked.connect(self.refresh_preview)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preview_content = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_content)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.preview_content)
        
        layout.addWidget(scroll)

    def refresh_preview(self):
        for i in reversed(range(self.preview_layout.count())): 
            self.preview_layout.itemAt(i).widget().setParent(None)
            
        data = {
            "issue_id": self.current_issue_id or "preview",
            "issue_name": self.issue_name_input.text() or "Preview Issue",
            "templates": {
                "brief_facts": self.brief_facts_drc_editor.toHtml(),
                "brief_facts_scn": self.brief_facts_scn_editor.toHtml(),
                "include_grounds": self.include_grounds_cb.isChecked(),
                "grounds": self.grounds_editor.toHtml(),
                "legal": self.legal_editor.toHtml(),
                "include_conclusion": self.include_conclusion_cb.isChecked(),
                "conclusion": self.conclusion_editor.toHtml()
            },
            "tables": self.table_builder.get_data(),
            "placeholders": []
        }
        
        from src.ui.issue_card import IssueCard
        try:
            card = IssueCard(data)
            self.preview_layout.addWidget(card)
        except Exception as e:
            self.preview_layout.addWidget(QLabel(f"Error: {e}"))

    # ---------------- Actions ----------------

    def load_issue_list(self):
        self.all_issues = self.db.get_all_issues_metadata()
        self.filter_issues()

    def filter_issues(self):
        query = self.search_input.text().lower()
        # module_idx = self.module_combo.currentIndex() # Removed based on feedback
        
        self.issue_list.clear()
        
        for issue in self.all_issues:
            # Module Filtering Logic
            category = (issue.get('category') or '').lower()
            tags = str(issue.get('tags', '')).lower()
            name = issue.get('issue_name', '').lower()
            
            is_scrutiny = "scrutiny" in category or "liability" in category or "itc" in category or "rcm" in category
            is_adjudication = "section 7" in category or "fraud" in category
            
            # Fallback if categories are generic
            if not is_scrutiny and not is_adjudication:
                # Assume scrutiny for now or check tags
                pass
            
            # target_module = False
            # if module_idx == 0: target_module = True
            # elif module_idx == 1 and is_scrutiny: target_module = True
            # elif module_idx == 2 and is_adjudication: target_module = True
            
            # if not target_module: continue
            
            # Check Search Query
            if query and (query not in name and query not in category and query not in str(issue.get('issue_id', ''))):
                continue
            
            # Add to List
            item = QListWidgetItem(self.issue_list)
            item.setSizeHint(QSize(200, 60)) # Height for 2 rows
            item.setData(Qt.ItemDataRole.UserRole, issue['issue_id'])
            
            widget = IssueListItemWidget(
                issue['issue_name'], 
                issue['issue_id'], 
                bool(issue.get('active')), 
                issue['category']
            )
            self.issue_list.setItemWidget(item, widget)

    def create_new_issue(self):
        self.current_issue_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
        self.issue_id_input.setText(self.current_issue_id)
        self.issue_name_input.clear()
        self.category_input.setCurrentIndex(0)
        self.severity_input.setCurrentIndex(0)
        self.version_input.setText("1.0")
        self.tags_input.clear()
        self.active_cb.setChecked(False)
        
        self.brief_facts_drc_editor.setHtml("")
        self.brief_facts_scn_editor.setHtml("")
        self.grounds_editor.setHtml("")
        self.include_grounds_cb.setChecked(True)
        self.legal_editor.setHtml("")
        self.conclusion_editor.setHtml("")
        self.include_conclusion_cb.setChecked(True)
        self.table_builder.set_data({})
        self.placeholders_table.setRowCount(0)
        
        self.editor_container.setEnabled(True)
        self.editor_title.setText("Create New Issue")

    def on_issue_selected(self, row):
        if row < 0: return
        item = self.issue_list.item(row)
        issue_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_issue(issue_id)

    def load_issue(self, issue_id):
        issue = self.db.get_issue(issue_id)
        if not issue: return
            
        self.current_issue_id = issue_id
        self.editor_container.setEnabled(True)
        self.editor_title.setText(f"Edit Issue: {issue.get('issue_name')}")
        
        self.issue_id_input.setText(issue_id)
        self.issue_name_input.setText(issue.get('issue_name', ''))
        self.category_input.setCurrentText(issue.get('category', ''))
        self.severity_input.setCurrentText(issue.get('severity', ''))
        self.version_input.setText(issue.get('version', '1.0'))
        self.tags_input.setText(", ".join(issue.get('tags', [])))
        
        meta = [m for m in self.all_issues if m['issue_id'] == issue_id]
        if meta: self.active_cb.setChecked(bool(meta[0]['active']))
        
        templates = issue.get('templates', {})
        self.brief_facts_drc_editor.setHtml(templates.get('brief_facts', ''))
        
        # Load SCN facts - handle migration from old 'scn' key to new 'brief_facts_scn'
        scn_facts = templates.get('brief_facts_scn')
        if not scn_facts:
            scn_facts = templates.get('scn', '')
        self.brief_facts_scn_editor.setHtml(scn_facts)
        
        self.grounds_editor.setHtml(templates.get('grounds', ''))
        self.include_grounds_cb.setChecked(templates.get('include_grounds', True))
        
        self.legal_editor.setHtml(templates.get('legal', ''))
        
        self.conclusion_editor.setHtml(templates.get('conclusion', ''))
        self.include_conclusion_cb.setChecked(templates.get('include_conclusion', True))
        
        self.table_builder.set_data(issue.get('tables', {}))
        
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
        text = (self.brief_facts_drc_editor.toHtml() + self.brief_facts_scn_editor.toHtml() + 
                self.grounds_editor.toHtml() + self.legal_editor.toHtml() + self.conclusion_editor.toHtml())
        matches = set(re.findall(r'\{\{([^}]+)\}\}', text))
        
        current_names = []
        for row in range(self.placeholders_table.rowCount()):
            item = self.placeholders_table.item(row, 0)
            if item: current_names.append(item.text())
            
        count = 0
        for match in matches:
            if match not in current_names:
                self.add_placeholder_row({'name': match, 'type': 'string'})
                count += 1
        QMessageBox.information(self, "Detection Complete", f"Found {count} new placeholders.")

    def save_issue(self):
        if not self.current_issue_id: return
            
        data = {
            "issue_id": self.current_issue_id,
            "issue_name": self.issue_name_input.text(),
            "category": self.category_input.currentText(),
            "severity": self.severity_input.currentText(),
            "version": self.version_input.text(),
            "tags": [t.strip() for t in self.tags_input.text().split(',') if t.strip()],
            "templates": {
                "brief_facts": self.brief_facts_drc_editor.toHtml(),
                "brief_facts_scn": self.brief_facts_scn_editor.toHtml(),
                "include_grounds": self.include_grounds_cb.isChecked(),
                "grounds": self.grounds_editor.toHtml(),
                "legal": self.legal_editor.toHtml(),
                "include_conclusion": self.include_conclusion_cb.isChecked(),
                "conclusion": self.conclusion_editor.toHtml()
            },
            "active": self.active_cb.isChecked(),
            "tables": self.table_builder.get_data()
        }
        
        placeholders = []
        for row in range(self.placeholders_table.rowCount()):
            name = self.placeholders_table.item(row, 0).text()
            if not name: continue
            placeholders.append({
                "name": name, 
                "type": self.placeholders_table.item(row, 1).text(),
                "required": self.placeholders_table.cellWidget(row, 2).isChecked(),
                "computed": self.placeholders_table.cellWidget(row, 3).isChecked()
            })
        data["placeholders"] = placeholders
        
        success, msg = self.db.save_issue(data)
        if success:
            self.db.publish_issue(self.current_issue_id, self.active_cb.isChecked())
            QMessageBox.information(self, "Success", "Issue saved successfully")
            self.load_issue_list()
        else:
            QMessageBox.critical(self, "Error", f"Failed to save: {msg}")

    def delete_issue(self):
        if not self.current_issue_id: return
        confirm = QMessageBox.question(self, "Confirm", "Delete this issue?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_issue(self.current_issue_id)
            self.load_issue_list()
            self.create_new_issue()
