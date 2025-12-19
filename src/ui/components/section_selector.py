import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem, 
                             QLabel, QHeaderView)
from PyQt6.QtCore import Qt
from src.database.db_manager import DatabaseManager

class SectionSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Legal Sections")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.db = DatabaseManager()
        self.sections = [] # List of dicts {title, content, section_number, id}
        
        self.init_ui()
        self.load_sections()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header / Instructions
        lbl = QLabel("Double click to view full content. Expand sections to select specific subsections.")
        lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(lbl)
        
        # Search
        search_layout = QHBoxLayout()
        search_lbl = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter sections by number, title, or content...")
        self.search_input.textChanged.connect(self.filter_tree)
        search_layout.addWidget(search_lbl)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Tree Widget instead of List
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setColumnCount(1)
        layout.addWidget(self.tree_widget)
        
        # Selection Buttons
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_deselect_all)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_insert = QPushButton("Insert Selected")
        self.btn_insert.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 5px 15px;")
        self.btn_insert.clicked.connect(self.accept)
        
        action_layout.addWidget(self.btn_cancel)
        action_layout.addWidget(self.btn_insert)
        layout.addLayout(action_layout)

    def load_sections(self):
        self.sections = self.db.get_cgst_sections()
        self.populate_tree(self.sections)

    def parse_subsections(self, content):
        """
        Parses content to identify subsections starting with (1), (2), etc.
        Returns a list of tuples: (subsection_label, content_text)
        """
        # Regex to match (1), (2), (a), etc. at start of line
        # We look for: newline + (digits/letters) + space
        pattern = r'(?:^|\n)(\([0-9a-zA-Z]+\))\s'
        parts = re.split(pattern, content)
        
        subsections = []
        
        # If parts has content before first match (intro text), handle it
        if parts and parts[0].strip():
            subsections.append(("Intro", parts[0].strip()))
            
        # Iterate over split parts. 
        # re.split includes capturing groups, so we get: [Intro, (1), Content1, (2), Content2...]
        for i in range(1, len(parts), 2):
            label = parts[i]
            text = parts[i+1].strip() if i+1 < len(parts) else ""
            subsections.append((label, text))
            
        return subsections

    def populate_tree(self, sections):
        self.tree_widget.clear()
        
        for sec in sections:
            # Prepare Parent Item
            title = sec.get('title', 'Unknown Section')
            sec_num = sec.get('section_number')
            content = sec.get('content', '')
            
            if sec_num:
                display_text = f"Section {sec_num} - {title}"
            else:
                display_text = title
            
            parent_item = QTreeWidgetItem(self.tree_widget)
            parent_item.setText(0, display_text)
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            parent_item.setCheckState(0, Qt.CheckState.Unchecked)
            
            # Store full section data in parent
            parent_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'section',
                'raw_data': sec
            })
            
            # Parse Subsections
            subsections = self.parse_subsections(content)
            
            if len(subsections) > 1: # Only create children if actual subsections exist
                for sub_label, sub_content in subsections:
                    child_item = QTreeWidgetItem(parent_item)
                    child_text = f"{sub_label} {sub_content[:100]}..."
                    child_item.setText(0, child_text)
                    child_item.setToolTip(0, sub_content)
                    child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    child_item.setCheckState(0, Qt.CheckState.Unchecked)
                    
                    child_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'subsection',
                        'label': sub_label,
                        'content': sub_content,
                        'parent_title': display_text
                    })
            else:
                # If no subsections formatted, allow selecting parent typically
                pass

    def filter_tree(self, text):
        text = text.lower()
        
        # Hide/Show items based on filter
        root = self.tree_widget.invisibleRootItem()
        child_count = root.childCount()
        
        for i in range(child_count):
            item = root.child(i)
            self._filter_recursive(item, text)

    def _filter_recursive(self, item, text):
        # customized logic: if parent matches, show. If child matches, show parent and child.
        data = item.data(0, Qt.ItemDataRole.UserRole)
        match = False
        
        if data:
            if data['type'] == 'section':
                sec = data['raw_data']
                if (text in sec.get('title', '').lower() or 
                    text in sec.get('content', '').lower() or 
                    text in str(sec.get('section_number', '')).lower()):
                    match = True
            elif data['type'] == 'subsection':
                if (text in data['content'].lower() or 
                    text in data['label'].lower()):
                    match = True
        
        # Check children
        child_match = False
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filter_recursive(child, text):
                child_match = True
        
        should_show = match or child_match
        item.setHidden(not should_show)
        if should_show:
             item.setExpanded(True) # Expand if matches found inside
             
        return should_show

    def select_all(self):
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
             root.child(i).setCheckState(0, Qt.CheckState.Checked)

    def deselect_all(self):
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
             root.child(i).setCheckState(0, Qt.CheckState.Unchecked)

    def get_selected_sections(self):
        """
        Returns a list of dicts.
        If a whole section is selected (all children), returns the section dict.
        If specific subsections are selected, returns dicts representing those subsections.
        """
        selected = []
        root = self.tree_widget.invisibleRootItem()
        
        for i in range(root.childCount()):
            parent = root.child(i)
            
            # If parent is fully checked, return the whole section
            # Note: with Tristate, Checked means ALL children are checked.
            if parent.checkState(0) == Qt.CheckState.Checked:
                 data = parent.data(0, Qt.ItemDataRole.UserRole)
                 selected.append({
                     'type': 'section',
                     'title': parent.text(0),
                     'content': data['raw_data']['content'],
                     'section_number': data['raw_data']['section_number']
                 })
            
            # If partially checked, check children
            elif parent.checkState(0) == Qt.CheckState.PartiallyChecked:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
                parent_title = parent.text(0)
                sec_num = data['raw_data']['section_number']
                
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        child_data = child.data(0, Qt.ItemDataRole.UserRole)
                        selected.append({
                            'type': 'subsection',
                            'title': parent_title,
                            'section_number': sec_num,
                            'label': child_data['label'],
                            'content': child_data['content']
                        })
                        
        return selected
