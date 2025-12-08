import sys
import json
import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
                             QLineEdit, QLabel, QFrame, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from src.database.db_manager import DatabaseManager

class GSTHandbook(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.init_ui()
        self.load_act_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📚 GST Handbook")
        header.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #1a237e;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f5f5f5;
                border: 1px solid #e0e0e0;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                font-weight: bold;
                color: #1a237e;
            }
            QTabBar::tab:hover {
                background: #e3f2fd;
            }
        """)
        
        # Act Tab
        self.act_tab, self.act_tree, self.act_content, self.act_search = self.create_handbook_tab("GST Acts")
        self.tabs.addTab(self.act_tab, "📖 GST Acts")
        
        # Rules Tab (placeholder)
        self.rules_tab, self.rules_tree, self.rules_content, self.rules_search = self.create_handbook_tab("GST Rules")
        self.tabs.addTab(self.rules_tab, "📋 GST Rules")
        
        layout.addWidget(self.tabs)

    def create_handbook_tab(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Search Bar with modern styling
        search_container = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText(f"🔍 Search in {title}...")
        search_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
                background: #f8f9fa;
            }
        """)
        search_input.textChanged.connect(lambda: self.on_search_changed(search_input.text()))
        search_container.addWidget(search_input)
        layout.addLayout(search_container)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #e0e0e0;
                width: 2px;
            }
            QSplitter::handle:hover {
                background: #1976d2;
            }
        """)
        
        # Navigation Tree (Left) with modern styling
        tree = QTreeWidget()
        tree.setHeaderLabel("📑 Table of Contents")
        tree.setMinimumWidth(350)
        tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
                font-size: 13px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QTreeWidget::item:hover {
                background: #e3f2fd;
            }
            QTreeWidget::item:selected {
                background: #1976d2;
                color: white;
            }
            QTreeWidget::branch:has-children:closed {
                image: url(none);
            }
            QTreeWidget::branch:has-children:open {
                image: url(none);
            }
            QHeaderView::section {
                background: #1a237e;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        # Set custom font for tree
        tree_font = QFont()
        tree_font.setPointSize(10)
        tree.setFont(tree_font)
        
        splitter.addWidget(tree)
        
        # Content Area (Right) with modern styling
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
            <div style="padding: 30px; text-align: center;">
                <h1 style="color: #1a237e; font-size: 32px; margin-bottom: 15px;">📚 {title}</h1>
                <p style="color: #666; font-size: 16px;">Select a section from the left to view its details</p>
            </div>
        """)
        content.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                background: white;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        splitter.addWidget(content)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        
        return widget, tree, content, search_input

    def load_act_data(self):
        """Loads GST Act data with hierarchical structure: Acts > Chapters > Sections"""
        try:
            self.act_tree.clear()
            
            # Get all Acts from DB
            acts = self.db.get_gst_acts()
            
            for act in acts:
                # Create Act item (Level 1)
                act_item = QTreeWidgetItem(self.act_tree)
                act_item.setText(0, f"📚 {act['title']}")
                act_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'act',
                    'content': f"<h1 style='color: #1a237e;'>{act['title']}</h1>"
                })
                
                # Set bold font for act
                font = act_item.font(0)
                font.setBold(True)
                font.setPointSize(11)
                act_item.setFont(0, font)
                act_item.setForeground(0, QColor("#1a237e"))
                
                # Get chapters for this act
                chapters = self.db.get_act_chapters(act['act_id'])
                
                if chapters:
                    # Act has chapters - create hierarchical structure
                    for chapter in chapters:
                        # Create Chapter item (Level 2)
                        chapter_item = QTreeWidgetItem(act_item)
                        # Format chapter ID with uppercase Roman numerals
                        chapter_id_display = chapter['chapter_id'].replace('CHAPTER_', 'CHAPTER ').upper()
                        chapter_display = f"📖 {chapter_id_display}"
                        if chapter['chapter_name']:
                            chapter_display += f" - {chapter['chapter_name']}"
                        chapter_item.setText(0, chapter_display)
                        chapter_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'chapter',
                            'content': f"<h2 style='color: #1976d2;'>{chapter_display}</h2>"
                        })
                        
                        # Set font for chapter
                        chapter_font = chapter_item.font(0)
                        chapter_font.setBold(True)
                        chapter_font.setPointSize(10)
                        chapter_item.setFont(0, chapter_font)
                        chapter_item.setForeground(0, QColor("#1976d2"))
                        
                        # Get sections for this chapter
                        sections = self.db.get_act_sections(act['act_id'], chapter['chapter_id'])
                        
                        for section in sections:
                            self.add_section_item(chapter_item, section)
                    
                    # Expand first act by default (usually CGST Act 2017)
                    if "Central Goods and Services Tax Act, 2017" in act['title']:
                        act_item.setExpanded(True)
                else:
                    # Act has no chapters - add sections directly
                    sections = self.db.get_act_sections(act['act_id'])
                    for section in sections:
                        self.add_section_item(act_item, section)

            self.act_tree.itemClicked.connect(self.display_content)

        except Exception as e:
            self.act_content.setText(f"<div style='color: red; padding: 20px;'>Error loading data: {str(e)}</div>")

    def add_section_item(self, parent_item, section):
        """Add a section item to the tree"""
        section_item = QTreeWidgetItem(parent_item)
        
        title = section['title']
        section_no = section['section_number']
        content = section['content']
        
        # Display text with section number
        if section_no:
            display_text = f"📄 Section {section_no}: {title[:50]}"
        else:
            # For sections without numbers, still show the title
            display_text = f"📄 {title[:60]}"
        
        if len(title) > 50:
            display_text += "..."
        
        section_item.setText(0, display_text)
        
        # Separate main content from footnotes
        main_content, footnotes = self.extract_footnotes(content)
        
        # Format content for display with section number in heading
        formatted_content = f"""
        <div style="padding: 20px; max-width: 900px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h2 style="color: white; margin: 0; font-size: 24px;">
                    {f'Section {section_no}: {title}' if section_no else title}
                </h2>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; 
                        border-left: 4px solid #1976d2; line-height: 1.8;">
                <pre style="white-space: pre-wrap; font-family: 'Segoe UI', Arial, sans-serif; 
                           font-size: 14px; color: #333; margin: 0;">{main_content}</pre>
            </div>
            
            {self.format_footnotes(footnotes) if footnotes else ''}
        </div>
        """
        
        section_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'section',
            'content': formatted_content
        })

    def display_content(self, item, column):
        """Display content of the selected item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and 'content' in data:
            self.act_content.setHtml(data['content'])

    def on_search_changed(self, text):
        """Handle search input changes with debouncing"""
        self.search_timer.stop()
        if text.strip():
            self.search_timer.start(500)  # 500ms delay
        else:
            self.load_act_data()  # Reset to full view

    def perform_search(self):
        """Perform the actual search"""
        query = self.act_search.text().strip()
        if not query:
            return
        
        try:
            results = self.db.search_handbook(query)
            
            self.act_tree.clear()
            
            if not results:
                no_results = QTreeWidgetItem(self.act_tree)
                no_results.setText(0, "No results found")
                return
            
            # Group results by act
            acts_dict = {}
            for result in results:
                act_title = result.get('act_title', 'Unknown Act')
                if act_title not in acts_dict:
                    acts_dict[act_title] = []
                acts_dict[act_title].append(result)
            
            # Display grouped results
            for act_title, sections in acts_dict.items():
                act_item = QTreeWidgetItem(self.act_tree)
                act_item.setText(0, f"📚 {act_title} ({len(sections)} results)")
                act_item.setExpanded(True)
                
                font = act_item.font(0)
                font.setBold(True)
                act_item.setFont(0, font)
                
                for section in sections:
                    self.add_section_item(act_item, section)
            
        except Exception as e:
            print(f"Search error: {e}")
    
    def extract_footnotes(self, content):
        """
        Separate main content from footnotes.
        Footnotes typically start with patterns like:
        '1. Subs.', '2. Ins.', '1. The word', etc.
        """
        import re
        
        # Split content into lines
        lines = content.split('\n')
        
        main_lines = []
        footnote_lines = []
        in_footnotes = False
        
        for line in lines:
            # Check if line starts a footnote
            # Pattern: starts with number followed by period and common footnote keywords
            if re.match(r'^\d+\.\s+(Subs\.|Ins\.|The\s+word|The\s+proviso|Clause|Omitted|Explanation)', line):
                in_footnotes = True
                footnote_lines.append(line)
            elif in_footnotes:
                # Continue collecting footnote lines
                # Stop if we hit a new section or empty line followed by non-footnote content
                if line.strip() == '':
                    footnote_lines.append(line)
                elif any(keyword in line for keyword in ['Act', 'ibid', 'w.e.f', 's.', 'for']):
                    footnote_lines.append(line)
                else:
                    # Might be end of footnotes
                    main_lines.append(line)
            else:
                main_lines.append(line)
        
        main_content = '\n'.join(main_lines).strip()
        footnotes = '\n'.join(footnote_lines).strip()
        
        return main_content, footnotes
    
    def format_footnotes(self, footnotes):
        """Format footnotes with distinct styling"""
        if not footnotes:
            return ''
        
        return f"""
            <div style="margin-top: 25px; padding-top: 20px; border-top: 2px solid #ddd;">
                <div style="background: #fafafa; padding: 15px 20px; border-radius: 8px; 
                            border-left: 4px solid #9e9e9e;">
                    <h4 style="color: #666; margin: 0 0 12px 0; font-size: 13px; 
                               font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                        📌 Amendments & Footnotes
                    </h4>
                    <pre style="white-space: pre-wrap; font-family: 'Segoe UI', Arial, sans-serif; 
                               font-size: 11px; color: #666; margin: 0; font-style: italic; 
                               line-height: 1.6;">{footnotes}</pre>
                </div>
            </div>
        """

    def load_rules_data(self):
        """Placeholder for Rules data"""
        pass
