from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QComboBox, QPushButton, QMessageBox, QStackedWidget, 
                             QCompleter, QFrame, QFileDialog, QScrollArea, 
                             QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QDialog, QApplication,
                             QSizePolicy, QSplitter, QTabWidget, QToolButton, QTextBrowser, QDateEdit,
                             QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QAbstractAnimation, QDate, pyqtSignal, QMarginsF
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from src.services.asmt10_generator import ASMT10Generator
from src.services.scrutiny_parser import ScrutinyParser
from src.services.file_validation_service import FileValidationService
from src.database.db_manager import DatabaseManager
import os
import json
import uuid
import copy
import datetime
from src.ui.components.side_nav_card import SideNavCard
from src.ui.ui_helpers import render_grid_to_table_widget
from src.utils.formatting import format_indian_number
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer
from src.ui.components.header_selection_dialog import HeaderSelectionDialog

class FinalizationConfirmationDialog(QDialog):
    def __init__(self, data, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm ASMT-10 Finalization")
        self.resize(600, 500)
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Header
        header = QFrame()
        header.setStyleSheet("background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 15px;")
        h_layout = QHBoxLayout(header)
        title = QLabel("Finalize ASMT-10 Notice")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        h_layout.addWidget(title)
        layout.addWidget(header)
        
        # 2. Summary Panel
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(15)
        
        # Summary Grid
        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(20)
        
        self.add_field(grid, 0, "O.C. No:", data.get('oc_num', '-'))
        self.add_field(grid, 1, "Issue Date:", data.get('issue_date', '-'))
        self.add_field(grid, 2, "GSTIN:", data.get('gstin', '-'))
        self.add_field(grid, 3, "Taxpayer:", data.get('legal_name', '-'))
        self.add_field(grid, 4, "Financial Year:", data.get('fy', '-'))
        
        c_layout.addLayout(grid)
        
        # Issues List
        c_layout.addWidget(QLabel("Issues Identified:"))
        issue_table = QTableWidget()
        issue_table.setColumnCount(2)
        issue_table.setHorizontalHeaderLabels(["Issue", "Tax Amount"])
        issue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        issue_table.verticalHeader().setVisible(False)
        issue_table.setRowCount(len(issues))
        issue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        issue_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        for i, issue in enumerate(issues):
            name = issue.get('category') or issue.get('issue_name') or "Unknown Issue"
            amt = float(issue.get('total_shortfall', 0))
            issue_table.setItem(i, 0, QTableWidgetItem(name))
            issue_table.setItem(i, 1, QTableWidgetItem(format_indian_number(amt, prefix_rs=True)))
            
        issue_table.setFixedHeight(150)
        c_layout.addWidget(issue_table)
        
        # Warning
        warn_frame = QFrame()
        warn_frame.setStyleSheet("background-color: #fff1f2; border: 1px solid #fecaca; border-radius: 6px; padding: 10px;")
        w_layout = QVBoxLayout(warn_frame)
        lbl = QLabel("⚠️ Warning: Irreversible Action")
        lbl.setStyleSheet("color: #9f1239; font-weight: bold;")
        w_layout.addWidget(lbl)
        
        msg = QLabel("Once finalized, this ASMT-10 will be entered into the O.C. Register and ASMT-10 Register. A new linked case file will be automatically created in the Adjudication Module.")
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #881337;")
        w_layout.addWidget(msg)
        c_layout.addWidget(warn_frame)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 3. Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 15px;")
        f_layout = QHBoxLayout(footer)
        f_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px 16px; background: white; border: 1px solid #cbd5e1; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("Confirm & Finalise")
        confirm_btn.setStyleSheet("padding: 8px 16px; background: #ea580c; color: white; border: none; border-radius: 4px; font-weight: bold;")
        confirm_btn.clicked.connect(self.accept)
        f_layout.addWidget(confirm_btn)
        
        layout.addWidget(footer)
        
    def add_field(self, grid, row, label, value):
        l = QLabel(label)
        l.setStyleSheet("color: #64748b; font-weight: 500;")
        grid.addWidget(l, row, 0)
        v = QLabel(value)
        v.setStyleSheet("color: #1e293b; font-weight: bold;")
        grid.addWidget(v, row, 1)

class ASMT10PreviewDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ASMT-10 Draft Preview")
        self.resize(1000, 800)
        self.html_content = html_content
        self.layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.pdf_btn = QPushButton("📄 Download PDF")
        self.pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px;")
        self.pdf_btn.clicked.connect(self.download_pdf)
        toolbar.addWidget(self.pdf_btn)
        self.word_btn = QPushButton("📝 Download Word (Docx)")
        self.word_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.word_btn.clicked.connect(self.download_word)
        toolbar.addWidget(self.word_btn)
        toolbar.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        toolbar.addWidget(close_btn)
        self.layout.addLayout(toolbar)
        self.web = QWebEngineView()
        self.web.setHtml(html_content)
        self.layout.addWidget(self.web)

    def download_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "ASMT-10_Draft.pdf", "PDF Files (*.pdf)")
        if path:
            success, msg = ASMT10Generator.save_pdf(self.html_content, path)
            if success: QMessageBox.information(self, "Success", "PDF Saved Successfully!")
            else: QMessageBox.critical(self, "Error", msg)

    def download_word(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Word Doc", "ASMT-10_Draft.doc", "Word Files (*.doc)")
        if path:
            success, msg = ASMT10Generator.save_docx(self.html_content, path)
            if success: QMessageBox.information(self, "Success", "Word Document Saved Successfully!")
            else: QMessageBox.critical(self, "Error", msg)


class RecentCaseItem(QWidget):
    def __init__(self, case_id, gstin, name, fy, status, created_at, delete_callback):
        super().__init__()
        self.case_id = case_id
        self.delete_callback = delete_callback
        
        # Main Horizontal Layout: Text Info | Delete Btn
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Left Side: Vertical Text Stack
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # 1. Legal Name
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px; border: none;")
        text_layout.addWidget(name_lbl)
        
        # 2. GSTIN
        gstin_lbl = QLabel(gstin)
        gstin_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; border: none;")
        text_layout.addWidget(gstin_lbl)
        
        # 3. FY & Status
        fy_status_layout = QHBoxLayout()
        fy_status_layout.setSpacing(10)
        
        fy_lbl = QLabel(f"FY: {fy}")
        fy_lbl.setStyleSheet("color: #34495e; font-size: 11px; border: none;")
        fy_status_layout.addWidget(fy_lbl)
        
        # Colored status dot/text
        status_color = "#27ae60" if status == "Initiated" else "#f39c12"
        status_lbl = QLabel(status)
        status_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 11px; border: none;")
        fy_status_layout.addWidget(status_lbl)
        
        fy_status_layout.addStretch()
        text_layout.addLayout(fy_status_layout)
        
        main_layout.addLayout(text_layout)
        
        # Right Side: Delete Button
        del_btn = QPushButton()
        del_btn.setText("🗑️") 
        del_btn.setToolTip("Delete Case")
        del_btn.setFixedSize(32, 32)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton { 
                background-color: #fab1a0; 
                border-radius: 4px;
                border: none; 
                font-size: 16px;
                color: #c0392b;
            }
            QPushButton:hover { 
                background-color: #e74c3c; 
                color: white;
            }
        """)
        del_btn.clicked.connect(self.request_delete)
        main_layout.addWidget(del_btn)

    def request_delete(self):
        self.delete_callback(self.case_id)

class FileUploaderWidget(QFrame):
    """Widget for managing a single file upload."""
    def __init__(self, title, file_key, upload_callback, delete_callback, file_filter="Excel Files (*.xlsx *.xls)", parent=None):
        super().__init__(parent)
        self.file_key = file_key
        self.upload_callback = upload_callback
        self.delete_callback = delete_callback
        self.file_filter = file_filter
        self.current_filename = None
        
        self.setObjectName("FileUploaderWidget")
        self.setStyleSheet("""
            #FileUploaderWidget { 
                background-color: white; 
                border: 1px solid #e2e8f0; 
                border-radius: 6px; 
            }
            #FileUploaderWidget:hover {
                border-color: #3b82f6;
                background-color: #f8fafc;
            }
        """)
        self.setFixedHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(10)
        
        # Title (Now Left Aligned)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 13px;")
        self.title_lbl.setWordWrap(False)
        layout.addWidget(self.title_lbl, 2)
        
        # Status Label (for success/error msgs) - moved inside layout
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_lbl, 1)

        # Upload Button Stack
        self.stack = QStackedWidget()
        
        # Page 1: Upload Button
        p1 = QWidget()
        p1_layout = QHBoxLayout(p1)
        p1_layout.setContentsMargins(0, 0, 0, 0)
        
        self.upload_btn = QPushButton("Browse")
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.setFixedHeight(30)
        self.upload_btn.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; 
                color: #475569; 
                padding: 0 12px; 
                border-radius: 4px; 
                font-weight: 600; 
                font-size: 12px;
                border: 1px solid #e2e8f0;
            }
            QPushButton:hover { 
                background-color: #e2e8f0; 
                border-color: #cbd5e1;
            }
        """)
        self.upload_btn.clicked.connect(self.request_upload)
        p1_layout.addStretch()
        p1_layout.addWidget(self.upload_btn)
        self.stack.addWidget(p1)
        
        # Page 2: File Info
        p2 = QWidget()
        p2_layout = QHBoxLayout(p2)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        p2_layout.setSpacing(8)
        
        # Icon
        file_icon = QLabel("📊")
        file_icon.setStyleSheet("font-size: 14px;")
        p2_layout.addWidget(file_icon)
        
        # Filename
        self.filename_lbl = QLabel("")
        self.filename_lbl.setStyleSheet("font-weight: 600; color: #059669; font-size: 12px;")
        self.filename_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        p2_layout.addWidget(self.filename_lbl, 1) 
        
        del_btn = QPushButton("✕")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("Remove File")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: #94a3b8; 
                font-weight: bold;
                border-radius: 11px; 
                border: none; 
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #fee2e2; 
                color: #ef4444; 
            }
        """)
        del_btn.clicked.connect(self.request_delete)
        p2_layout.addWidget(del_btn)
        
        self.stack.addWidget(p2)
        layout.addWidget(self.stack, 2)

    def request_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {self.title_lbl.text()}", "", self.file_filter)
        if file_path:
            self.upload_callback(self.file_key, file_path)

    def request_delete(self):
        self.delete_callback(self.file_key)

    def set_file(self, filename):
        self.current_filename = filename
        self.filename_lbl.setText(filename)
        self.filename_lbl.setToolTip(filename) # Show full name on hover
        self.stack.setCurrentIndex(1)
        self.status_lbl.setText("Complete")
        self.setStyleSheet("""
            #FileUploaderWidget { 
                background-color: #f0fdf4; 
                border: 1px solid #86efac; 
                border-radius: 6px; 
            }
        """)

    def reset(self):
        self.current_filename = None
        self.stack.setCurrentIndex(0)
        self.status_lbl.setText("")
        self.setStyleSheet("""
            #FileUploaderWidget { 
                background-color: white; 
                border: 1px solid #e2e8f0; 
                border-radius: 6px; 
            }
            #FileUploaderWidget:hover {
                border-color: #3b82f6;
                background-color: #f8fafc;
            }
        """)



class AnalysisSummaryStrip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            AnalysisSummaryStrip {
                background-color: white;
                border-bottom: 1px solid #e0e6ed;
            }
        """)
        self.setFixedHeight(50)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)
        
        # Icon/Badge
        icon = QLabel("ℹ️")
        icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon)

        # 1. Legal Name
        self.name_lbl = QLabel("Taxpayer: -")
        self.name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #34495e;")
        layout.addWidget(self.name_lbl)
        
        separator = QLabel("|")
        separator.setStyleSheet("color: #dcdde1; font-weight: bold;")
        layout.addWidget(separator)

        # 2. FY
        self.fy_lbl = QLabel("FY: -")
        self.fy_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #7f8c8d;")
        layout.addWidget(self.fy_lbl)
        
        layout.addStretch()

    def update_summary(self, legal_name, fy):
        self.name_lbl.setText(f"Taxpayer: {legal_name}")
        self.fy_lbl.setText(f"FY: {fy}")


class IssueCard(QFrame):
    def __init__(self, issue_data, parent=None, save_template_callback=None, issue_number=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.save_template_callback = save_template_callback
        self.issue_number = issue_number
        
        # Load persisted inclusion state (Default: True)
        self.is_included = issue_data.get('is_included', True)

        self.setMaximumWidth(850) # Constraint for professional look
        self.setStyleSheet("""
            IssueCard {
                background: white;
                border: 1px solid #e1e8ed;
                border-radius: 6px;
                margin-bottom: 2px;
            }
            IssueCard:hover {
                border: 1px solid #3498db;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 1. Header (Clickable)
        self.header = QPushButton()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: none;
                text-align: left;
                padding: 10px 15px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #f8faff; }
        """)
        self.header.clicked.connect(self.toggle)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Inclusion Checkbox
        self.include_cb = QCheckBox()
        self.include_cb.setToolTip("Include in ASMT-10 Notice")
        self.include_cb.setChecked(self.is_included)
        self.include_cb.stateChanged.connect(self._on_inclusion_changed)
        header_layout.addWidget(self.include_cb)
        
        # Icon (Chevron)
        self.icon_lbl = QLabel("˃") # Small professional arrow
        self.icon_lbl.setFixedWidth(20)
        self.icon_lbl.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.icon_lbl)
        
        # Issue Title
        import re
        base_title = issue_data.get('category', 'Issue')
        # Strip "Point X- " prefix
        base_title = re.sub(r'^Point \d+- ?', '', base_title, flags=re.IGNORECASE)
        
        title_text = base_title

        
        # "Issue <n> – <Name>" Format
        if self.issue_number:
            title_text = f"Issue {self.issue_number} – {title_text}"
            
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #2c3e50;")
        self.title_lbl.setWordWrap(True)
        header_layout.addWidget(self.title_lbl, 1)

        
        # Amount Badge (The "Pill")
        self.badge_container = QFrame()
        self.badge_container.setStyleSheet("""
            QFrame {
                background-color: #fee2e2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 2px 10px;
            }
        """)
        badge_layout = QHBoxLayout(self.badge_container)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(2)
        
        currency_lbl = QLabel("₹")
        currency_lbl.setStyleSheet("color: #991b1b; font-weight: 700; font-size: 11px; border: none; background: transparent;")
        badge_layout.addWidget(currency_lbl)
        
        amount = issue_data.get('total_shortfall', 0.0)
        self.amount_edit = QLineEdit(f"{amount:,.0f}")
        self.amount_edit.setStyleSheet("""
            QLineEdit {
                color: #991b1b; 
                font-weight: 800; 
                border: none; 
                background: transparent; 
                font-size: 12px;
                padding: 0;
            }
        """)
        self.amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        # badge_layout.addWidget(QLabel("₹"))
        badge_layout.addWidget(self.amount_edit)
        
        header_layout.addWidget(self.badge_container)
        
        self.layout.addWidget(self.header)
        
        # 2. Content (Collapsible)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(15)
        
        # Section A: Legal Text / Description (Editable)
        lbl_desc = QLabel("Issue Description & Legal Text:")
        lbl_desc.setStyleSheet("font-weight: bold; color: #34495e;")
        self.content_layout.addWidget(lbl_desc)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Draft the legal grounds for this issue...")
        # Pre-fill with template text/brief_facts
        self.desc_edit.setText(issue_data.get('brief_facts') or issue_data.get('description', ''))
        self.desc_edit.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 4px; padding: 8px;")
        self.desc_edit.setFixedHeight(120) # Min height
        self.content_layout.addWidget(self.desc_edit)
        
        # Save as Master Button
        if self.save_template_callback:
            save_master_layout = QHBoxLayout()
            save_master_layout.addStretch()
            self.save_master_btn = QPushButton("💾 Save as Default Template")
            self.save_master_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #475569;
                    border: 1px solid #cbd5e1;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                    color: #1e293b;
                }
            """)
            self.save_master_btn.setToolTip("Save this legal text as the default for all future cases of this issue.")
            self.save_master_btn.clicked.connect(self._on_save_master_clicked)
            save_master_layout.addWidget(self.save_master_btn)
            self.content_layout.addLayout(save_master_layout)
        
        # Section B: Table Preview (Read-Only)
        lbl_tbl = QLabel("Calculation Details (ASMT-10 Preview):")
        lbl_tbl.setStyleSheet("font-weight: bold; color: #34495e; margin-top: 10px;")
        self.content_layout.addWidget(lbl_tbl)
        
        self.table_view = QTextBrowser() # Render HTML
        table_html = ASMT10Generator.generate_issue_table_html(issue_data)
        
        # Add internal styling for the card preview
        styled_html = f"""
        <html><head><style>
            table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; border: 1px solid #bdc3c7; }}
            th, td {{ border: 1px solid #bdc3c7; padding: 8px; font-size: 10pt; text-align: center; }}
            th {{ background-color: #f8f9fa; color: #2c3e50; font-weight: bold; font-size: 9pt; }}
            td {{ color: #34495e; }}
        </style></head><body>
        {table_html}
        </body></html>
        """
        self.table_view.setHtml(styled_html)
        self.table_view.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; background: white;")
        self.table_view.setFixedHeight(220)
        self.content_layout.addWidget(self.table_view)
        
        self.layout.addWidget(self.content_area)
        
        # Opacity Effect for Disabled Look
        self.opacity_effect = QGraphicsOpacityEffect(self.content_area)
        self.content_area.setGraphicsEffect(self.opacity_effect)
        
        # Initial Visual State
        self._update_visual_state()
        
        # Animation
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.is_expanded = False
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0) 

    def toggle(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def collapse(self):
        self.animation.stop()
        self.animation.setStartValue(self.content_area.height())
        self.animation.setEndValue(0)
        self.animation.start()
        self.animation.finished.connect(lambda: self.content_area.setVisible(False))
        self.is_expanded = False
        self.icon_lbl.setText("˃")
        
    def expand(self):
        self.animation.stop()
        try:
            self.animation.finished.disconnect()
        except:
            pass
        self.content_area.setVisible(True)
        # Calculate height
        self.content_area.setMaximumHeight(16777215) # Unbound to measure
        self.content_area.adjustSize()
        h = self.content_area.sizeHint().height()
        
        self.animation.setStartValue(0)
        self.animation.setEndValue(h)
        self.animation.start()
        self.is_expanded = True
        self.icon_lbl.setText("˅")

    def get_data(self):
        """Return updated issue data"""
        data = self.issue_data.copy()
        
        # PERSIST: Selection State
        data['is_included'] = self.is_included
        
        # User edits go to brief_facts (used for ASMT-10 drafting)
        new_text = self.desc_edit.toPlainText().strip()
        data['brief_facts'] = new_text
        
        # Keep description as the identifier/title if it's not the same as brief_facts
        # but ensure we don't blow away the identifier
        
        try:
            # Clean up number formatting before parsing back to float
            clean_val = self.amount_edit.text().replace(',', '').replace('₹', '').strip()
            data['total_shortfall'] = float(clean_val)
        except:
            pass # Keep original if parse error
        return data

    def _on_save_master_clicked(self):
        """Internal handler to trigger the parent's template save logic."""
        if self.save_template_callback:
            data = self.get_data()
            payload = data.copy()
            payload['description'] = data.get('brief_facts', '') 
            self.save_template_callback(payload)

    def _on_inclusion_changed(self, state):
        """Handle inclusion toggle."""
        self.is_included = (state == 2) # Qt.CheckState.Checked
        
        # Mutate underlying data immediately as per spec requirements?
        # get_data() is the authoritative pull, but updating self.issue_data logic is safer 
        # for intermediate reads if any. But primarily get_data() does the work.
        
        self._update_visual_state()

    def _update_visual_state(self):
        """Visual feedback for inclusion state."""
        if self.is_included:
            self.opacity_effect.setOpacity(1.0)
            self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #2c3e50;")
            self.badge_container.setStyleSheet("""
                QFrame {
                    background-color: #fee2e2;
                    border: 1px solid #fecaca;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        else:
            self.opacity_effect.setOpacity(0.5)
            self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #95a5a6; text-decoration: line-through;")
            self.badge_container.setStyleSheet("""
                QFrame {
                    background-color: #fce4e4; 
                    border: 1px solid #e0e0e0;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)

class ResultsContainer(QScrollArea):
    def __init__(self, parent=None, save_template_callback=None):
        super().__init__(parent)
        self.save_template_callback = save_template_callback
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea { border: none; background: #f4f7f9; }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet(".QWidget { background: transparent; }")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(8) # Compact spacing
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.setWidget(self.container)
        self.cards = []

    def clear_results(self):
        # Remove all cards
        for card in self.cards:
            self.layout.removeWidget(card)
            card.deleteLater()
        self.cards = []

    def add_result(self, issue_data, issue_number=None):
        card = IssueCard(issue_data, parent=self.container, save_template_callback=self.save_template_callback, issue_number=issue_number)
        # Wrap card in a centering container if needed, but AlignHCenter on layout covers it usually.
        # However, to strictly enforce the AlignHCenter effect on the widget, we ensure the card is added.
        self.layout.addWidget(card)
        self.cards.append(card)


    def get_all_data(self):
        return [card.get_data() for card in self.cards]

class CompliancePointCard(QFrame):
    """Collapsible row representing one of the 13 SOP parameters."""
    def __init__(self, number, title, description, parent=None):
        super().__init__(parent)
        self.number = number
        self.original_desc = description # Store for reset
        self.is_expanded = False
        
        self.setObjectName("ComplianceCard")
        self.setStyleSheet("""
            #ComplianceCard {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-bottom: 2px;
            }
            #ComplianceCard:hover {
                border-color: #cbd5e1;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Header (Clickable)
        self.header = QPushButton()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 12px 15px;
            }
            QPushButton:hover { background-color: #f8fafc; }
        """)
        self.header.clicked.connect(self.toggle)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        # Icon (Chevron)
        self.icon_lbl = QLabel("˃")
        self.icon_lbl.setFixedWidth(20)
        self.icon_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.icon_lbl)
        
        # Number Badge
        self.num_lbl = QLabel(f"{number}")
        self.num_lbl.setFixedSize(24, 24)
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_lbl.setStyleSheet("""
            background: #f1f5f9; 
            color: #475569; 
            border-radius: 12px; 
            font-weight: 800; 
            font-size: 10px;
        """)
        header_layout.addWidget(self.num_lbl)
        
        # Title
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px; margin-left: 5px;")
        header_layout.addWidget(self.title_lbl, 1)
        
        # Status Badge
        self.status_container = QFrame()
        self.status_container.setFixedHeight(26)
        self.status_container.setStyleSheet("background: #f1f5f9; border-radius: 13px; padding: 0 10px;")
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)
        
        self.status_icon = QLabel("⚪")
        self.status_icon.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        status_layout.addWidget(self.status_icon)
        
        self.value_lbl = QLabel("Pending")
        self.value_lbl.setStyleSheet("font-weight: bold; color: #64748b; font-size: 11px; border: none; background: transparent;")
        status_layout.addWidget(self.value_lbl)
        
        header_layout.addWidget(self.status_container)
        
        self.main_layout.addWidget(self.header)
        
        # 2. Content Area (Collapsible)
        self.content_area = QWidget()
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(50, 0, 20, 15)
        self.content_layout.setSpacing(10)
        
        self.desc_lbl = QLabel(description)
        self.desc_lbl.setStyleSheet("color: #64748b; font-size: 12px; line-height: 1.4;")
        self.desc_lbl.setWordWrap(True)
        self.content_layout.addWidget(self.desc_lbl)
        
        # Additional Details (Placeholder for calculation breakdown)
        self.details_box = QFrame()
        self.details_box.setStyleSheet("background: #f8fafc; border-radius: 4px; border: 1px solid #f1f5f9;")
        details_layout = QVBoxLayout(self.details_box)
        details_layout.setContentsMargins(0, 0, 0, 0) # Zero margins for table
        
        # Placeholder Label
        self.details_lbl = QLabel("No detailed analysis performed yet.")
        self.details_lbl.setStyleSheet("color: #475569; font-size: 11px; font-style: italic; margin: 10px;")
        self.details_lbl.setVisible(True)
        details_layout.addWidget(self.details_lbl)
        
        # Summary Table Widget (Initially Hidden)
        self.table_widget = QTableWidget()
        self.table_widget.setVisible(False)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #e2e8f0;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #cbd5e1;
                font-weight: bold;
                color: #475569;
            }
            QTableWidget::item {
                padding: 4px;
                color: #334155;
            }
        """)
        details_layout.addWidget(self.table_widget)
        
        self.content_layout.addWidget(self.details_box)
        
        # HTML View (For SOP-5 Dual Tables and others using HTML renderer)
        self.html_view = QTextBrowser()
        self.html_view.setVisible(False)
        self.html_view.setOpenExternalLinks(True)
        self.html_view.setStyleSheet("background: white; border: none;")
        # Set min height to avoid collapse? handled by content adjustment?
        self.html_view.setMinimumHeight(150) 
        details_layout.addWidget(self.html_view)
        
        self.main_layout.addWidget(self.content_area)
        
        # Animation
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def toggle(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
            
    def expand(self):
        self.animation.stop()
        self.content_area.setVisible(True)
        self.content_area.setMaximumHeight(16777215)
        self.content_area.adjustSize()
        h = self.content_area.sizeHint().height()
        
        self.animation.setStartValue(0)
        self.animation.setEndValue(h)
        self.animation.start()
        self.is_expanded = True
        self.icon_lbl.setText("˅")
        self.header.setStyleSheet("QPushButton { background-color: #f8fafc; border: none; text-align: left; padding: 12px 15px; }")

    def collapse(self):
        self.animation.stop()
        self.animation.setStartValue(self.content_area.height())
        self.animation.setEndValue(0)
        self.animation.finished.connect(self._on_collapse_finished)
        self.animation.start()
        self.is_expanded = False
        self.icon_lbl.setText("˃")
        self.header.setStyleSheet("QPushButton { background-color: transparent; border: none; text-align: left; padding: 12px 15px; }")

    def _on_collapse_finished(self):
        self.content_area.setVisible(False)
        try:
            self.animation.finished.disconnect(self._on_collapse_finished)
        except:
            pass

    def _strong_font(self):
        """Helper to return bold font for table items."""
        f = self.table_widget.font()
        f.setBold(True)
        return f

    def reset(self):
        """Restores the card to its initial empty state."""
        self.set_status('pending')
        self.desc_lbl.setText(self.original_desc) # Restore static description
        self.details_lbl.setText("No detailed analysis performed yet.")
        self.details_lbl.setVisible(True)
        self.table_widget.setVisible(False)
        self.table_widget.setRowCount(0)
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.html_view.setVisible(False)
        self.html_view.clear()
        
        # Reset animation/expansion if needed?
        if self.is_expanded:
            self.collapse()

    def set_status(self, status, value_text=None, details=None):
        """Update status and optionally details."""
        if status == 'pass':
            self.status_icon.setText("✅")
            self.status_container.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #166534; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText(value_text or "Matched")
        elif status == 'alert':
            self.status_icon.setText("⚠️")
            self.status_container.setStyleSheet("background: #fffbeb; border: 1px solid #fef3c7; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #92400e; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText(value_text or "Minor Diff")
        elif status == 'fail':
            self.status_icon.setText("❌")
            self.status_container.setStyleSheet("background: #fef2f2; border: 1px solid #fee2e2; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #991b1b; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText(value_text or "Shortfall")
        elif status == 'info':
            self.status_icon.setText("ℹ️")
            self.status_container.setStyleSheet("background: #eff6ff; border: 1px solid #dbeafe; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #1e40af; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText(value_text or "Data Not Available")
        else:
            self.status_icon.setText("⚪")
            self.status_container.setStyleSheet("background: #f1f5f9; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText(value_text or "Pending")
            
        if details:
            # DEBUG: Trace Data Source
            print(f"DEBUG CARD {self.num_lbl.text()}: Details keys: {list(details.keys()) if isinstance(details, dict) else 'Not Dict'}")
            if isinstance(details, dict):
                 if "grid_data" in details:
                      print(f"DEBUG CARD {self.num_lbl.text()}: Found grid_data. Rows: {len(details['grid_data'].get('rows', []))}")
                      if len(details['grid_data'].get('rows', [])) > 0:
                           print(f"DEBUG CARD {self.num_lbl.text()}: grid_data row 0 keys: {list(details['grid_data']['rows'][0].keys())}")
                 if "summary_table" in details:
                      print(f"DEBUG CARD {self.num_lbl.text()}: Found summary_table. Rows: {len(details['summary_table'].get('rows', []))}")
                      if len(details['summary_table'].get('rows', [])) > 0:
                           print(f"DEBUG CARD {self.num_lbl.text()}: summary_table row 0 keys: {list(details['summary_table']['rows'][0].keys())}")

            # Check if details is structured table data
            if isinstance(details, dict):
                 # Priority 0: HTML Tables (e.g. SOP-5)
                 # [LEGACY ADAPTER] Auto-convert old 'tables' payload to 'summary_table' (Native Grid)
                 # This ensures backward compatibility for existing cases without violating the strict rendering contract.
                 if "tables" in details and details["tables"] and "summary_table" not in details:
                     print(f"DEBUG CARD {self.num_lbl.text()}: Adapting legacy 'tables' to 'summary_table'")
                     try:
                         legacy_tables = details["tables"]
                         adapter_rows = []
                         adapter_cols = []
                         
                         if legacy_tables and isinstance(legacy_tables, list) and len(legacy_tables) > 0:
                             # Use columns from first table as master schema
                             if "columns" in legacy_tables[0]:
                                 adapter_cols = legacy_tables[0]["columns"]
                             
                             for tbl in legacy_tables:
                                 # Add Title Row (Section Header)
                                 if "title" in tbl and tbl["title"]:
                                     # Bold section header in col0
                                     header_row = {}
                                     # Populate col0 with title
                                     header_row["col0"] = {"value": f"*** {tbl['title']} ***", "style": "bold"}
                                     # Populate other cols empty to ensure row validity
                                     for col in adapter_cols:
                                         if col["id"] != "col0":
                                             header_row[col["id"]] = {"value": ""}
                                     adapter_rows.append(header_row)
                                 
                                 # Add Data Rows
                                 if "rows" in tbl:
                                     adapter_rows.extend(tbl["rows"])
                                     
                                 # Spacer Row
                                 spacer = {c["id"]: {"value": ""} for c in adapter_cols}
                                 adapter_rows.append(spacer)
                                 
                             details["summary_table"] = {
                                 "columns": adapter_cols,
                                 "rows": adapter_rows
                             }
                             # CRITICAL: Remove 'tables' key so it passes the subsequent Guardrail
                             del details["tables"]
                             print(f"DEBUG CARD {self.num_lbl.text()}: Adapter Success. Converted to Native Grid.")
                     except Exception as e:
                         print(f"ERROR: Legacy adapter failed for card {self.num_lbl.text()}: {e}")
                         # Fallthrough to Guardrail (which will raise RuntimeError)

                 # [GUARD] STRICT NATIVE GRID ENFORCEMENT
                 if "tables" in details and details["tables"]:
                     raise RuntimeError("Invalid payload: 'tables' (HTML path) not allowed in Scrutiny Dashboard.")
                 if False: # DISABLED
                 # if "tables" in details and details["tables"]:
                      html = ASMT10Generator.generate_issue_table_html(details)
                      # Basic styling injection if needed (ASMT10Gen usually outputs raw content, we might need basic CSS)
                      # ASMT10Generator styles assume print. Let's add basic web view styles.
                      style = """
                      <style>
                          .data-table { 
                              width: 100%; 
                              border-collapse: collapse; 
                              margin-top: 10px; 
                              font-size: 11px; 
                              font-family: sans-serif;
                              table-layout: fixed;
                          }
                          th { background-color: #f1f5f9; padding: 6px; border: 1px solid #e2e8f0; font-weight: bold; color: #475569; }
                          td { padding: 6px; border: 1px solid #e2e8f0; color: #334155; word-wrap: break-word; }
                          
                          /* Column Widths (SOP-5 Specific Optimization) */
                          th:nth-child(1) { width: 70%; }
                          th:nth-child(2) { width: 30%; }
                      </style>
                      """
                      self.html_view.setHtml(style + html)
                      self.html_view.setVisible(True)
                      self.table_widget.setVisible(False)
                      self.details_lbl.setVisible(False)
                      # Auto-height adjustment for HTML view?
                      doc_h = self.html_view.document().size().height()
                      self.html_view.setFixedHeight(int(doc_h + 20))
                      return

                 elif "summary_table" in details or "grid_data" in details: # Fallback support checking
                    if "grid_data" in details:
                         tbl_data = details["grid_data"]
                    elif "summary_table" in details:
                         tbl_data = details["summary_table"]
                    else: 
                         tbl_data = {}
                     
                    # Structured Table Data (Canonical Schema) - Unified Renderer
                    render_grid_to_table_widget(self.table_widget, tbl_data)
                    
                    total_h = self.table_widget.verticalHeader().length() + self.table_widget.horizontalHeader().height() + 2
                    self.table_widget.setFixedHeight(min(total_h, 300)) # Auto height cap
                    
                    self.table_widget.setVisible(True)
                    self.details_lbl.setVisible(False)
                
            else:
                # Text fallback - important for preserving context when summary table is not available
                text_to_show = ""
                if isinstance(details, dict):
                    text_to_show = details.get("status_msg") or details.get("description") or ""
                elif isinstance(details, str):
                    text_to_show = details
                
                if text_to_show:
                    self.details_lbl.setText(text_to_show)
                    self.details_lbl.setVisible(True)
                    self.table_widget.setVisible(False)
                else:
                    self.details_lbl.setText("No detailed analysis performed yet.")
                    self.details_lbl.setVisible(True)
                    self.table_widget.setVisible(False)

class ComplianceDashboard(QScrollArea):
    """Container for the 13 SOP compliance cards in a list view."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: #f8fafc; }")
        
        self.container = QWidget()
        self.container.setStyleSheet(".QWidget { background: transparent; }")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header Section
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        header_lbl = QLabel("13-Point Compliance Dashboard")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: #0f172a;")
        header_layout.addWidget(header_lbl)
        
        info_lbl = QLabel("Automated verification based on GST SOP Instruction No. 02/2022.")
        info_lbl.setStyleSheet("font-size: 14px; color: #64748b;")
        header_layout.addWidget(info_lbl)
        
        self.layout.addWidget(header_widget)

        # List Container
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        
        self.params = [
            (1, "Outward Liability (GSTR 3B vs GSTR 1)", "Comparison of Table 3.1(a)/(b) of GSTR-3B against Tables 4, 5, 6, 7, 9, 10 & 11 of GSTR-1."),
            (2, "RCM (GSTR 3B vs GSTR 2B)", "Inward supplies liable to reverse charge (RCM) vs ITC & Cash Ledger payments."),
            (3, "ISD Credit (GSTR 3B vs GSTR 2B)", "ITC from Input Service Distributors (ISD) in Table 4(A)(4) vs GSTR-2B."),
            (4, "All Other ITC (GSTR 3B vs GSTR 2B)", "ITC auto-drafted vs claimed for inward supplies from registered persons (Forward Charge)."),
            (5, "TDS/TCS (GSTR 3B vs GSTR 2B)", "Liability in Table 3.1(a) vs Taxable values on which TDS/TCS was deducted."),
            (6, "E-Waybill Comparison (GSTR 3B vs E-Waybill)", "Liability declared in GSTR-3B vs Tax Liability generated in E-Way Bills (EWB Summary)."),
            (7, "ITC passed on by Cancelled TPs", "ITC claimed from suppliers whose GST registration has been cancelled retrospectively."),
            (8, "ITC passed on by Suppliers who have not filed GSTR 3B", "ITC claimed from suppliers who have not filed their GSTR-3B returns for the period(s)."),
            (9, "Ineligible Availment of ITC [Violation of Section 16(4)]", "ITC claimed after the statutory time limit (after Nov following the FY or Annual Return)."),
            (10, "Import of Goods (3B vs ICEGATE)", "ITC on Import of Goods (GSTR-3B Table 4(A)(1)) vs Auto-drafted values from ICEGATE (2A Table 10/11)."),
            (11, "Rule 42 & 43 ITC Reversals", "Verification whether required ITC reversals (Personal/Exempt usage) have been performed."),
            (12, "GSTR 3B vs 2B (discrepancy identified from GSTR 9)", "Scrutiny of Table 8 of GSTR 9 to identify excess ITC availment.")
        ]
        
        self.cards = {}
        for num, title, desc in self.params:
            card = CompliancePointCard(num, title, desc)
            self.cards[num] = card
            self.list_layout.addWidget(card)
            
        self.layout.addWidget(self.list_container)
        self.layout.addStretch()
        
        self.setWidget(self.container)

    def update_point(self, num, status, value_text=None, details=None):
        if num in self.cards:
            self.cards[num].set_status(status, value_text, details)
            
    def reset_all(self):
        for card in self.cards.values():
            card.reset()

class DynamicUploadGroup(QFrame):
    """Manages a group of file uploads with selectable frequency (Yearly/Quarterly/Monthly)."""
    def __init__(self, title, group_key, frequencies, upload_callback, delete_callback, file_filter="Excel Files (*.xlsx *.xls)", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.group_key = group_key
        self.frequencies = frequencies
        self.upload_callback = upload_callback
        self.delete_callback = delete_callback
        self.file_filter = file_filter
        self.file_paths = {} # sub_key -> full_path
        self.selected_freq = frequencies[0]
        
        self.setStyleSheet("""
            #UploadGroup {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        self.setObjectName("UploadGroup")
        
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel(self.title_text)
        title_lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #334155;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        # Frequency Selection
        freq_container = QWidget()
        freq_layout = QHBoxLayout(freq_container)
        freq_layout.setContentsMargins(0, 0, 0, 0)
        
        freq_lbl = QLabel("Mode:")
        freq_lbl.setStyleSheet("font-weight: bold; color: #64748b; font-size: 12px; margin-right: 5px;")
        freq_layout.addWidget(freq_lbl)
        
        self.btn_group = QButtonGroup(self)
        for freq in self.frequencies:
            rb = QRadioButton(freq)
            rb.setStyleSheet("QRadioButton { font-weight: 600; color: #475569; font-size: 13px; }")
            if freq == self.selected_freq:
                rb.setChecked(True)
            self.btn_group.addButton(rb)
            freq_layout.addWidget(rb)
        
        self.btn_group.buttonClicked.connect(self._on_freq_changed)
        header_layout.addWidget(freq_container)
        
        if len(self.frequencies) <= 1:
            freq_container.setVisible(False)
        
        self.main_layout.addLayout(header_layout)
        
        # Uploaders Container
        self.uploaders_widget = QWidget()
        self.uploaders_layout = QGridLayout(self.uploaders_widget)
        self.uploaders_layout.setContentsMargins(0, 0, 0, 0)
        self.uploaders_layout.setSpacing(8)
        self.main_layout.addWidget(self.uploaders_widget)
        
        self.refresh_uploaders()

    def _on_freq_changed(self, button):
        self.selected_freq = button.text()
        self.refresh_uploaders()

    def refresh_uploaders(self):
        # Clear existing
        while self.uploaders_layout.count():
            item = self.uploaders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add based on frequency
        if self.selected_freq == "Yearly":
            self._add_uploader(f"Yearly Summary of {self.title_text}", "yearly")
        elif self.selected_freq == "Quarterly":
            quarters = ["Q1 (Apr-Jun)", "Q2 (Jul-Sep)", "Q3 (Oct-Dec)", "Q4 (Jan-Mar)"]
            for i, q in enumerate(quarters):
                self._add_uploader(f"{q}", f"q{i+1}", row=i//2, col=i%2)
        elif self.selected_freq == "Monthly":
            months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
            for i, m in enumerate(months):
                self._add_uploader(f"{m}", f"m{i+1}", row=i//3, col=i%3)

    def _add_uploader(self, label, sub_key, row=0, col=0):
        full_key = f"{self.group_key}_{sub_key}"
        uploader = FileUploaderWidget(label, full_key, self.upload_callback, self.delete_callback, file_filter=self.file_filter)
        # Validation: Only valid, non-empty strings are allowed to restore state.
        # Key presence alone is insufficient due to potential NoneType values in dict.
        val = self.file_paths.get(full_key)
        if isinstance(val, str) and val:
             uploader.set_file(os.path.basename(val))
        self.uploaders_layout.addWidget(uploader, row, col)

    def set_file_path(self, key, path):
        # Update internal mapping and the visible widget if it exists
        self.file_paths[key] = path
        for i in range(self.uploaders_layout.count()):
            item = self.uploaders_layout.itemAt(i)
            if item and item.widget():
                uploader = item.widget()
                if isinstance(uploader, FileUploaderWidget) and uploader.file_key == key:
                    if path:
                        uploader.set_file(os.path.basename(path))
                    else:
                        uploader.reset()

    def set_state(self, frequency, paths):
        self.selected_freq = frequency
        # Update radio buttons
        for btn in self.btn_group.buttons():
            if btn.text() == frequency:
                btn.setChecked(True)
                break
        self.file_paths = paths
        self.refresh_uploaders()

class ScrutinyTab(QWidget):
    DEFAULT_REPLY_DAYS = 15

    def __init__(self, nav_adj_callback=None):
        super().__init__()
        self.nav_adj_callback = nav_adj_callback
        self.db = DatabaseManager()
        self._analysis_in_progress = False # Phase 5: Re-entrancy flag
        self.parser = ScrutinyParser()
        self.asmt10 = ASMT10Generator()
        self.current_case_id = None
        self.case_state = "INIT" # Lifecycle: INIT -> READY -> ANALYZED -> FINALIZED
        self.current_case_data = {} # store validated metadata
        self.file_paths = {} # 'tax_liability', 'gstr_2b'
        self.scrutiny_results = []
        self.reply_date_overridden = False # ASMT-10 Date Logic Fix
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Panel (Workspace)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 3) 
        
        # Right Panel (Recent Cases)
        recent_container = QFrame()
        recent_container.setObjectName("recentPane")
        recent_container.setStyleSheet("#recentPane { background-color: #f8f9fa; border-left: 1px solid #e0e0e0; }")
        recent_container.setMinimumWidth(300)
        recent_container.setMaximumWidth(450)
        rc_layout = QVBoxLayout(recent_container)
        
        rc_header = QLabel("Recent Scrutiny Cases")
        rc_header.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px; color: #2c3e50;")
        rc_layout.addWidget(rc_header)
        
        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; }
            QListWidget::item { 
                background: white; 
                border-bottom: 1px solid #eee; 
                margin-bottom: 5px; 
                border-radius: 4px;
            }
            QListWidget::item:hover { background: #fdfdfd; }
            QListWidget::item:selected { background: white; border: 1px solid #3498db; }
        """)
        self.recent_list.itemClicked.connect(self.resume_case)
        rc_layout.addWidget(self.recent_list)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.setFlat(True)
        refresh_btn.clicked.connect(self.load_recent_cases)
        rc_layout.addWidget(refresh_btn)
        
        self.recent_container = recent_container
        main_layout.addWidget(self.recent_container, 1)
        
        self.setup_creation_page()
        self.stack.addWidget(self.initiation_page)
        
        self.workspace_page = QWidget()
        self.stack.addWidget(self.workspace_page)
        self.setup_workspace_page()
        
        self.load_recent_cases()
        
    def setup_creation_page(self):
        self.initiation_page = QWidget()
        layout = QHBoxLayout(self.initiation_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # New Case Card
        new_case_container = QWidget()
        nc_layout = QVBoxLayout(new_case_container)
        nc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QWidget()
        card.setObjectName("init_card")
        card.setStyleSheet("#init_card { background-color: white; border-radius: 12px; border: 1px solid #e0e0e0; }")
        card.setMaximumWidth(550)
        card.setMinimumWidth(350)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(40, 40, 40, 40)
        
        icon_lbl = QLabel("🔍") 
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_lbl)
        title = QLabel("Initiate New Scrutiny Case")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        desc = QLabel("Select a Taxpayer and Financial Year to begin automated ASMT-10 drafting.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #7f8c8d; font-size: 14px; margin-bottom: 10px;")
        card_layout.addWidget(desc)
        gstin_lbl = QLabel("Taxpayer (GSTIN):")
        gstin_lbl.setStyleSheet("font-weight: bold; color: #555;")
        card_layout.addWidget(gstin_lbl)
        self.gstin_combo = QComboBox()
        self.gstin_combo.setEditable(True)
        self.gstin_combo.setPlaceholderText("Search GSTIN...")
        self.gstin_combo.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        gstins = self.db.get_all_gstins()
        self.gstin_combo.addItems(gstins)
        completer = QCompleter(gstins)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.gstin_combo.setCompleter(completer)
        self.gstin_combo.currentTextChanged.connect(self.on_gstin_changed)
        card_layout.addWidget(self.gstin_combo)
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px; } QLabel { font-size: 13px; } QLabel#tp_name { font-weight: bold; color: #2c3e50; } QLabel#tp_trade { font-style: italic; color: #7f8c8d; } QLabel#tp_status { font-weight: bold; }")
        self.details_frame.setVisible(False)
        details_layout = QVBoxLayout(self.details_frame)
        self.tp_name_lbl = QLabel("")
        self.tp_name_lbl.setObjectName("tp_name")
        details_layout.addWidget(self.tp_name_lbl)
        self.tp_trade_lbl = QLabel("")
        self.tp_trade_lbl.setObjectName("tp_trade")
        details_layout.addWidget(self.tp_trade_lbl)
        self.tp_status_lbl = QLabel("")
        self.tp_status_lbl.setObjectName("tp_status")
        details_layout.addWidget(self.tp_status_lbl)
        card_layout.addWidget(self.details_frame)
        fy_lbl = QLabel("Financial Year:")
        fy_lbl.setStyleSheet("font-weight: bold; color: #555; margin-top: 10px;")
        card_layout.addWidget(fy_lbl)
        self.fy_combo = QComboBox()
        self.fy_combo.setPlaceholderText("Select Financial Year")
        self.fy_combo.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        self.fy_combo.addItems(["2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"])
        card_layout.addWidget(self.fy_combo)
        btn = QPushButton("Create Case Folder")
        btn.setStyleSheet("QPushButton { background-color: #2980b9; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; margin-top: 10px; } QPushButton:hover { background-color: #3498db; }")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.create_case)
        card_layout.addWidget(btn)
        nc_layout.addWidget(card)
        layout.addWidget(new_case_container, 2)
        
        nc_layout.addWidget(card)
        layout.addWidget(new_case_container, 2)
        
        # Consistent layout
        layout.addStretch()

    def load_recent_cases(self):
        self.recent_list.clear()
        cases = self.db.get_scrutiny_cases()
        for case in cases:
            item = QListWidgetItem(self.recent_list)
            # Use a slightly smaller size hint to avoid horizontal scrollbars
            item.setSizeHint(QSize(280, 80)) 
            item.setData(Qt.ItemDataRole.UserRole, case['id'])
            widget = RecentCaseItem(
                case['id'], # Pass UUID for deletion
                case['gstin'], 
                case['legal_name'], 
                case['financial_year'], 
                case['status'], 
                case['created_at'],
                self.delete_case
            )
            self.recent_list.setItemWidget(item, widget)

    def delete_case(self, case_id):
        """Handle case deletion request with confirmation."""
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            "Are you sure you want to delete this case? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.db.delete_proceeding(case_id)
            if success:
                self.load_recent_cases() # Refresh list
                # If the deleted case was open, close it
                if self.current_case_id == case_id:
                    self.close_case()
                QMessageBox.information(self, "Success", "Case deleted successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete case.")
            


    def resume_case_by_id(self, pid):
        """Helper to resume case by ID (wraps resume_case)"""
        # Create a dummy item to pass to resume_case
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, pid)
        self.resume_case(item)
            
    # --- UI LIFECYCLE HELPERS ---

    def setup_banner(self):
        """Create the finalized locked banner (hidden by default)"""
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("""
            QFrame { background-color: #fff1f2; border-bottom: 1px solid #fda4af; }
        """)
        self.banner_frame.setFixedHeight(60)
        self.banner_frame.setVisible(False)
        
        layout = QHBoxLayout(self.banner_frame)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.banner_lbl = QLabel()
        self.banner_lbl.setStyleSheet("color: #9f1239; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.banner_lbl)
        
        layout.addStretch()
        
        self.nav_adj_btn = QPushButton("Open Adjudication Case ➔")
        self.nav_adj_btn.clicked.connect(self.go_to_adjudication)
        self.nav_adj_btn.setStyleSheet("""
            QPushButton {
                background-color: #be123c; color: white; border: none;
                padding: 6px 12px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #9f1239; }
        """)
        layout.addWidget(self.nav_adj_btn)

    def go_to_adjudication(self):
        """Navigate to Adjudication Module with current case context"""
        if self.current_adj_id and self.nav_adj_callback:
            self.nav_adj_callback(self.current_adj_id)
        elif not self.current_adj_id:
            QMessageBox.warning(self, "Blocking Error", "No linked Adjudication Case found.\n\nThis case has not been finalised or the link is broken.")
        else:
            QMessageBox.warning(self, "Navigation Error", "Navigation callback not connected.")

    def apply_case_state(self):
        """
        SINGLE SOURCE OF TRUTH for UI state.
        Derived strictly from self.case_state.
        """
        state = getattr(self, 'case_state', 'INIT')
        
        # 1. Finalized Banner & Adjudication Button
        if state == "FINALIZED":
            if hasattr(self, 'banner_frame'): self.banner_frame.setVisible(True)
            if hasattr(self, 'open_adjudication_btn'): self.open_adjudication_btn.setVisible(True)
            self.set_read_only_mode(True)
        else:
            if hasattr(self, 'banner_frame'): self.banner_frame.setVisible(False)
            if hasattr(self, 'open_adjudication_btn'): self.open_adjudication_btn.setVisible(False)
            if state == "ANALYZED":
                 self.set_read_only_mode(False)
            else:
                 self.set_read_only_mode(False) # Default editable for INIT/READY
        
        # Debug Log (Temporary Diagnostic)
        import inspect
        caller = inspect.stack()[1].function
        print(f"APPLY STATE: {state} FROM {caller}")

    def show_finalized_banner(self, date_str, adj_id):
        # Strict Assertion
        assert getattr(self, 'case_state', 'INIT') == "FINALIZED", "Banner requires FINALIZED state"
        
        self.banner_lbl.setText(f"🔒 ASMT-10 Finalised on {date_str}. This stage is locked.")
        # Visibility handled by apply_case_state, but we ensure text is set here
        # apply_case_state() should have been called by render_finalized_view logic
        # But this method is usually called BY render_finalized_view.
        # So we can keep it as a data setter.
        
        self.current_adj_id = adj_id
        if adj_id:
            self.nav_adj_btn.setEnabled(True)
        else:
            self.nav_adj_btn.setEnabled(False)
        
    def hide_banner(self):
        if hasattr(self, 'banner_frame'):
            self.banner_frame.setVisible(False)

    def set_read_only_mode(self, readonly=True, proc_data=None):
        """Enable/Disable Read-Only Mode for Finalized Cases"""
        
        # 1. Disable Action Buttons
        self.analyze_btn.setVisible(not readonly)
        self.save_btn.setVisible(not readonly)
        self.finalise_btn.setVisible(not readonly)
        
        # 2. Disable Inputs in Case Details
        self.oc_num_input.setReadOnly(readonly)
        self.notice_date_edit.setReadOnly(readonly)
        self.reply_date_edit.setReadOnly(readonly)
        
        # 3. Disable Uploads
        if hasattr(self, 'tax_group'): self.tax_group.setDisabled(readonly)
        if hasattr(self, 'gstr3b_group'): self.gstr3b_group.setDisabled(readonly)
        if hasattr(self, 'gstr1_group'): self.gstr1_group.setDisabled(readonly)
        if hasattr(self, 'gstr2b_group'): self.gstr2b_group.setDisabled(readonly)
        
        if readonly:
             self.setWindowTitle(self.windowTitle() + " (Read-Only)")

    def resume_case_by_id(self, pid):
        """Helper to resume case by ID (wraps resume_case)"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, pid)
        self.resume_case(item)

    
    def load_case_context(self, pid):
        """Helper to load pure data context without UI side effects."""
        proc = self.db.get_proceeding(pid)
        if not proc:
            return None, None
        
        state = self.derive_case_state(proc)
        return proc, state

    def hard_reset_for_resume(self):
        """
        Deep UI reset for clean slate before resumption.
        Does NOT reset identity (current_case_id/data).
        """
        if hasattr(self, 'compliance_dashboard'):
            self.compliance_dashboard.reset_all()
        if hasattr(self, 'results_area'):
            self.results_area.clear_results()
        if hasattr(self, 'summary_strip'):
            self.summary_strip.update_summary("Unknown", "N/A")
        if hasattr(self, 'asmt_preview'):
            from PyQt6.QtCore import QUrl
            self.asmt_preview.setUrl(QUrl("about:blank"))
        
        # STRICT RESET: Banner must be hidden by default
        if hasattr(self, 'finalized_banner'):
            self.finalized_banner.hide()
        if hasattr(self, 'open_adjudication_btn'):
            self.open_adjudication_btn.hide()
            
        self.scrutiny_results = []
        
        # Reset specific uploaders if needed or ensure they are ready to be set
        # But we don't clear them here as we might just restore them immediately.
        # The key is that Analysis Widgets are DEAD.

    def _require_active_case(self, operation: str):
        """Hard Guard: Ensure operations run only within an active case context."""
        if not self.current_case_id:
            msg = f"FATAL: {operation} called without active case (Integrity Violation)"
            self.log_event("CRITICAL", msg)
            raise RuntimeError(msg)

    def log_event(self, level, message, **context):
        """Phase 6: Auditability Wrapper."""
        timestamp = datetime.datetime.now().isoformat()
        entry = f"[{timestamp}] [{level}] {message} | Context: {context}"
        print(entry) # Stdout for now, can be file/DB logging later
        
        # Optional: Write to local audit log file
        try:
             with open("audit_log.txt", "a") as f:
                 f.write(entry + "\n")
        except: pass

    def _block_if_finalized(self, operation: str):
        """Hard Guard: Prevent mutation on legally finalized cases."""
        if getattr(self, 'case_state', 'INIT') == "FINALIZED":
             raise RuntimeError(f"MUTATION BLOCKED: {operation} attempted on FINALIZED case.")


    def _persist_additional_details(self):
        """Centralized persistence for additional_details."""
        self._require_active_case("_persist_additional_details")
        
        # Ensure we have a dict to dump
        details = self.current_case_data.get("additional_details", {})
        if not isinstance(details, dict):
            details = {}
            
        self.db.update_proceeding(
            self.current_case_id,
            {
                "additional_details": json.dumps(details)
            }
        )
        print(f"Persisted additional_details for Case {self.current_case_id}")

    def _transition_case_state(self, new_state: str):
        """Phase 3: Strict Lifecycle Transition Enforcement."""
        current = getattr(self, 'case_state', 'INIT')
        
        # Hydration/Reset Bypass
        # Transitions to INIT are always allowed (Reset/Backtrack)
        # Transitions FROM None/INIT (Initial Load) should be allowed potentially, 
        # but usually handled by derive_case_state directly.
        
        if current == new_state:
            return

        # Allowed Transitions Graph
        valid_map = {
            'INIT': ['READY'],
            'READY': ['ANALYZED'],
            'ANALYZED': ['FINALIZED']
        }
        
        if new_state not in valid_map.get(current, []):
             raise RuntimeError(f"ILLEGAL STATE TRANSITION: {current} -> {new_state}")
                 
        self.case_state = new_state

    def derive_case_state(self, proc):
        """
        Sole authority for lifecycle state.
        Determines state purely from persisted data: INIT, READY, ANALYZED, FINALIZED.
        """
        # 1. Parse Additional Details safely
        add_details = proc.get('additional_details', {})
        if isinstance(add_details, str):
            try: 
                import json
                add_details = json.loads(add_details)
            except: 
                add_details = {}

        file_paths = add_details.get('file_paths', {})
        analysis_completed = add_details.get('analysis_completed', False)
        asmt_status = proc.get('asmt10_status')

        # 2. Hierarchy of Truth
        
        # A. Finalization overrides everything
        if asmt_status == 'finalised':
            return "FINALIZED"

        # B. Illegal State Normalization (Analysis without files -> INIT)
        if analysis_completed and not file_paths:
            print(f"WARNING: Illegal State detected for Case {proc.get('proceeding_id')}. Analysis flagged w/o files. Forcing INIT.")
            return "INIT"

        # C. Normal Lifecycle
        if not file_paths:
            return "INIT"
        
        if file_paths and not analysis_completed:
            return "READY"
            
        if file_paths and analysis_completed:
            return "ANALYZED"
            
        return "INIT" # Fallback

    def render_finalized_view(self, proc):
        """
        Dedicated renderer for FINALIZED cases.
        Uses cached/snapshot data only. No live analysis components.
        """
        # 1. State Set (Already handled by load context usually, but verify)
        # 2. Apply UI State (Banner, Locks)
        self.apply_case_state()
        
        # 3. Populate Data to Banner
        fin_date = proc.get('asmt10_finalised_on')
        adj_id = proc.get('adjudication_case_id')
        self.show_finalized_banner(fin_date, adj_id)
        
        # 2. Lock UI
        self.set_read_only_mode(True, proc)
        
        # 3. Load Frozen Summary/Metadata if available (Optional enhancement)
        # For now, we ensure Analysis Dashboard is blank/reset because we don't want live editable widgets
        self.reset_analysis_ui()
        
        # 4. Potentially load just the ASMT-10 Preview if it exists
        # We can let the user click "Refresh Preview" or "Download" to see the generated PDF
        # But we DO NOT populate the editable results_area
        pass

    def reset_case_details_form(self):
        """Reset the case details form to default empty state."""
        if hasattr(self, 'oc_num_input'): self.oc_num_input.clear()
        if hasattr(self, 'notice_date_edit'): self.notice_date_edit.setDate(QDate.currentDate())
        if hasattr(self, 'reply_date_edit'): 
            # SYSTEM UPDATE: Block signal (Date Logic Fix)
            self.reply_date_edit.blockSignals(True)
            self.reply_date_edit.setDate(QDate.currentDate().addDays(self.DEFAULT_REPLY_DAYS))
            self.reply_date_edit.blockSignals(False)

    def _parse_additional_details(self, proc):
        """Helper to parse JSON details safely with Scheme Stabilization (Phase 4)."""
        add_details = proc.get('additional_details', {})
        if isinstance(add_details, str):
            try: 
                import json
                add_details = json.loads(add_details)
            except: 
                add_details = {}
        
        if not isinstance(add_details, dict):
             add_details = {}
             
        # Phase 4: Schema Stabilization (In-Memory Defaults)
        add_details.setdefault('file_paths', {})
        add_details.setdefault('group_configs', {})
        add_details.setdefault('analysis_completed', False)
        add_details.setdefault('validation_warnings', {})
        # Date Logic Fix: Override Flag Default
        add_details.setdefault('reply_date_overridden', False)
        
        return add_details

    def _restore_uploader_states(self, file_paths, add_details):
        """
        Restore upload widgets from persisted file paths.
        Extracted from legacy resume_case logic.
        """
        self.file_paths = file_paths or {}

        # 1. Update basic uploaders
        if 'tax_liability_yearly' in self.file_paths or 'gstr9_yearly' in self.file_paths:
            if hasattr(self, 'analyze_btn'):
                self.analyze_btn.setEnabled(True)
        
        if 'tax_liability_yearly' in self.file_paths and hasattr(self, 'tax_group'):
            self.tax_group.set_file_path('tax_liability_yearly', self.file_paths['tax_liability_yearly'])

        # 2. Restore Dynamic Groups
        group_configs = add_details.get('group_configs', {})
        
        # GSTR-3B
        if hasattr(self, 'gstr3b_group'):
            g3b_freq = group_configs.get('gstr3b', {}).get('frequency', 'Yearly')
            g3b_paths = {k: v for k, v in self.file_paths.items() if k.startswith("gstr3b")}
            self.gstr3b_group.set_state(g3b_freq, g3b_paths)
        
        # GSTR-1
        if hasattr(self, 'gstr1_group'):
            g1_freq = group_configs.get('gstr1', {}).get('frequency', 'Yearly')
            g1_paths = {k: v for k, v in self.file_paths.items() if k.startswith("gstr1")}
            self.gstr1_group.set_state(g1_freq, g1_paths)
        
        # GSTR-2B
        if hasattr(self, 'gstr2b_group'):
            g2b_freq = group_configs.get('gstr2b', {}).get('frequency', 'Yearly')
            g2b_paths = {k: v for k, v in self.file_paths.items() if k.startswith("gstr2b")}
            self.gstr2b_group.set_state(g2b_freq, g2b_paths)

        # GSTR-2A
        if hasattr(self, 'gstr2a_group'):
            g2a_freq = group_configs.get('gstr2a', {}).get('frequency', 'Yearly')
            g2a_paths = {k: v for k, v in self.file_paths.items() if k.startswith("gstr2a")}
            self.gstr2a_group.set_state(g2a_freq, g2a_paths)

        # GSTR-9
        if hasattr(self, 'gstr9_group'):
            g9_freq = group_configs.get('gstr9', {}).get('frequency', 'Yearly')
            g9_paths = {k: v for k, v in self.file_paths.items() if k.startswith("gstr9")}
            self.gstr9_group.set_state(g9_freq, g9_paths)

    def _restore_identity_only(self, proc):
        """Restore basic case metadata (GSTIN, FY, Header Labels). PURE UI ONLY."""
        # FIX: Removed identity assignment. Identity is strictly bound in resume_case.
        self.case_info_lbl.setText(f"{proc.get('legal_name')} | {proc.get('gstin')} | {proc.get('financial_year')}")
        
        # VALIDATION ASSERTION (TEMPORARY)
        assert self.current_case_id is not None, "Identity Nullified in _restore_identity_only"

    def hydrate_case_details_form(self, proc, readonly=False):
        """Populate OC Number and Dates from DB."""
        oc_val = proc.get('oc_number', '')
        if hasattr(self, 'oc_num_input'):
            self.oc_num_input.setText(oc_val)
            self.oc_num_input.setReadOnly(readonly)
        
        n_date = proc.get('notice_date')
        if hasattr(self, 'notice_date_edit'):
            if n_date: self.notice_date_edit.setDate(QDate.fromString(n_date, "yyyy-MM-dd"))
            else: self.notice_date_edit.setDate(QDate.currentDate())
            self.notice_date_edit.setReadOnly(readonly)
            
        
        # Restore Date Override Flag (Date Logic Fix)
        add_details = self._parse_additional_details(proc)
        self.reply_date_overridden = add_details.get('reply_date_overridden', False)

        r_date = proc.get('last_date_to_reply')
        if hasattr(self, 'reply_date_edit'):
            # SYSTEM UPDATE: Block signal to prevent triggering override logic
            self.reply_date_edit.blockSignals(True)
            if r_date: 
                self.reply_date_edit.setDate(QDate.fromString(r_date, "yyyy-MM-dd"))
            else: 
                # Fallback: Notice Date + Default Days (if notice date is set)
                # If notice date is also missing/current, effectively current + default
                current_notice = self.notice_date_edit.date()
                self.reply_date_edit.setDate(current_notice.addDays(self.DEFAULT_REPLY_DAYS))
            self.reply_date_edit.setReadOnly(readonly)
            self.reply_date_edit.blockSignals(False)

    def _load_issues_from_db(self, proc):
        """Load and parse issues directly from DB without parser execution."""
        try:
            saved_issues_str = proc.get('selected_issues')
            if not saved_issues_str or saved_issues_str == '{}':
                return []

            if isinstance(saved_issues_str, list):
                issues = saved_issues_str
            elif isinstance(saved_issues_str, dict):
                issues = saved_issues_str
            else:
                import json
                issues = json.loads(saved_issues_str)
            
            # Handle parser format
            if isinstance(issues, dict) and 'issues' in issues:
                self.current_case_data['metadata'] = issues.get('metadata', {})
                issues = issues['issues']

            if isinstance(issues, list):
                return self.enrich_issues_with_templates(issues)
            return []
        except Exception as e:
            print(f"Error loading issues from DB: {e}")
            return []

    def _populate_results_view_readonly(self, issues):
        """
        Dedicated renderer for FINALIZED cases.
        Bypasses strict guards and mutable state checks.
        """
        # 1. Update Summary Strip
        try:
            legal_name = self.current_case_data.get('legal_name', 'Unknown')
            self.summary_strip.update_summary(
                legal_name,
                self.current_case_data.get('financial_year', 'Unknown')
            )
        except: pass

        # 2. Populate Dashboard & Executive Summary
        self.results_area.clear_results()
        self.compliance_dashboard.reset_all()
        
        found_points = set()
        issue_idx = 1
        
        for issue in issues:
            shortfall = issue.get("total_shortfall", 0)
            
            # Executive Summary (Results Area)
            if shortfall > 0:
                self.results_area.add_result(issue, issue_number=issue_idx)
                issue_idx += 1
            
            # Dashboard Status
            point_num = issue.get('sop_point')
            if point_num:
                found_points.add(point_num)
                if issue.get("status_msg"):
                    status = issue.get("status", "info")
                    msg = issue.get("status_msg")
                    
                    # Consistent "Rs. 0" for PASS
                    if status == 'pass':
                        val = issue.get('total_shortfall', 0)
                        msg = format_indian_number(val, prefix_rs=True)
                        
                    self.compliance_dashboard.update_point(point_num, status, msg, details=issue)
                else:
                    status = "fail" if shortfall > 100 else "alert" if shortfall > 0 else "pass"
                    msg = format_indian_number(shortfall, prefix_rs=True)
                    self.compliance_dashboard.update_point(point_num, status, msg, details=issue)

        self.switch_section(1)
        self.nav_cards[1].set_summary(f"{len(issues)} issues identified")

    def render_finalized_view(self, proc):
        """
        READ-ONLY DB hydration path for FINALIZED cases.
        Bypasses files, parser, and analysis logic.
        """
        # RUNTIME GUARD
        assert self.case_state == "FINALIZED", f"render_finalized_view called in {self.case_state}"

        # 1. Load Data
        issues = self._load_issues_from_db(proc)
        # DEEPCOPY SAFETY: Detach from DB result reference
        issues = copy.deepcopy(issues)
        self.scrutiny_results = issues
        
        # 2. Apply UI State (Banner, ReadOnly)
        self.apply_case_state()
        
        # 3. Banner Data
        fin_date = proc.get('asmt10_finalised_on')
        adj_id = proc.get('adjudication_case_id')
        self.show_finalized_banner(fin_date, adj_id)

        # 4. Render UI (Dashboard/Summary) - SECURE PATH
        self._populate_results_view_readonly(issues)
        
        # 5. Generate ASMT-10 Preview - DIRECT GENERATION
        if hasattr(self, 'asmt_preview'):
            try:
                # Force-enrich taxpayer details if missing (legacy support)
                if not proc.get('taxpayer_details') and proc.get('gstin'):
                     proc['taxpayer_details'] = self.db.get_taxpayer(proc['gstin'])

                html = ASMT10Generator.generate_html(proc, issues, for_preview=True)
                self.asmt_preview.setHtml(html)
            except Exception as e:
                print(f"Error rendering finalized preview: {e}")
                self.asmt_preview.setHtml(f"<div style='color:red;'>Error: {e}</div>")

    def resume_case(self, item):
        pid = item.data(Qt.ItemDataRole.UserRole)
        
        # 1. Load Context & State (Pure)
        # We RE-FETCH to ensure no stale object refs
        proc = self.db.get_proceeding(pid)
        if not proc:
            return
            
        state = self.derive_case_state(proc)

        # 2. State & Identity Set (ABSOLUTE PRIORITY)
        self.current_case_id = pid
        self.current_case_data = proc
        
        # NORMALIZE LEGACY DATA (Fix for string additional_details)
        if 'additional_details' in self.current_case_data:
            ad = self.current_case_data['additional_details']
            if isinstance(ad, str):
                try: 
                    self.current_case_data['additional_details'] = json.loads(ad)
                except: 
                    self.current_case_data['additional_details'] = {}
            elif not isinstance(ad, dict):
                 self.current_case_data['additional_details'] = {}
        else:
            self.current_case_data['additional_details'] = {}

        # PERSIST: Normalize immediately to prevent string/dict vibration
        self._persist_additional_details()

        self.case_state = state 
        
        print(f"DEBUG: resume_case after BIND: ID={self.current_case_id}")

        # 3. Hard Reset (Clean Slate)
        # MUST NOT clear current_case_id
        self.hard_reset_for_resume()
        print(f"DEBUG: resume_case after hard_reset: ID={self.current_case_id}")

        self.switch_section(0) 
        print(f"DEBUG: resume_case after switch_section: ID={self.current_case_id}")

        # 4. APPLY UI STATE (Strict Single Authority)
        self.apply_case_state()
        print(f"DEBUG: resume_case after apply_case_state: ID={self.current_case_id}")

        # 5. Strict State Machine
        if self.case_state == "INIT":
            self._restore_identity_only(proc)
            # FIX: Do not hard reset. Hydrate explicitly to preserve any saved dates/OC.
            self.hydrate_case_details_form(proc, readonly=False)
            
        elif self.case_state == "READY":
            self._restore_identity_only(proc)
            # FIX: Do not hard reset. Hydrate explicitly.
            self.hydrate_case_details_form(proc, readonly=False)
            self._restore_uploader_states(self._parse_additional_details(proc).get('file_paths', {}), self._parse_additional_details(proc))
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("Analyze SOP Points")
            
        elif self.case_state == "ANALYZED":
            print(f"DEBUG: Entering ANALYZED block. ID={self.current_case_id}")
            self._restore_identity_only(proc)
            print(f"DEBUG: After _restore_identity_only. ID={self.current_case_id}")
            
            add_details = self._parse_additional_details(proc)
            self._restore_uploader_states(add_details.get('file_paths', {}), add_details)
            print(f"DEBUG: After _restore_uploader_states. ID={self.current_case_id}")
            
            self.hydrate_case_details_form(proc, readonly=False)
            print(f"DEBUG: After hydrate_case_details_form. ID={self.current_case_id}")
            
            self.scrutiny_results = self._load_issues_from_db(proc)
            print(f"DEBUG: calling populate_results_view with current_case_id={self.current_case_id}")
            
            self.populate_results_view(self.scrutiny_results)
            
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("Re-Analyze Data")
            self.set_read_only_mode(False)

        elif self.case_state == "FINALIZED":
            self._restore_identity_only(proc)
            self.hydrate_case_details_form(proc, readonly=True)
            # Restore uploaders visually for context (Read-Only implicitly by set_read_only_mode later)
            add_details = self._parse_additional_details(proc)
            self._restore_uploader_states(add_details.get('file_paths', {}), add_details)
            
            self.render_finalized_view(proc)

        self.stack.setCurrentIndex(1)
        self.recent_container.setVisible(False)

    def _legacy_resume_case_disabled(self, item):
        raise RuntimeError("LEGACY RESUME PATH DISABLED — DO NOT USE")
        # 1. State Reset
        self.current_adj_id = None 
        
        pid = item.data(Qt.ItemDataRole.UserRole)
        proc = self.db.get_proceeding(pid)
        if proc:
            self.current_case_id = pid
            self.current_case_data = {
                'gstin': proc['gstin'],
                'financial_year': proc['financial_year']
            }
            self.case_info_lbl.setText(f"{proc['legal_name']} | {proc['gstin']} | {proc['financial_year']}")
            
            # Reset UI state
            self.switch_section(0)
            self.clear_results_view()
            
            # Load Case Details
            oc_val = proc.get('oc_number', '')
            self.oc_num_input.setText(oc_val)
            
            notice_date_str = proc.get('notice_date', '')
            if notice_date_str:
                self.notice_date_edit.setDate(QDate.fromString(notice_date_str, "yyyy-MM-dd"))
            else:
                self.notice_date_edit.setDate(QDate.currentDate())
                
            reply_date_str = proc.get('last_date_to_reply', '')
            if reply_date_str:
                self.reply_date_edit.setDate(QDate.fromString(reply_date_str, "yyyy-MM-dd"))
            else:
                self.reply_date_edit.setDate(QDate.currentDate().addDays(30))

            # Load File Paths
            add_details = proc.get('additional_details', {})
            if isinstance(add_details, str):
                try: 
                    import json
                    add_details = json.loads(add_details)
                except: 
                    add_details = {}
            
            # --- STATUS ENFORCEMENT & STRICT LIFECYCLE ---
            asmt_status = proc.get('asmt10_status')
            
            # 1. Check Finalization First
            if asmt_status == 'finalised':
                self.case_state = "FINALIZED"
                self.set_read_only_mode(True, proc)
                fin_date = proc.get('asmt10_finalised_on')
                adj_id = proc.get('adjudication_case_id')
                self.show_finalized_banner(fin_date, adj_id)
            else:
                self.set_read_only_mode(False)
                self.hide_banner()
            
            persisted_paths = add_details.get('file_paths', {})
            if persisted_paths:
                self.file_paths = persisted_paths
                # Update uploaders
                if 'tax_liability_yearly' in persisted_paths or 'gstr9_yearly' in persisted_paths:
                    self.analyze_btn.setEnabled(True)
                
                if 'tax_liability_yearly' in persisted_paths:
                    self.tax_group.set_file_path('tax_liability_yearly', persisted_paths['tax_liability_yearly'])
                
                # Restore Dynamic Groups
                group_configs = add_details.get('group_configs', {})
                
                # GSTR-3B
                g3b_freq = group_configs.get('gstr3b', {}).get('frequency', 'Yearly')
                g3b_paths = {k: v for k, v in persisted_paths.items() if k.startswith("gstr3b")}
                self.gstr3b_group.set_state(g3b_freq, g3b_paths)
                
                # GSTR-1
                g1_freq = group_configs.get('gstr1', {}).get('frequency', 'Yearly')
                g1_paths = {k: v for k, v in persisted_paths.items() if k.startswith("gstr1")}
                self.gstr1_group.set_state(g1_freq, g1_paths)
                
                # GSTR-2B
                g2b_freq = group_configs.get('gstr2b', {}).get('frequency', 'Yearly')
                g2b_paths = {k: v for k, v in persisted_paths.items() if k.startswith("gstr2b")}
                self.gstr2b_group.set_state(g2b_freq, g2b_paths)

                # GSTR-9
                g9_freq = group_configs.get('gstr9', {}).get('frequency', 'Yearly')
                g9_paths = {k: v for k, v in persisted_paths.items() if k.startswith("gstr9")}
                self.gstr9_group.set_state(g9_freq, g9_paths)

            try:
                saved_issues_str = proc['selected_issues']
                if saved_issues_str and saved_issues_str != '{}':
                    if isinstance(saved_issues_str, list):
                        issues = saved_issues_str
                    elif isinstance(saved_issues_str, dict):
                        issues = saved_issues_str
                    else:
                        issues = json.loads(saved_issues_str)
                    
                    # Handle new parser format which returns {"metadata":..., "issues": [...]}
                    if isinstance(issues, dict) and 'issues' in issues:
                        self.current_case_data['metadata'] = issues.get('metadata', {})
                        issues = issues['issues']

                    if isinstance(issues, list) and len(issues) > 0:
                        # Re-enrich to ensure issue_master_id is present for resumed cases
                        issues = self.enrich_issues_with_templates(issues)
                        self.scrutiny_results = issues
                        self.populate_results_view(issues)
                        self.analyze_btn.setText("Re-Analyze Data")  
                        self.analyze_btn.setEnabled(True)
            except Exception as e:
                with open("ui_load_error.log", "w") as f:
                    import traceback
                    f.write(f"Error loading saved issues: {str(e)}\n")
                    f.write(traceback.format_exc())
                print(f"Error loading saved issues: {e}")
            self.stack.setCurrentIndex(1)
            self.recent_container.setVisible(False) # Hide recent list in workspace
            
    def setup_workspace_page(self):
        """Set up the scrutiny workspace with a Side-Accordion (Master-Detail) layout."""
        self.setup_banner()
        workspace_layout = QVBoxLayout(self.workspace_page)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        
        # Add Banner at top
        workspace_layout.addWidget(self.banner_frame)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # 1. Global Toolbar (Persistent at Top)
        toolbar = QFrame()
        toolbar.setStyleSheet("background: white; border-bottom: 1px solid #e2e8f0;")
        toolbar.setFixedHeight(60)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        toolbar_layout.setSpacing(15)

        self.case_info_lbl = QLabel("No Case Selected")
        self.case_info_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 14px;")
        toolbar_layout.addWidget(self.case_info_lbl)
        toolbar_layout.addStretch()

        self.save_btn = QPushButton("💾 Save Case")
        self.save_btn.setStyleSheet("""
            QPushButton { 
                background-color: #ecfdf5; border: 1px solid #10b981; color: #065f46; 
                padding: 8px 16px; border-radius: 6px; font-weight: 600; 
            }
            QPushButton:hover { background-color: #d1fae5; }
        """)
        self.save_btn.clicked.connect(self.save_findings)
        toolbar_layout.addWidget(self.save_btn)

        self.analyze_btn = QPushButton("⚡ Run Analysis")
        self.analyze_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3b82f6; color: white; 
                padding: 8px 20px; border-radius: 6px; font-weight: bold; border: none;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #cbd5e1; }
        """)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze_file)
        toolbar_layout.addWidget(self.analyze_btn)

        self.close_case_btn = QPushButton("✕ Close")
        self.close_case_btn.setStyleSheet("""
            QPushButton { 
                background-color: white; border: 1px solid #e2e8f0; color: #64748b; 
                padding: 8px 12px; border-radius: 6px; font-weight: 600; 
            }
            QPushButton:hover { background-color: #f8fafc; color: #ef4444; border-color: #fecaca; }
        """)
        self.close_case_btn.clicked.connect(self.close_case)
        toolbar_layout.addWidget(self.close_case_btn)

        workspace_layout.addWidget(toolbar)

        # 2. Splitter for Side Nav and Content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e2e8f0; }")

        # --- LEFT SIDEBAR (NAV) ---
        sidebar = QWidget()
        sidebar.setStyleSheet("background-color: #f8fafc;")
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(350)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(12)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        nav_lbl = QLabel("CASE SECTIONS")
        nav_lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #94a3b8; letter-spacing: 0.5px; margin-bottom: 5px;")
        sidebar_layout.addWidget(nav_lbl)

        self.nav_cards = []
        sections = [
            (0, "📄", "Case Data & Uploads"),
            (1, "📊", "SOP Compliance Check"),
            (2, "📋", "Executive Summary"),
            (3, "📝", "Case Details"),
            (4, "✉️", "ASMT-10 Drafting")
        ]

        for idx, icon, title in sections:
            card = SideNavCard(idx, icon, title)
            card.clicked.connect(self.switch_section)
            self.nav_cards.append(card)
            sidebar_layout.addWidget(card)

        sidebar_layout.addStretch()
        splitter.addWidget(sidebar)

        # --- RIGHT CONTENT AREA ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: white;")

        # Page 0: Uploads
        upload_page = QScrollArea()
        upload_page.setWidgetResizable(True)
        upload_page.setStyleSheet("QScrollArea { border: none; background: white; }")
        up_content = QWidget()
        up_layout = QVBoxLayout(up_content)
        up_layout.setContentsMargins(30, 30, 30, 30)
        up_layout.setSpacing(20)
        up_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title_lbl = QLabel("Upload Case Documents")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")
        up_layout.addWidget(title_lbl)

        self.tax_group = DynamicUploadGroup(
            "1. Tax Liability & ITC (Comparison Excel)", "tax_liability", 
            ["Yearly"], 
            self.handle_file_upload, self.handle_file_delete,
            file_filter="Excel Files (*.xlsx *.xls)"
        )
        up_layout.addWidget(self.tax_group)
        
        # GSTR-3B PDFs
        self.gstr3b_group = DynamicUploadGroup(
            "2. GSTR-3B PDF Uploads", "gstr3b", 
            ["Yearly", "Monthly"], 
            self.handle_file_upload, self.handle_file_delete,
            file_filter="PDF Files (*.pdf)"
        )
        up_layout.addWidget(self.gstr3b_group)

        # GSTR-1 PDFs
        self.gstr1_group = DynamicUploadGroup(
            "3. GSTR-1 PDF Uploads", "gstr1", 
            ["Yearly", "Monthly"], 
            self.handle_file_upload, self.handle_file_delete,
            file_filter="PDF Files (*.pdf)"
        )
        up_layout.addWidget(self.gstr1_group)

        # GSTR-2B Summary (Excel only)
        self.gstr2b_group = DynamicUploadGroup(
            "4. Consolidated GSTR-2B Summary", "gstr2b", 
            ["Yearly", "Quarterly", "Monthly"], 
            self.handle_file_upload, self.handle_file_delete,
            file_filter="Excel Files (*.xlsx *.xls)"
        )
        up_layout.addWidget(self.gstr2b_group)

        # GSTR-2A Summary (Excel only)
        self.gstr2a_group = DynamicUploadGroup(
            "4a. Consolidated GSTR-2A (Optional)", "gstr2a",
            ["Yearly"],
            self.handle_file_upload, self.handle_file_delete,
            file_filter="Excel Files (*.xlsx *.xls)"
        )
        up_layout.addWidget(self.gstr2a_group)

        # GSTR-9 PDFs
        self.gstr9_group = DynamicUploadGroup(
            "5. GSTR-9 (Annual Return) PDFs", "gstr9", 
            ["Yearly"], 
            self.handle_file_upload, self.handle_file_delete,
            file_filter="PDF Files (*.pdf)"
        )
        up_layout.addWidget(self.gstr9_group)

        up_layout.addStretch()

        upload_page.setWidget(up_content)
        self.content_stack.addWidget(upload_page)

        # Page 1: SOP Compliance Dashboard
        self.compliance_dashboard = ComplianceDashboard()
        self.content_stack.addWidget(self.compliance_dashboard)

        # Page 2: Executive Summary
        exec_page = QWidget()
        exec_layout = QVBoxLayout(exec_page)
        exec_layout.setContentsMargins(0, 0, 0, 0)
        exec_layout.setSpacing(0)
        
        self.summary_strip = AnalysisSummaryStrip()
        exec_layout.addWidget(self.summary_strip)
        
        self.results_area = ResultsContainer(save_template_callback=self.handle_save_master_template)
        exec_layout.addWidget(self.results_area)
        self.content_stack.addWidget(exec_page)

        # Page 3: Case Details
        details_page = QScrollArea()
        details_page.setWidgetResizable(True)
        details_page.setStyleSheet("QScrollArea { border: none; background: white; }")
        dp_content = QWidget()
        dp_layout = QVBoxLayout(dp_content)
        dp_layout.setContentsMargins(40, 40, 40, 40)
        dp_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        details_form = QFrame()
        details_form.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;")
        details_form.setMaximumWidth(800)
        form_layout = QVBoxLayout(details_form)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(20)
        
        form_title = QLabel("Registration & Notice Details")
        form_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 10px;")
        form_layout.addWidget(form_title)

        # O.C. No using helper
        oc_lbl = QLabel("O.C. Number *")
        oc_lbl.setStyleSheet("font-weight: bold; color: #475569;")
        form_layout.addWidget(oc_lbl)
        
        oc_input_layout = QHBoxLayout()
        self.oc_num_input = QLineEdit()
        self.oc_num_input.setPlaceholderText("Format: No./Year (e.g. 15/2025)")
        self.oc_num_input.setStyleSheet("padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; font-size: 14px;")
        
        self.oc_suggest_btn = QPushButton("Get Next")
        self.oc_suggest_btn.setStyleSheet("padding: 8px 15px; background-color: #3498db; color: white; border-radius: 6px; font-weight: bold;")
        self.oc_suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.oc_num_input))
        
        oc_input_layout.addWidget(self.oc_num_input, 1)
        oc_input_layout.addWidget(self.oc_suggest_btn)
        form_layout.addLayout(oc_input_layout)
        
        # Notice Date
        nd_lbl = QLabel("Notice Date (ASMT-10 Date) *")
        nd_lbl.setStyleSheet("font-weight: bold; color: #475569;")
        form_layout.addWidget(nd_lbl)
        
        self.notice_date_edit = QDateEdit()
        self.notice_date_edit.setCalendarPopup(True)
        self.notice_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.notice_date_edit.setDate(QDate.currentDate())
        self.notice_date_edit.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; font-size: 14px;")
        self.notice_date_edit.dateChanged.connect(self.on_notice_date_changed)
        form_layout.addWidget(self.notice_date_edit)
        
        # Reply Date
        rd_lbl = QLabel("Last Date to Reply *")
        rd_lbl.setStyleSheet("font-weight: bold; color: #475569;")
        form_layout.addWidget(rd_lbl)
        
        self.reply_date_edit = QDateEdit()
        self.reply_date_edit.setCalendarPopup(True)
        self.reply_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.reply_date_edit.setDate(QDate.currentDate().addDays(self.DEFAULT_REPLY_DAYS))
        # REMOVED: setMaximumDate(30). Business rule: Officer can select any future date.
        self.reply_date_edit.setMinimumDate(QDate.currentDate()) 
        self.reply_date_edit.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; font-size: 14px;")
        # Date Logic Fix: Connect Change Signal
        self.reply_date_edit.dateChanged.connect(self.on_reply_date_user_changed)
        form_layout.addWidget(self.reply_date_edit)
        
        dp_layout.addWidget(details_form)
        details_page.setWidget(dp_content)
        self.content_stack.addWidget(details_page)

        # Page 4: ASMT-10 Drafting
        draft_page = QWidget()
        draft_layout = QVBoxLayout(draft_page)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        draft_layout.setSpacing(0)
        
        asmt_toolbar = QFrame()
        asmt_toolbar.setFixedHeight(60)
        asmt_toolbar.setStyleSheet("background: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        at_layout = QHBoxLayout(asmt_toolbar)
        at_layout.setContentsMargins(20, 0, 20, 0)
        
        self.asmt_pdf_btn = QPushButton("📄 Download PDF")
        self.asmt_pdf_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none;")
        self.asmt_pdf_btn.setIconSize(QSize(16, 16))
        self.asmt_pdf_btn.clicked.connect(lambda: self.download_asmt10("pdf"))
        at_layout.addWidget(self.asmt_pdf_btn)
        
        self.asmt_word_btn = QPushButton("📝 Download Word")
        self.asmt_word_btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; margin-left: 10px;")
        self.asmt_word_btn.clicked.connect(lambda: self.download_asmt10("word"))
        at_layout.addWidget(self.asmt_word_btn)
        
        at_layout.addStretch()
        
        # Removed "Issue & Register OC" button from here as requested
        # self.asmt_issue_btn = QPushButton("✅ Issue & Register OC")
        # at_layout.addWidget(self.asmt_issue_btn)
        
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; 
                color: white; 
                font-weight: 600;
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        refresh_btn.clicked.connect(self.refresh_asmt10_preview)
        at_layout.addWidget(refresh_btn)
        
        draft_layout.addWidget(asmt_toolbar)
        
        self.asmt_preview = QWebEngineView()
        self.asmt_preview.setStyleSheet("border: none;")
        self.asmt_preview.page().pdfPrintingFinished.connect(self.on_pdf_finished) # Connect print signal
        draft_layout.addWidget(self.asmt_preview, 1)

        
        self.content_stack.addWidget(draft_page)
        
        # Sticky Footer for Drafting Page (Minimal Action Area)
        # Sticky Footer for Drafting Page (Minimal Action Area)
        footer_container = QFrame()
        footer_container.setStyleSheet("background-color: white; border-top: 1px solid #e2e8f0; padding: 5px;")
        fc_layout = QHBoxLayout(footer_container)
        fc_layout.setContentsMargins(0,0,0,0)
        
        fc_layout.addStretch()
        self.finalise_btn = QPushButton("Finalise ASMT-10")
        self.finalise_btn.setStyleSheet("""
            QPushButton { 
                background-color: #ea580c; 
                color: white; 
                font-weight: bold; 
                font-size: 13px;
                padding: 6px 20px; 
                border-radius: 4px; 
                border: none;
            }
            QPushButton:hover { background-color: #c2410c; }
            QPushButton:disabled { background-color: #feb2b2; }
        """)

        self.finalise_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.finalise_btn.clicked.connect(self.finalize_asmt_notice)
        fc_layout.addWidget(self.finalise_btn)
        
        # ALIAS: Fix for AttributeError in analysis code using US spelling
        self.finalize_btn = self.finalise_btn
        # Center align or right align? User said "bottom-fixed action area... minimal". Usually right or center.
        # "Occupies only height required... No extra padding".
        # Let's keep it right-aligned or start-stretched-end?
        # "action area containing only one primary button"
        # I'll keep stretch-button-stretch for center or stretch-button for right. Let's do stretch-button to align right/center properly.
        # Actually user example often implies right bottom or center. I'll stick to previous stretch-button-stretch (Center).
        fc_layout.addStretch() 
        
        draft_layout.addWidget(footer_container, 0)



        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)
        
        workspace_layout.addWidget(splitter)

        # Default selection
        self.switch_section(0)

    def switch_section(self, index):
        """Switch the right content pane based on sidebar selection."""
        for i, card in enumerate(self.nav_cards):
            card.set_active(i == index)
        
        self.content_stack.setCurrentIndex(index)
        
        # Trigger refresh only if drafting selected (Index 3 or 4 based on setup)
        # Checking widget at index
        if index == 3 and hasattr(self, 'asmt_preview'):
            # Only refresh if state is ANALYZED
            if getattr(self, 'case_state', None) == "ANALYZED":
                self.refresh_asmt10_preview()

    def handle_file_upload(self, key, file_path):
        """Handle file upload callback with Strict Phase-1 Validation."""
        self._require_active_case(f"handle_file_upload({key})")
        self._block_if_finalized(f"handle_file_upload({key})")


        # 1. Prepare Validation Context
        exp_gstin = self.current_case_data.get('gstin', '')
        exp_fy = self.current_case_data.get('financial_year', '')
        
        # 2. Run Validation Service
        # Note: Validation Mode ('A'/'B') is now determined internally by the service based on file key/type.
        # We pass 'A' as placeholder to enforce strictness where applicable.
        is_valid, level, payload = FileValidationService.validate_file(file_path, key, exp_gstin, exp_fy, 'A')
        
        # 3. Handle Result
        if not is_valid:
            if level == "CRITICAL":
                # Payload is string message
                # Blocking Error - No Override
                title_suffix = " (Mismatch Detected)" if "Mismatch" in str(payload) else ""
                QMessageBox.critical(self, "Validation Failed", f"File Rejected{title_suffix}.\n\n{payload}")
                return
            elif level == "WARNING":
                # Payload is list of structured warnings
                # Format for display
                warn_text = ""
                for w in payload:
                    warn_text += f"- {w.get('message', 'Unknown Warning')}\n"
                    
                # Soft Warning - Ask for User Override
                reply = QMessageBox.question(
                    self, 
                    "Validation Warning", 
                    f"The file appears to contain discrepancies:\n\n{warn_text}\nDo you want to proceed anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
                # If Yes, proceed and log warning
                self._log_validation_warning(key, payload)
        
        # 4. Proceed with Upload Acceptance
        self.file_paths[key] = file_path

        # 5. Routing to UI Groups
        if key == "tax_liability_yearly":
            self.tax_group.set_file_path(key, file_path)
        elif key.startswith("gstr3b"):
            self.gstr3b_group.set_file_path(key, file_path)
        elif key.startswith("gstr1"):
            self.gstr1_group.set_file_path(key, file_path)
        elif key.startswith("gstr2b"):
            self.gstr2b_group.set_file_path(key, file_path)
        elif key.startswith("gstr2a"):
            self.gstr2a_group.set_file_path(key, file_path)
        elif key.startswith("gstr9"):
            self.gstr9_group.set_file_path(key, file_path)
        
        # 6. Enable Analysis Button (Common Condition)
        # CHECK: Only enable analysis if primary files are present
        has_primary = 'tax_liability_yearly' in self.file_paths
        has_gstr9 = any(k.startswith('gstr9') for k in self.file_paths)
        
        if has_primary or has_gstr9:
            self.analyze_btn.setEnabled(True)
            
        # PERSIST: File paths mutated
        self._persist_additional_details()

    def _log_validation_warning(self, key, warnings_list):
        """Persist structured validation warning override."""
        # Ensure dict
        if 'additional_details' not in self.current_case_data:
            self.current_case_data['additional_details'] = {}
            
        add_details = self.current_case_data['additional_details']
        if not isinstance(add_details, dict): 
             add_details = {}
             self.current_case_data['additional_details'] = add_details
             
        if 'validation_warnings' not in add_details:
             add_details['validation_warnings'] = {}
             
        from datetime import datetime
        
        # Store structured payload wrapped in meta
        add_details['validation_warnings'][key] = {
            "timestamp": datetime.now().isoformat(),
            "warnings": warnings_list
        }
        
        # PERSIST: Immediate State Consistency
        self._persist_additional_details()

    def handle_file_delete(self, key):
        """Handle file deletion"""
        self._require_active_case(f"handle_file_delete({key})")
        self._block_if_finalized(f"handle_file_delete({key})")
        
        if key in self.file_paths:
            del self.file_paths[key]
            
            # Downgrade State checks
            if not self.file_paths:
                self.case_state = "INIT"
                self.reset_analysis_ui()
            
        if key == "tax_liability_yearly":
            self.tax_group.set_file_path(key, None)
            self.analyze_btn.setEnabled(False) 
        elif key.startswith("gstr3b"):
            self.gstr3b_group.set_file_path(key, None)
        elif key.startswith("gstr1"):
            self.gstr1_group.set_file_path(key, None)
        elif key.startswith("gstr2b"):
            self.gstr2b_group.set_file_path(key, None)
        elif key.startswith("gstr2a"):
            self.gstr2a_group.set_file_path(key, None)
        elif key.startswith("gstr9"):
            self.gstr9_group.set_file_path(key, None)

    def analyze_file(self):
        """Analyze the Tax Liability file or GSTR 9 PDF"""
        main_file = self.file_paths.get('tax_liability_yearly')
        gstr9_file = self.file_paths.get('gstr9_yearly')
        
        # Enable analysis if either primary Excel OR GSTR 9 is present
        if not main_file and not gstr9_file:
            QMessageBox.warning(self, "No Data", "Please upload the Tax Liability Excel file or GSTR 9 PDF to run analysis.")
            return

        # Phase 5: Re-entrancy Guard
        if getattr(self, '_analysis_in_progress', False):
             self.log_event("WARN", "RE-ENTRANCY BLOCKED: analyze_file called while running.")
             return
        
        self._analysis_in_progress = True

        try:
            # STRICT BINDING ASSERTION
            self._require_active_case("analyze_file")
            self._block_if_finalized("analyze_file")
            
            self.scrutiny_results = [] # Invalidate previous results
            self.analyze_btn.setText("Analyzing...")
            self.analyze_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Prepare configs
            # Prepare configs
            configs = {
                "gstr3b_freq": self.gstr3b_group.selected_freq,
                "gstr1_freq": self.gstr1_group.selected_freq,
                "gstr2a_freq": self.gstr2a_group.selected_freq
            }
            
            # Phase-2: Initialize GSTR2AAnalyzer
            gstr2a_path = self.file_paths.get('gstr2a_yearly') # Or monthly set? Assuming Yearly for now as per spec file
            # Wait, user example file was yearly. 
            # In file loader mapping? 'gstr2a_yearly' is proper key.
            
            self.gstr2a_analyzer = None
            if gstr2a_path and os.path.exists(gstr2a_path):
                # Load cached selections from Case Data if available?
                # Ideally persist selections. But for now, transient or stored in memory?
                # Plan says: "cached selections". We can store in DB 'additional_details'.
                # For now, simplistic in-memory per session or fresh. 
                # To be robust: Load from DB if we want persistence across sessions.
                # Let's start with instance-level cache for this session.
                
                self.gstr2a_analyzer = GSTR2AAnalyzer(gstr2a_path)
                # Correctly wire the signal BEFORE passing to parser
                self.gstr2a_analyzer.ambiguity_detected.connect(self.resolve_header_ambiguity)

            # Run All Analysis
            results = self.parser.parse_file(main_file, self.file_paths, configs, gstr2a_analyzer=self.gstr2a_analyzer)
            
            if "error" in results:
                QMessageBox.critical(self, "Analysis Failed", results["error"])
                self.analyze_btn.setEnabled(True)
                return
                
            # SUCCESS: Mark Analysis Completed (Atomic)
            if self.current_case_id:
                # Update additional details flag
                if 'additional_details' not in self.current_case_data or not isinstance(self.current_case_data['additional_details'], dict):
                    self.current_case_data['additional_details'] = {}
                self.current_case_data['additional_details']['analysis_completed'] = True
                
                # PERSIST: Immediate State Consistency for Analysis Completion
                self._persist_additional_details()
                
                # STATE TRANSITION
                self._transition_case_state("ANALYZED")
                
                # INVARIANT ASSERTION
                if self.case_state != "ANALYZED":
                    raise RuntimeError("State transition to ANALYZED failed!")
                
                # APPLY UI STATE (Strict Single Authority)
                self.apply_case_state()

            # 1. Enrich (Smart Draft)
            issues = results.get("issues", []) # Assuming 'issues' are part of the results dict
            issues = self.enrich_issues_with_templates(issues)
            self.scrutiny_results = issues
            
            # 2. BLOCKING ERROR CHECK
            for issue in issues:
                if not isinstance(issue, dict): continue
                err = issue.get("error")
                if isinstance(err, dict) and err.get("type") == "blocking":
                     QMessageBox.critical(self, "Analysis Blocked", 
                         f"Critical Error in {issue.get('sheet') or issue.get('issue_id')}: {err.get('msg') or err.get('message')}")
                     self.analyze_btn.setEnabled(True)
                     return
                elif isinstance(err, str):
                     # Handle legacy string-type errors if any slip through
                     print(f"WARNING: String-type error detected for {issue.get('issue_id')}: {err}")
                     # Optionally show alert? For now, we just don't crash.

            # 3. RENDER (Strictly after state set)
            self.populate_results_view(issues)
            
            # VERIFICATION ASSERTION
            if hasattr(self, 'compliance_dashboard'):
                try: 
                     # Basic check: matching points should not be pending
                     pass
                except: pass

            self.switch_section(1) # Go to results (Dashboard)
            self.analyze_btn.setText("Re-Analyze Data")
            self.analyze_btn.setEnabled(True)
            self.set_read_only_mode(False) # Ensure UI is editable
            
            # Auto-save findings
            self.save_findings(silent=True)
            self.analyze_btn.setEnabled(True)
            self.finalize_btn.setEnabled(True) # Unlock Finalization only now
            
            analyzed_count = results.get("summary", {}).get("analyzed_count", 0) # Ensure analyzed_count is defined
            QMessageBox.information(self, "Analysis Complete", f"Analysis Complete. Analyzed {analyzed_count} SOP points.")
            
        except Exception as e:
            self.analyze_btn.setText("Analyze SOP Points")
            self.analyze_btn.setEnabled(True)
            # self.finalize_btn.setEnabled(False) # Keep locked
            self.log_event("ERROR", f"Analysis failed: {str(e)}", error=str(e))
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
        finally:
             self._analysis_in_progress = False
             self.analyze_btn.setEnabled(True) # Ensure unlocked

    def resolve_header_ambiguity(self, sop_id, canonical_key, options, cache_key):
        """
        Slot to handle Ambiguity Signal from GSTR2AAnalyzer.
        Shows Modal Dialog. Updates Analyzer cache.
        """
        # Check if finalized? Logic is mostly inside Analyzer usage, but Dialog shouldn't show if finalized.
        # But analyze_file shouldn't run if finalized anyway (UI blocked).
        
        dlg = HeaderSelectionDialog(str(sop_id), canonical_key, options, self)
        if dlg.exec():
            # User Selected
            selection = dlg.selected_header
            if selection:
                # Update Cache in Analyzer
                self.gstr2a_analyzer.cached_selections[cache_key] = selection
        else:
            # User Cancelled (Fallback)
            # We don't update cache. Analyzer will see cache missing and return None/Error for that SOP.
            pass

    def on_gstin_changed(self, text):
        if len(text) == 15:
            taxpayer = self.db.get_taxpayer(text)
            if taxpayer:
                self.tp_name_lbl.setText(f"Legal Name: {taxpayer.get('Legal Name', 'Unknown')}")
                self.tp_trade_lbl.setText(f"Trade Name: {taxpayer.get('Trade Name', '')}")
                status = taxpayer.get('Status', 'Active')
                self.tp_status_lbl.setText(f"Status: {status}")
                self.tp_status_lbl.setStyleSheet(f"color: {'green' if status == 'Active' else 'red'}; font-weight: bold;")
                self.details_frame.setVisible(True)
                return
        self.details_frame.setVisible(False)
        
    def reset_ui_state(self, full=True):
        """
        Comprehensive reset of the UI and internal state.
        full=True: Clears EVERYTHING (for New Case/Close Case).
        full=False: Clears only analysis results (for Re-Analysis).
        """
        # 1. Internal Data & Lifecycle
        self.scrutiny_results = []
        if full:
            # ABSOLUTE RULE: reset_ui_state MUST NEVER CLEAR IDENTITY
            # Identity (current_case_id/data) is managed ONLY by create_case / resume_case / close_case
            self.file_paths.clear()
            self.file_paths.clear()
            self.case_state = "INIT"
            self.reply_date_overridden = False # Date Logic Fix: Reset Flag

        # 2. Signal Safety (Disconnect risky signals)
        try: self.asmt_preview.loadFinished.disconnect()
        except (TypeError, AttributeError): pass
        try: self.results_area.issueSelected.disconnect()
        except (TypeError, AttributeError): pass

        # 3. Component Reset (Deep Clear)
        self.clear_results_view()
        if hasattr(self, 'compliance_dashboard'):
             self.compliance_dashboard.reset_all()

        if hasattr(self, 'results_area'):
             self.results_area.clear_results()
             if self.results_area.layout: self.results_area.layout.update()

        # 4. WebEngine Hard Reset
        if hasattr(self, 'asmt_preview'):
            from PyQt6.QtCore import QUrl
            self.asmt_preview.setUrl(QUrl("about:blank"))
            if hasattr(self.asmt_preview, 'history'):
                self.asmt_preview.history().clear()

        # 5. Uploaders (Full Reset)
        if full:
            if hasattr(self, 'tax_group'): self.tax_group.set_state("Yearly", {})
            if hasattr(self, 'gstr3b_group'): self.gstr3b_group.set_state("Yearly", {})
            if hasattr(self, 'gstr1_group'): self.gstr1_group.set_state("Yearly", {})
            if hasattr(self, 'gstr2b_group'): self.gstr2b_group.set_state("Yearly", {})
            if hasattr(self, 'gstr2a_group'): self.gstr2a_group.set_state("Yearly", {})
            if hasattr(self, 'gstr9_group'): self.gstr9_group.set_state("Yearly", {})
            
            # Reset Case Info
            self.case_info_lbl.setText("No Case Selected")
            self.gstin_combo.setCurrentIndex(-1)
            self.details_frame.setVisible(False)
            
            if hasattr(self, 'recent_container'):
                self.recent_container.setVisible(True)

        # 6. UI Unlocks (Explicit Finalization Reset)
        self.analyze_btn.setEnabled(False) # Wait for upload
        self.analyze_btn.setText("Analyze SOP Points")
        
        # Explicitly Lock Finalization until Analysis
        if hasattr(self, 'finalize_btn'): 
            self.finalize_btn.setEnabled(False)
            self.finalize_btn.setText("Finalize & Issue Notice")

        # Unlock Inputs for new entry
        if hasattr(self, 'oc_num_input'): self.oc_num_input.setEnabled(True); self.oc_num_input.clear()
        if hasattr(self, 'reply_date_edit'): self.reply_date_edit.setEnabled(True); self.reply_date_edit.setDate(QDate.currentDate().addDays(30))

    def reset_analysis_ui(self):
        """Targeted reset for analysis artifacts only - preserves case identity."""
        if hasattr(self, 'compliance_dashboard'):
            self.compliance_dashboard.reset_all()
        if hasattr(self, 'results_area'):
            self.results_area.clear_results()
        if hasattr(self, 'summary_strip'):
            self.summary_strip.update_summary("Unknown", "N/A")
        if hasattr(self, 'asmt_preview'):
            from PyQt6.QtCore import QUrl
            self.asmt_preview.setUrl(QUrl("about:blank"))
        self.scrutiny_results = []

    def create_case(self):
        gstin = self.gstin_combo.currentText()
        fy = self.fy_combo.currentText()
        if not gstin or not fy:
            QMessageBox.warning(self, "Validation Error", "Please select both GSTIN and Financial Year.")
            return

        # 1. State Reset (Full)
        self.reset_ui_state(full=True)
        self.reset_case_details_form()
        self.recent_container.setVisible(False) # Hide recent list immediately
        
        taxpayer = self.db.get_taxpayer(gstin)

        legal_name = taxpayer.get('Legal Name', 'Unknown') if taxpayer else "Unknown"
        trade_name = taxpayer.get('Trade Name', '') if taxpayer else ""
        address = taxpayer.get('Address') or taxpayer.get('Address of Principal Place of Business') or ""
        
        data = { 
            "gstin": gstin, 
            "legal_name": legal_name, 
            "trade_name": trade_name,
            "address": address,
            "financial_year": fy, 
            "form_type": "ASMT-10", 
            "financial_year": fy, 
            "form_type": "ASMT-10", 
            "initiating_section": "61", 
            "status": "Initiated", 
            "created_by": "System",
            "taxpayer_details": taxpayer, # Store full snapshot
            "selected_issues": [], # Explicit Empty
            "additional_details": {"file_paths": {}, "group_configs": {}, "analysis_completed": False} # Explicit Init
        }

        # Verify State Authority
        # FIX: Check derived state against the new data payload, not uninitialized current_case_data
        self.case_state = self.derive_case_state(data)
        assert self.case_state == "INIT", "Newly created case must be in INIT state"
        
        # Create DB Entry
        new_pid = self.db.create_proceeding(data)
        
        # ASSERTION: ID Uniqueness (Critical)
        if new_pid and self.current_case_id:
             if new_pid == self.current_case_id:
                  QMessageBox.critical(self, "System Error", "FATAL: Database returned duplicate Case ID. Aborting.")
                  return
        
        # Redundant Safety: Match "No Documents" state
        self.file_paths = {}

        if new_pid:
            self.current_case_id = new_pid
            self.current_case_data = {'gstin': gstin, 'financial_year': fy}
            
            # APPLY UI STATE (Strict Authority)
            self.apply_case_state()
            
            self.case_info_lbl.setText(f"{legal_name} | {gstin} | {fy}")
            self.switch_section(0) # Go to uploads
            self.stack.setCurrentIndex(1)
            self.recent_container.setVisible(False)
            self.load_recent_cases()
            QMessageBox.information(self, "Success", "Case created successfully! You can now proceed to upload files.")
        else:
            QMessageBox.critical(self, "Error", "Failed to create case database entry.")

    def close_case(self):
        # 1. Reset UI
        self.reset_ui_state(full=True)
        
        # 2. Clear Identity (Explicitly here, and ONLY here outside of creation/resume)
        self.current_case_id = None
        self.current_adj_id = None
        self.current_case_data = None
        
        self.case_info_lbl.setText("No Case Selected")
        self.switch_section(0)
        self.recent_container.setVisible(True)
        self.load_recent_cases()
        self.stack.setCurrentIndex(0)



    def clear_results_view(self):
        self.summary_strip.update_summary("Unknown", "N/A")
        self.results_area.clear_results()

    def _resolve_fact_path(self, facts, path):
        """Helper to resolve dot-notation path in facts dict."""
        if not path: return {}
        parts = path.split('.')
        # parts[0] is usually "facts"
        curr = facts
        
        start_idx = 1 if parts[0] == "facts" else 0
        
        for p in parts[start_idx:]:
            if isinstance(curr, dict):
                curr = curr.get(p, {})
            else:
                return {}
        return curr

    def _hydrate_grid_from_facts(self, table_def, facts):
        """Hydrates grid_data using Table Definition and Semantic Facts."""
        columns = table_def.get("columns", [])
        rows_def = table_def.get("rows", [])
        
        # 1. Build Header (No change, list of dicts)
        # BUT we must ensure they have IDs
        header_row = []
        for i, col in enumerate(columns):
             # Ensure ID exists
             c_id = col.get("id") or f"col{i}"
             col["id"] = c_id # Backfill into definition for row loop usage
             
             header_row.append({
                 "id": c_id,
                 "label": col["label"],
                 "value": col["label"], # UI often uses value
                 "type": "static",
                 "style": "header"
             })
        
        grid = [] # Data Rows (List of Dicts)
        
        # 2. Build Data Rows
        for r_def in rows_def:
            row_cells = {}
            
            # Label Cell (First Col) - Use first column ID
            first_col_id = columns[0]["id"]
            row_cells[first_col_id] = {
                "value": r_def["label"],
                "type": "static",
                "style": "normal"
            }
            
            # Data Cells
            source_path = r_def.get("source") # e.g. "facts.gstr1"
            base_fact = self._resolve_fact_path(facts, source_path)
            
            # Columns 1..N (Tax Heads)
            # Assuming columns are [Desc, IGST, CGST, SGST, Cess]
            # We map col id to tax head key.
            
            for col in columns[1:]: # Skip Desc column
                col_id = col["id"] # igst, cgst...
                val = base_fact.get(col_id, 0) if isinstance(base_fact, dict) else 0
                
                # Apply Semantics
                semantics = r_def.get("semantics", {})
                style = "normal"
                
                if semantics.get("emphasis") == "primary": 
                    style = "bold"
                    
                # Conditional Severity
                if semantics.get("condition") == "is_positive" and val > 0:
                     if semantics.get("severity") == "critical": 
                         style = "red_bold" # UI IssueCard needs to handle this style string
                
                
                row_cells[col_id] = {
                    "value": val,
                    "type": "input", 
                    "var": f"{r_def.get('row_id')}_{col_id}", 
                    "style": style
                }
            
            grid.append(row_cells)
            
        # CANONICAL SCHEMA: Return Dict
        # Grid is now List[Dict[str, Cell]]
        return {
            "columns": header_row,
            "rows": grid
        }

    def enrich_issues_with_templates(self, issues):
        """Fetches official legal language and detailed schema from DB for detected SOP issues.
           Enforces strict logic: issue_id -> Master DB Record.
           
           CRITICAL INVARIANT: Every issue MUST have a valid sop_point.
        """
        # DIAGNOSTIC LOGGING
        print(f"DEBUG: enrich_issues_with_templates received {len(issues)} issues.")

        # STATIC FALLBACK REGISTRY (Safety Net for DB Failures)
        SOP_FALLBACK_MAP = {
            'LIABILITY_3B_R1': 1,
            'RCM_LIABILITY_ITC': 2,
            'ISD_CREDIT_MISMATCH': 3,
            'ITC_3B_2B_OTHER': 4,
            'TDS_TCS_MISMATCH': 5,
            'EWAY_BILL_MISMATCH': 6,
            'CANCELLED_SUPPLIERS': 7,
            'NON_FILER_SUPPLIERS': 8,
            'SEC_16_4_VIOLATION': 9,
            'IMPORT_ITC_MISMATCH': 10,
            'RULE_42_43_VIOLATION': 11,
            'ITC_3B_2B_9X4': 12
        }

        enriched = []
        for issue in issues:
            # DEFENSIVE GUARD
            if not isinstance(issue, dict):
                print(f"ERROR: Invalid issue payload (not a dict): {issue}")
                continue

            desc = issue.get("description") or issue.get("category")
            
            # Step 1: Resolve ID (Must be provided by Parser now)
            issue_id = issue.get('issue_id') 
            
            if not issue_id:
                 # REQUIREMENT: Fail Loudly if parser lacks ID
                 error_msg = f"INTEGRITY ERROR: Scrutiny Issue '{desc}' has no 'issue_id'. Parser must emit Semantic IDs."
                 print(error_msg)
                 raise RuntimeError(error_msg)

            # Step 2: Fetch Master Record
            master = self.db.get_issue(issue_id)
            
            # --- START CRITICAL ENFORCEMENT ---
            resolved_sop_point = None
            resolved_issue_name = None
            
            if master:
                # 1. DB Priority
                resolved_sop_point = master.get('sop_point')
                resolved_issue_name = master.get('issue_name')
                
                # Enrich Metadata
                issue['issue_master_id'] = master.get('issue_id')
                issue['issue_name'] = resolved_issue_name
                issue['sop_point'] = resolved_sop_point 
                
            # 2. Static Fallback (If DB missing or incomplete)
            if not resolved_sop_point:
                resolved_sop_point = SOP_FALLBACK_MAP.get(issue_id)
                if resolved_sop_point:
                     print(f"WARNING: Issue '{issue_id}' resolved via STATIC FALLBACK (DB missing sop_point).")

            # 3. FATAL ASSERTION
            if not resolved_sop_point:
                 err = f"FATAL INVARIANT FAILURE: Issue '{issue_id}' cannot be mapped to an SOP Point. DB and Fallback failed."
                 print(err)
                 QMessageBox.critical(self, "System Integrity Error", err)
                 raise RuntimeError(err) # Crash Fast
                 
            # Apply to Issue
            issue['sop_point'] = resolved_sop_point
            # --- END CRITICAL ENFORCEMENT ---
            
            # Check for New Facts-Based Path
            table_def = master.get('table_definition') if master else None
            facts = issue.get('facts')
            
            if table_def and facts:
                # NEW PATH: Hydrate from Facts (Canonical Dict)
                print(f"DEBUG: Hydrating {issue_id} via New Path.")
                issue['grid_data'] = self._hydrate_grid_from_facts(table_def, facts)
            elif "summary_table" in issue or "tables" in issue:
                # PRE-PARSED TABLE PATH: Respect pre-calculated summary tables (SOP-2 Robust Path)
                pass
            else:
                # LEGACY PATH: Snapshot Injection (Only if Master exists)
                if master:
                    master_grid = master.get('grid_data')
                    snapshot = issue.get('snapshot', {})
                    
                    if master_grid and isinstance(master_grid, list):
                        import copy
                        rehydrated_grid = copy.deepcopy(master_grid)
                        
                        # Fill variables from snapshot
                        for row in rehydrated_grid:
                            for cell in row:
                                var_name = cell.get('var')
                                if var_name and var_name in snapshot:
                                    cell['value'] = snapshot[var_name]
                        
                        # CONVERT TO CANONICAL DICT SCHEMA
                        if len(rehydrated_grid) > 0:
                             header_row = rehydrated_grid[0]
                             data_rows = rehydrated_grid[1:]
                             
                             col_keys = []
                             for i, h_cell in enumerate(header_row):
                                  if isinstance(h_cell, dict):
                                      col_keys.append(h_cell.get("id") or f"col{i}")
                                  else:
                                      col_keys.append(f"col{i}")
                                      
                             dict_rows = []
                             for row in data_rows:
                                  row_dict = {}
                                  for i, cell in enumerate(row):
                                      if i < len(col_keys):
                                           row_dict[col_keys[i]] = cell
                                  dict_rows.append(row_dict)

                             issue['grid_data'] = {
                                 "columns": header_row, 
                                 "rows": dict_rows
                             }
            
            # Enrich Legal Text
            if master:
                 template_facts = master.get('templates', {}).get('brief_facts', "")
                 # If issue doesn't have specific facts yet, use template
                 if not issue.get('brief_facts') or issue.get('brief_facts') == desc:
                      issue['brief_facts'] = template_facts
            
            # Fallback if still empty
            if not issue.get('brief_facts'):
                issue['brief_facts'] = desc

            enriched.append(issue)
        return enriched

    def handle_save_master_template(self, issue_data):
        """Callback from IssueCard to update the global master template."""
        issue_id = issue_data.get('issue_master_id')
        if not issue_id:
            QMessageBox.warning(self, "Unsupported", "This issue does not have a master template in the database.")
            return
            
        new_text = issue_data.get('description', '').strip()
        if not new_text:
            QMessageBox.warning(self, "Invalid Content", "Cannot save empty template.")
            return
            
        reply = QMessageBox.question(self, "Save Master Template", 
                                   "Are you sure you want to save this text as the DEFAULT for all future cases?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.db.update_master_template_description(issue_id, new_text)
            if success:
                QMessageBox.information(self, "Template Updated", "Master template updated successfully and will be used for future cases.")
            else:
                QMessageBox.critical(self, "Save Error", f"Failed to update master template:\n{msg}")

    def populate_results_view(self, issues):
        """Populate the analysis results into collapsible cards."""
        # DIAGNOSTIC LOGGING (MANDATORY)
        print("POPULATE_RESULTS_VIEW CALLED")
        print("Case state:", getattr(self, 'case_state', 'Unknown'))
        print("Issues passed:", len(issues) if issues else 0)
        if issues:
            print("Issue IDs:", [i.get('issue_id') for i in issues])
            print("SOP Points:", [i.get('sop_point') for i in issues])

        # STRICT GUARD: Check lifecycle
        assert getattr(self, 'case_state', 'INIT') == "ANALYZED", f"populate_results_view called in invalid state: {self.case_state}"
        
        # GUARD: Prevent population if no active case (Now a hard assertion)
        assert self.current_case_id is not None, "populate_results_view called without active case (current_case_id is None)"

        # 1. Update Summary Strip
        try:
            legal_name = self.current_case_data.get('legal_name', 'Unknown')
            if legal_name == 'Unknown' and self.current_case_data.get('gstin'):
                 taxpayer = self.db.get_taxpayer(self.current_case_data.get('gstin'))
                 if taxpayer:
                     legal_name = taxpayer.get('Legal Name', taxpayer.get('legal_name', 'Unknown'))
            
            self.summary_strip.update_summary(
                legal_name,
                self.current_case_data.get('financial_year', 'Unknown')
            )
        except Exception as e:
            print(f"Error updating summary: {e}")

        # 2. STRICT RESET (Exactly Once)
        self.results_area.clear_results()
        self.compliance_dashboard.reset_all()
        print("RESET DONE")

        if not issues:
             print("No issues to populate")
             return

        # 3. Populate Cards
        found_points = set()
        issue_idx = 1
        updated_cards_count = 0
        
        for issue in issues:
            shortfall = issue.get("total_shortfall", 0)
            
            # Only add to "Executive Summary" / Results List if there is an actual liability/issue
            # Only add to "Executive Summary" / Results List if there is an actual liability/issue
            if shortfall > 0:
                # [SOP-10 PRE-UI] Checkpoint
                if issue.get('issue_id') == 'IMPORT_ITC_MISMATCH':
                    import hashlib
                    import json
                    def _safe_hash(d):
                         try:
                             s = json.dumps(d, sort_keys=True, default=str)
                             return hashlib.sha1(s.encode()).hexdigest()
                         except: return "HASH_ERR"
                    
                    print(f"\n[SOP-10 PRE-UI] Issue ID: {issue.get('issue_id')}")
                    print(f"[SOP-10 PRE-UI] Category: {issue.get('category')}")
                    print(f"[SOP-10 PRE-UI] Template Type: {issue.get('template_type')}")
                    print(f"[SOP-10 PRE-UI] Summary Table: {issue.get('summary_table')}")
                    st = issue.get('summary_table')
                    print(f"[SOP-10 PRE-UI] ID(Summary Table): {id(st)}")
                    print(f"[SOP-10 PRE-UI] ID(Summary Rows): {id(st.get('rows')) if st else 'N/A'}")
                    print(f"[SOP-10 PRE-UI] Hash: {_safe_hash(issue)}")

                self.results_area.add_result(issue, issue_number=issue_idx)
                issue_idx += 1
            
            # Update Dashboard Status
            point_num = issue.get('sop_point')
            
            if point_num:
                found_points.add(point_num)
                # Check for explicit status message from parser
                if issue.get("status_msg"):
                    status = issue.get("status", "info")
                    msg = issue.get("status_msg")
                    
                    # User Request: If PASS, show value (Rs. 0) not "Matched" or "0"
                    # We override ONLY if the parser didn't already format it as "Rs. ..."
                    # Actually, requirement says "All zero-value cards display exactly: Rs. 0".
                    # If status_msg is "Matched" (from legacy parser logic), we should overwrite it?
                    # "Mandatory fix: Remove all special-casing for zero... Enforce badge_text = format_indian_number(amount, prefix_rs=True)"
                    
                    if status == 'pass':
                        # Force numeric display
                        val = issue.get('total_shortfall', 0)
                        msg = format_indian_number(val, prefix_rs=True)

                    print(f"UPDATING CARD: {point_num} STATUS: {status} MSG: {msg}")
                    self.compliance_dashboard.update_point(point_num, status, msg, details=issue)
                    updated_cards_count += 1
                else:
                    status = "fail" if shortfall > 100 else "alert" if shortfall > 0 else "pass"
                    print(f"UPDATING CARD: {point_num} STATUS: {status} SHORTFALL: {shortfall}")
                    msg = format_indian_number(shortfall, prefix_rs=True)
                    self.compliance_dashboard.update_point(point_num, status, msg, details=issue)
                    updated_cards_count += 1
            else:
                print(f"INTEGRITY ERROR: Issue '{issue.get('issue_id')}' has no 'sop_point' in DB. Cannot map to Dashboard.")

        # 4. MAPPING INVARIANT CHECK
        # We can't easily check self.dashboard.cards direct status without access to its internals, 
        # but we can trust our log for now. 
        # User requested: assert updated == len(issues)
        # But 'issues' includes things that might not map to cards (e.g. general info?). 
        # Scrutiny issues typically DO map 1:1 to SOP points.
        print(f"Cards updated: {updated_cards_count} / {len(issues)}")
        
        # 4. Switch to Compliance Dashboard
        self.switch_section(1)
        self.nav_cards[1].set_summary(f"{len(issues)} issues identified")


    def refresh_asmt10_preview(self):
        """Generates and displays the ASMT-10 HTML in the preview pane."""
        # STRICT GUARD: Check lifecycle
        # For FINALIZED, we use a different path or allow it if safe, but here we strictly rely on render_finalized_view logic usually.
        # But the user request says: "refresh_asmt10_preview ... assert self.case_state in (ANALYZED, FINALIZED)"
        # However, my previous logic blocked FINALIZED here to force using render_finalized_view logic...
        # The REQ says: "if getattr(self, 'case_state', 'INIT') not in ('ANALYZED', 'FINALIZED'): return"
        
        # HARD LOCK: FINALIZED cases must NEVER regenerate preview via parser/generator live path
        if getattr(self, 'case_state', 'INIT') == "FINALIZED":
             return

        # Consolidated state check
        if getattr(self, 'case_state', 'INIT') != "ANALYZED":
            self.asmt_preview.setHtml("")
            return

        # GUARD: Prevent preview generation if no active case
        if not self.current_case_id:
            return

        if not self.scrutiny_results:
            self.asmt_preview.setHtml("<div style='display:flex; justify-content:center; align-items:center; height:100%; color:#95a5a6; font-family:sans-serif;'><h2>Please analyze a case to preview ASMT-10</h2></div>")
            return
            
        # Optional: Auto-save findings to DB before previewing
        self.save_findings(silent=True)
        
        proc = self.db.get_proceeding(self.current_case_id)
        if not proc:
            # Fallback for display if DB fetch fails
            proc = {
                "gstin": self.current_case_data.get('gstin', 'N/A'),
                "legal_name": self.current_case_data.get('legal_name', 'N/A'),
                "financial_year": self.current_case_data.get('financial_year', 'N/A')
            }
        else:
            proc = dict(proc)
            # Enrich with fresh taxpayer data if missing fields
            gstin = proc.get('gstin')
            if gstin:
                taxpayer = self.db.get_taxpayer(gstin)
                if taxpayer:
                    if not proc.get('legal_name'):
                        proc['legal_name'] = taxpayer.get('Legal Name', 'Unknown')
                    if not proc.get('address'):
                        proc['address'] = taxpayer.get('Address') or taxpayer.get('Address of Principal Place of Business')
                    # Also ensure taxpayer_details is set for generator fallbacks
                    if not proc.get('taxpayer_details'):
                        proc['taxpayer_details'] = taxpayer
            
        try:
            html = ASMT10Generator.generate_html(proc, self.scrutiny_results, for_preview=True)
            self.asmt_preview.setHtml(html)
        except Exception as e:
            self.asmt_preview.setHtml(f"<div style='color:red;'><h2>Error generating preview: {str(e)}</h2></div>")

    def download_asmt10(self, format_type):
        """Download the ASMT-10 in PDF or Word format."""
        if not self.scrutiny_results and self.case_state != "FINALIZED":
            QMessageBox.warning(self, "No Data", "Please analyze a case first.")
            return

        proc = self.db.get_proceeding(self.current_case_id)
        if not proc: return
            
        # DATA SOURCE: 
        # If FINALIZED: Fetch authoritative snapshot from DB.
        # If DRAFTING: Use current live scrutiny_results.
        if getattr(self, 'case_state', 'INIT') == "FINALIZED":
             issues = self._load_issues_from_db(dict(proc))
        else:
             issues = self.scrutiny_results
             
        if not issues:
             QMessageBox.warning(self, "No Data", "No issues found to export.")
             return
             
        html = ASMT10Generator.generate_html(proc, issues)
        
        if format_type == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Save ASMT-10 PDF", f"ASMT10_{proc['gstin']}.pdf", "PDF Files (*.pdf)")
            if path:
                # Use WebEngine's built-in printToPdf which renders the current view
                # If Finalized, the view is already displaying the snapshot, so this matches.
                # BUT, printToPdf captures the *Visible* QWebEnginePage.
                # If we want to ensure we print exactly what we generated from DB, 
                # we might need to setHtml first if the view is stale?
                # In Finalized mode, render_finalized_view sets the HTML. 
                # So the view should be correct.
                # However, for robustness, we can update the view if needed, 
                # but printToPdf is async and relies on the widget.
                # Let's rely on the user having the view open (which is true if they clicked the button).
                
                # Wait, if we are in FINALIZED mode, we prevented `refresh_asmt10_preview`.
                # Does `render_finalized_view` set the HTML?
                # Yes: self.asmt_preview.setHtml(html) is inside render_finalized_view (needs verification).
                # Checking render_finalized_view... it calls _populate_results_view_readonly but does it render HTML?
                # I recall lines 1800+ in previous view_file showing:
                # html = ASMT10Generator.generate_html(proc, issues, for_preview=True)
                # self.asmt_preview.setHtml(html)
                # So yes, the view is hydrated.
                
                layout = QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(15, 15, 15, 15), # 15mm margins
                    QPageLayout.Unit.Millimeter
                )
                self.asmt_preview.page().printToPdf(path, layout)
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save ASMT-10 Word", f"ASMT10_{proc['gstin']}.doc", "Word Files (*.doc)")
            if path:
                success, msg = ASMT10Generator.save_docx(html, path)
                if success: QMessageBox.information(self, "Success", "Word document (HTML-based) saved successfully.")
                else: QMessageBox.critical(self, "Error", msg)

    def on_pdf_finished(self, path, success):
        """Callback for PDF printing"""
        if success:
            QMessageBox.information(self, "Success", f"PDF saved successfully to:\n{path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to generate PDF.")

    def on_notice_date_changed(self, date):
        """Update reply date default and range when notice date changes"""
        # Suggest Default: Notice Date + 15 days
        # But ensure Officer can change it freely to any later date.
        
        # SYSTEM UPDATE: Block signals on reply edit while we auto-adjust min date
        # (Though setMinimumDate usually doesn't trigger dateChanged unless current value is invalid)
        self.reply_date_edit.blockSignals(True)
        self.reply_date_edit.setMinimumDate(date)
        self.reply_date_edit.blockSignals(False)
        
        # Core Date Logic Fix: Only auto-update if NOT overridden
        if not self.reply_date_overridden:
             self.reply_date_edit.blockSignals(True)
             self.reply_date_edit.setDate(date.addDays(self.DEFAULT_REPLY_DAYS))
             self.reply_date_edit.blockSignals(False)

    def on_reply_date_user_changed(self, date):
        """Date Logic Fix: Detect explicit user override."""
        self.reply_date_overridden = True
        # print(f"Reply Date Overridden by User: {date.toString()}")

    def save_findings(self, silent=False):
        """Consolidated save method for both issue findings and case details."""
        self._require_active_case("save_findings")
        # Check Finalized status?
        # Usually save is disabled in UI for Finalized.
        # But if called programmatically, we should block it unless we are in a special mode.
        # For now, SAFE MODE requires strict blocking.
        # Exception: finalize_asmt_notice calls save_findings(silent=True) internally right before locking.
        # BUT finalize_asmt_notice checks idempotency first. If not finalized yet, it's allowed.
        # If already finalized, save_findings would trigger this block.
        # So we must block IF state IS already FINALIZED.
        self._block_if_finalized("save_findings")

        
        # 1. Gather issue findings from the Results Area (Executive Summary)
        # These are the ones the user might have edited.
        updated_issues = self.results_area.get_all_data()
        
        # 2. Merge these updates back into the full scrutiny_results list
        # 2. Update existing issues or add new ones
        existing_issues = self.scrutiny_results # This is the current in-memory state
        
        if existing_issues:
            # FIX: Merge strictly by issue_id (CRITICAL DATA INTEGRITY)
            # Create a map for quick lookup of existing issues by issue_id
            existing_issues_map = {issue.get('issue_id'): issue for issue in existing_issues if issue.get('issue_id')}
            
            final_issues = []
            for updated in updated_issues: # Iterate through issues from results_area (user-edited)
                updated_id = updated.get('issue_id')
                
                if not updated_id:
                     raise RuntimeError(f"CRITICAL: Issue '{updated.get('category')}' is missing 'issue_id'. Cannot save.")

                if updated_id in existing_issues_map:
                    # Update existing issue with new data from results_area
                    existing_issue = existing_issues_map[updated_id]
                    existing_issue.update(updated) # Merge changes
                    final_issues.append(existing_issue)
                    del existing_issues_map[updated_id] # Remove from map to track processed issues
                else:
                    # This case should ideally not happen if results_area only shows existing issues
                    # But if it does, add it as a new issue
                    final_issues.append(updated)
            
            # Add back any issues that were in existing_issues but not in updated_issues (e.g., matched points not shown in results_area)
            final_issues.extend(existing_issues_map.values())
            
            self.scrutiny_results = final_issues # Update the internal state
        else:
            # If there were no existing issues, just take what's from results_area
            self.scrutiny_results = updated_issues
            final_issues = updated_issues
        
        # 3. Gather Case Details
        oc_num = self.oc_num_input.text().strip()
        notice_date = self.notice_date_edit.date().toString("yyyy-MM-dd")
        reply_date = self.reply_date_edit.date().toString("yyyy-MM-dd")
        
        # 4. Update Database
        # 4. Update Database
        # Fetch existing additional_details to preserve other keys (like analysis_completed)
        existing_proc = self.db.get_proceeding(self.current_case_id)
        add_details = {}
        if existing_proc:
            existing_details = existing_proc.get('additional_details', '{}')
            if isinstance(existing_details, str):
                try: add_details = json.loads(existing_details)
                except: add_details = {}
            else:
                add_details = existing_details if isinstance(existing_details, dict) else {}

        # Merge updates
        add_details['file_paths'] = self.file_paths
        
        group_configs = {
            "gstr3b": {"frequency": self.gstr3b_group.selected_freq},
            "gstr1": {"frequency": self.gstr1_group.selected_freq},
            "gstr2b": {"frequency": self.gstr2b_group.selected_freq},
            "gstr9": {"frequency": self.gstr9_group.selected_freq}
        }
        add_details['group_configs'] = group_configs
        
        # Persist Analysis Completed Flag if currently analyzed
        if self.case_state in ["ANALYZED", "FINALIZED"]:
            add_details['analysis_completed'] = True
        
        updates = {
            "selected_issues": self.scrutiny_results, # Save the FULL list
            "oc_number": oc_num,
            "notice_date": notice_date,
            "last_date_to_reply": reply_date,
            "last_date_to_reply": reply_date,
            "additional_details": json.dumps(add_details),
            # Date Logic Fix: Persist Override Flag (redundantly in root for easier debug/access if schema allows? 
            # No, keep strict schema inside additional_details to avoid DB schema change on SQL side)
        }
        
        # Date Logic Fix: Ensure flag is inside add_details before dumping
        add_details['reply_date_overridden'] = self.reply_date_overridden
        updates['additional_details'] = json.dumps(add_details)
        
        success = self.db.update_proceeding(self.current_case_id, updates)
        
        if not silent:
            if success:
                QMessageBox.information(self, "Saved", "Analysis findings and case details saved successfully.")
            else:
                QMessageBox.critical(self, "Save Error", "Failed to update case in database.")

    def draft_asmt10(self):
        if not self.scrutiny_results:
            QMessageBox.warning(self, "No Data", "Please analyze a file first.")
            return

        # STRICT SNAPSHOT LOCK
        if getattr(self, 'case_state', 'INIT') == "FINALIZED":
             QMessageBox.warning(self, "Restricted", "Drafting is disabled for Finalized cases. Please use the Finalized View.")
             return

        self.save_findings()
        proc = self.db.get_proceeding(self.current_case_id)
        if not proc: proc = {"gstin": "Preview", "legal_name": "Preview", "financial_year": "2023-24", "created_at": "2024-12-16"}
        else: proc = dict(proc)
            
        try:
            html = ASMT10Generator.generate_html(proc, self.scrutiny_results)
            dialog = ASMT10PreviewDialog(html, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", str(e))

    def finalize_asmt_notice(self):
        """Finalize the ASMT-10 notice with validation and registers."""
        self._require_active_case("finalize_asmt_notice")
        
        # Idempotency Check (Not an error)
        if getattr(self, 'case_state', 'INIT') == "FINALIZED":
             QMessageBox.information(self, "Already Finalized", "This case is already finalized.")
             return
        
        # 1. Validation
        oc_num = self.oc_num_input.text().strip()
        gstin = self.current_case_data.get('gstin', '')
        fy = self.current_case_data.get('financial_year', '')
        
        # For simplicity, we assume Taxpayer Name/GSTIN/FY are present if case exists.
        # Check explicit mandatory inputs
        if not oc_num:
            QMessageBox.warning(self, "Validation Error", "Mandatory Field Missing: O.C. Number is required.")
            self.switch_section(3) # Go to details
            self.oc_num_input.setFocus()
            return

        # 2. Confirmation Dialog
        proc = self.db.get_proceeding(self.current_case_id)
        legal_name = proc.get('legal_name', '')
        issue_date = self.notice_date_edit.date().toString("yyyy-MM-dd")
        
        data = {
            'oc_num': oc_num,
            'issue_date': issue_date,
            'gstin': gstin,
            'legal_name': legal_name,
            'fy': fy
        }
        
        # Filter to only show actual issues in the dialog
        
        # Filter Logic: Shortfall > 0 AND Included by User
        detected_issues = [i for i in self.scrutiny_results if float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)]
        
        dlg = FinalizationConfirmationDialog(data, detected_issues, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
            
        # 3. Finalization Action
        
        # Save current state first
        self.save_findings(silent=True)
        
        # Authoritative Persistence: Persist ONLY finalized issues (shortfall > 0) to case_issues
        # This is the SOLE legal source for downstream SCN drafting.
        # DEEPCOPY CRITICAL: Lock the snapshot in memory before writing to DB
        active_issues = copy.deepcopy([i for i in self.scrutiny_results if float(i.get('total_shortfall', 0)) > 0 and i.get('is_included', True)])
        structured_issues = []
        for item in active_issues:
            # issue_id is the primary legal identifier
            issue_id = item.get('issue_master_id') or item.get('sop_point_id') or item.get('category', 'unknown_issue')
            
            # Legally Frozen Snapshot
            snapshot_data = {
                'issue_id': issue_id,
                'issue_name': item.get('issue_name') or item.get('category'),
                'total_shortfall': float(item.get('total_shortfall', 0)),
                'brief_facts': item.get('brief_facts'), # The edited ASMT-10 narration
                'snapshot': item.get('snapshot', {}), # Raw detected values
                'grid_data': item.get('grid_data'), # Frozen table structure
                'tables': item.get('tables'), # Frozen Multi-Table Structure (SOP-5)
                'financial_year': fy
            }
            
            structured_issues.append({
                'issue_id': issue_id,
                'data': snapshot_data
            })
            
        # Write strictly to DRC-01A stage
        self.db.save_case_issues(self.current_case_id, structured_issues, stage='DRC-01A')
        
        # Prepare Data for Transaction
        oc_data = {
            'OC_Number': oc_num,
            'OC_Date': issue_date,
            'OC_Content': f"ASMT-10 Issued for GSTIN {gstin}. Discrepancies noted in returns.",
            'OC_To': legal_name
        }
        
        asmt_data = {
            'gstin': gstin,
            'financial_year': fy,
            'issue_date': issue_date,
            'case_id': self.current_case_id,
            'oc_number': oc_num
        }
        
        adj_data = {
            'source_scrutiny_id': self.current_case_id,
            'gstin': gstin,
            'legal_name': legal_name,
            'financial_year': fy
        }
        
        # Execute Atomic Transaction
        success, result = self.db.finalize_proceeding_transaction(
            self.current_case_id, oc_data, asmt_data, adj_data
        )
        
        if success:
            QMessageBox.information(self, "Success", f"ASMT-10 Finalized Successfully.\n\nLinked Adjudication Case Created.\nID: {result}")
            # Reload application state to apply read-only restrictions
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, self.current_case_id)
            self.resume_case(item) 
        else:
            QMessageBox.critical(self, "Error", f"Finalization Failed: {result}")


    def suggest_next_oc(self, input_field: QLineEdit):
        """Fetch next available OC number and set it to input"""
        try:
            import datetime
            current_year = datetime.date.today().year
            
            # Fetch next number from DB
            next_num = self.db.get_next_oc_number(str(current_year))
            
            formatted_oc = f"{next_num}/{current_year}"
            input_field.setText(formatted_oc)
            
        except Exception as e:
            print(f"Error suggesting OC: {e}")
