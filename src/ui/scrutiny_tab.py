from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QComboBox, QPushButton, QMessageBox, QStackedWidget, 
                             QCompleter, QFrame, QFileDialog, QScrollArea, 
                             QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QDialog, QApplication,
                             QSizePolicy, QSplitter, QTabWidget, QToolButton, QTextBrowser, QDateEdit,
                             QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QAbstractAnimation, QDate, pyqtSignal, QMarginsF
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from src.database.db_manager import DatabaseManager
from src.services.scrutiny_parser import ScrutinyParser
from src.services.asmt10_generator import ASMT10Generator
import os
import json
import datetime

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

class SideNavCard(QFrame):
    clicked = pyqtSignal(int)
    
    def __init__(self, index, icon, title, parent=None):
        super().__init__(parent)
        self.index = index
        self.is_active = False
        
        self.setObjectName("NavCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(75)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 18px;")
        h_layout.addWidget(self.icon_lbl)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 13px; background: transparent;")
        h_layout.addWidget(self.title_lbl)
        h_layout.addStretch()
        layout.addLayout(h_layout)
        
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500; background: transparent;")
        layout.addWidget(self.summary_lbl)
        
        self.set_style()

    def set_active(self, active):
        self.is_active = active
        self.set_style()

    def set_style(self):
        if self.is_active:
            self.setStyleSheet("""
                #NavCard { 
                    background-color: #eff6ff; 
                    border: 1px solid #3b82f6; 
                    border-left: 4px solid #3b82f6;
                    border-radius: 8px; 
                }
            """)
            self.title_lbl.setStyleSheet("font-weight: 700; color: #2563eb; font-size: 13px; background: transparent;")
        else:
            self.setStyleSheet("""
                #NavCard { 
                    background-color: white; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 8px; 
                }
                #NavCard:hover { background-color: #f8fafc; border-color: #cbd5e1; }
            """)
            self.title_lbl.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 13px; background: transparent;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)
        
    def set_summary(self, text):
        self.summary_lbl.setText(text)

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
    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
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
        
        # Icon (Chevron)
        self.icon_lbl = QLabel("˃") # Small professional arrow
        self.icon_lbl.setFixedWidth(20)
        self.icon_lbl.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.icon_lbl)
        
        # Issue Title
        title_text = issue_data.get('category', 'Issue')
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
        # Pre-fill with template text/description
        self.desc_edit.setText(issue_data.get('description', ''))
        self.desc_edit.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 4px; padding: 8px;")
        self.desc_edit.setFixedHeight(120) # Min height
        self.content_layout.addWidget(self.desc_edit)
        
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
        data['description'] = self.desc_edit.toPlainText()
        try:
            # Clean up number formatting before parsing back to float
            clean_val = self.amount_edit.text().replace(',', '').replace('₹', '').strip()
            data['total_shortfall'] = float(clean_val)
        except:
            pass # Keep original if parse error
        return data

class ResultsContainer(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
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

    def add_result(self, issue_data):
        card = IssueCard(issue_data)
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
        else:
            self.status_icon.setText("⚪")
            self.status_container.setStyleSheet("background: #f1f5f9; border-radius: 13px; padding: 0 10px;")
            self.value_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 11px; background: transparent;")
            self.value_lbl.setText("Pending")
            
        if details:
            # Check if details is structured table data
            if isinstance(details, dict) and "summary_table" in details:
                # DEBUG: Popup to confirm data arrival
                QMessageBox.information(self, "Debug", f"Received Data for Point {self.number}")
                
                tbl_data = details["summary_table"]
                headers = tbl_data.get("headers", [])
                rows = tbl_data.get("rows", [])
                
                self.table_widget.setColumnCount(len(headers))
                self.table_widget.setRowCount(len(rows))
                self.table_widget.setHorizontalHeaderLabels(headers)
                self.table_widget.verticalHeader().setVisible(False)
                self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                # Resize first column to content if possible, but Stretch is usually cleaner
                
                for r, row_data in enumerate(rows):
                    # row_data is a dict {"col0": val, "col1": val...} based on parser
                    # Parser sends: { "col0": desc, "col1": cgst, ... }
                    self.table_widget.setItem(r, 0, QTableWidgetItem(str(row_data.get("col0", ""))))
                    
                    for c in range(1, 4): # CGST, SGST, IGST
                        val = row_data.get(f"col{c}", 0)
                        # Format as currency?
                        try:
                            val_str = f"₹ {val:,.0f}"
                        except:
                            val_str = str(val)
                            
                        item = QTableWidgetItem(val_str)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        self.table_widget.setItem(r, c, item)
                        
                self.table_widget.resizeRowsToContents()
                total_h = self.table_widget.verticalHeader().length() + self.table_widget.horizontalHeader().height() + 2
                self.table_widget.setFixedHeight(min(total_h, 300)) # Auto height cap
                
                self.table_widget.setVisible(True)
                self.details_lbl.setVisible(False)
                
            else:
                # Text fallback
                if isinstance(details, str):
                    self.details_lbl.setText(details)
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
            (1, "Outward Liability (3B vs GSTR-1)", "Comparison of Table 3.1(a)/(b) of GSTR-3B against Tables 4, 5, 6, 7, 9, 10 & 11 of GSTR-1."),
            (2, "RCM Liability (3B vs GSTR-2A/Rules)", "Inward supplies liable to reverse charge (RCM) vs ITC & Cash Ledger payments."),
            (3, "ISD Credit (3B vs GSTR-2A)", "ITC from Input Service Distributors (ISD) in Table 4(A)(4) vs GSTR-2A Table 7."),
            (4, "All Other ITC (3B vs GSTR-2A)", "ITC auto-drafted vs claimed for inward supplies from registered persons (Forward Charge)."),
            (5, "TDS/TCS Taxable Value (3B vs 2A)", "Liability in Table 3.1(a) vs Taxable values on which TDS/TCS was deducted (GSTR-2A Table 9)."),
            (6, "E-Way Bill Comparison (3B vs EWB)", "Liability declared in GSTR-3B vs Tax Liability generated in E-Way Bills (EWB Summary)."),
            (7, "Cancelled Suppliers ITC", "ITC claimed from suppliers whose GST registration has been cancelled retrospectively."),
            (8, "Non-Filing Suppliers ITC", "ITC claimed from suppliers who have not filed their GSTR-3B returns for the period(s)."),
            (9, "Section 16(4) ITC Rules", "ITC claimed after the statutory time limit (after Nov following the FY or Annual Return)."),
            (10, "Import of Goods (3B vs ICEGATE)", "ITC on Import of Goods (GSTR-3B Table 4(A)(1)) vs Auto-drafted values from ICEGATE (2A Table 10/11)."),
            (11, "Rule 42 & 43 ITC Reversals", "Verification whether required ITC reversals (Personal/Exempt usage) have been performed."),
            (12, "Interest Liability (Sec 50)", "Calculation of Interest on delayed filing of returns or delayed payment of tax."),
            (13, "Late Fee Payment (Sec 47)", "Verification of payment of late fees for delayed filing of GSTR-1 or GSTR-3B.")
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
            card.set_status('pending')

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
        if full_key in self.file_paths:
            uploader.set_file(os.path.basename(self.file_paths[full_key]))
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
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.parser = ScrutinyParser()
        self.asmt10 = ASMT10Generator()
        self.current_case_id = None
        self.current_case_data = {} # store validated metadata
        self.file_paths = {} # 'tax_liability', 'gstr_2b'
        self.scrutiny_results = []
        
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
            
    def resume_case(self, item):
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
            
            persisted_paths = add_details.get('file_paths', {})
            if persisted_paths:
                self.file_paths = persisted_paths
                # Update uploaders
                if 'tax_liability_yearly' in persisted_paths:
                    self.tax_group.set_file_path('tax_liability_yearly', persisted_paths['tax_liability_yearly'])
                    self.analyze_btn.setEnabled(True)
                
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
                    else:
                        issues = json.loads(saved_issues_str)

                    if isinstance(issues, list) and len(issues) > 0:
                        self.scrutiny_results = issues
                        self.populate_results_view(issues)
                        self.analyze_btn.setText("Re-Analyze Data")  
                        self.analyze_btn.setEnabled(True)
            except Exception as e:
                print(f"Error loading saved issues: {e}")
            self.stack.setCurrentIndex(1)
            self.recent_container.setVisible(False) # Hide recent list in workspace
            
    def setup_workspace_page(self):
        """Set up the scrutiny workspace with a Side-Accordion (Master-Detail) layout."""
        workspace_layout = QVBoxLayout(self.workspace_page)
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
        
        self.results_area = ResultsContainer()
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
        oc_lbl = QLabel("O.C. Number")
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
        nd_lbl = QLabel("Notice Date (ASMT-10 Date)")
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
        rd_lbl = QLabel("Last Date to Reply")
        rd_lbl.setStyleSheet("font-weight: bold; color: #475569;")
        form_layout.addWidget(rd_lbl)
        
        self.reply_date_edit = QDateEdit()
        self.reply_date_edit.setCalendarPopup(True)
        self.reply_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.reply_date_edit.setDate(QDate.currentDate().addDays(30))
        self.reply_date_edit.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; font-size: 14px;")
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
        
        self.asmt_issue_btn = QPushButton("✅ Issue & Register OC")
        self.asmt_issue_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none;")
        self.asmt_issue_btn.clicked.connect(self.finalize_asmt_notice)
        at_layout.addWidget(self.asmt_issue_btn)
        
        refresh_btn = QPushButton("🔄 Refresh Preview")
        refresh_btn.setStyleSheet("padding: 8px 15px; border: 1px solid #cbd5e1; border-radius: 6px; background: white; font-weight: 500;")
        refresh_btn.clicked.connect(self.refresh_asmt10_preview)
        at_layout.addWidget(refresh_btn)
        
        draft_layout.addWidget(asmt_toolbar)
        
        self.asmt_preview = QWebEngineView()
        self.asmt_preview.setStyleSheet("border: none;")
        self.asmt_preview.page().pdfPrintingFinished.connect(self.on_pdf_finished) # Connect print signal
        draft_layout.addWidget(self.asmt_preview)
        
        self.content_stack.addWidget(draft_page)

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
        
        # Trigger refresh if drafting selected
        if index == 3:
            self.refresh_asmt10_preview()

    def handle_file_upload(self, key, file_path):
        """Handle file upload callback."""
        if key == "tax_liability_yearly":
            # Perform strict validation
            exp_gstin = self.current_case_data.get('gstin', '')
            exp_fy = self.current_case_data.get('financial_year', '')
            
            is_valid, msg = self.parser.validate_metadata(file_path, exp_gstin, exp_fy)
            
            if not is_valid:
                QMessageBox.critical(self, "Validation Failed", f"The uploaded file does not match the case details.\n\n{msg}")
                return
            
            # If valid
            self.file_paths[key] = file_path
            self.tax_group.set_file_path(key, file_path)
            self.analyze_btn.setEnabled(True)
        else:
            # Route to dynamic groups
            self.file_paths[key] = file_path
            if key.startswith("gstr3b"):
                self.gstr3b_group.set_file_path(key, file_path)
            elif key.startswith("gstr1"):
                self.gstr1_group.set_file_path(key, file_path)
            elif key.startswith("gstr2b"):
                self.gstr2b_group.set_file_path(key, file_path)
            elif key.startswith("gstr9"):
                self.gstr9_group.set_file_path(key, file_path)

    def handle_file_delete(self, key):
        """Handle file deletion"""
        if key in self.file_paths:
            del self.file_paths[key]
            
        if key == "tax_liability_yearly":
            self.tax_group.set_file_path(key, None)
            self.analyze_btn.setEnabled(False) 
        elif key.startswith("gstr3b"):
            self.gstr3b_group.set_file_path(key, None)
        elif key.startswith("gstr1"):
            self.gstr1_group.set_file_path(key, None)
        elif key.startswith("gstr2b"):
            self.gstr2b_group.set_file_path(key, None)
        elif key.startswith("gstr9"):
            self.gstr9_group.set_file_path(key, None)

    def analyze_file(self):
        """Analyze the Tax Liability file"""
        file_path = self.file_paths.get('tax_liability_yearly')
        if not file_path:
            return
            
        try:
            self.analyze_btn.setText("Analyzing...")
            self.analyze_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Parse
            result = self.parser.parse_file(file_path, extra_files=self.file_paths)
            issues = result.get("issues", [])
            
            # Enrich with Master Templates (Smart Draft)
            issues = self.enrich_issues_with_templates(issues)
            
            self.scrutiny_results = issues
            self.populate_results_view(issues)
            
            self.analyze_btn.setText("Re-Analyze Data")
            self.analyze_btn.setEnabled(True)
            QMessageBox.information(self, "Analysis Complete", f"Analysis Complete. Analyzed 13 SOP points.")
            
        except Exception as e:
            self.analyze_btn.setText("Analyze SOP Points")
            self.analyze_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")

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
        
    def create_case(self):
        gstin = self.gstin_combo.currentText()
        fy = self.fy_combo.currentText()
        if not gstin or not fy:
            QMessageBox.warning(self, "Validation Error", "Please select both GSTIN and Financial Year.")
            return
        taxpayer = self.db.get_taxpayer(gstin)
        
        # Ensure clean slate
        self.file_paths.clear()
        if hasattr(self, 'tax_group'): self.tax_group.set_state("Yearly", {})
        if hasattr(self, 'gstr3b_group'): self.gstr3b_group.set_state("Yearly", {})
        if hasattr(self, 'gstr1_group'): self.gstr1_group.set_state("Yearly", {})
        if hasattr(self, 'gstr2b_group'): self.gstr2b_group.set_state("Yearly", {})
        if hasattr(self, 'gstr9_group'): self.gstr9_group.set_state("Yearly", {})
        self.clear_results_view()
        self.compliance_dashboard.reset_all()

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
            "initiating_section": "61", 
            "status": "Initiated", 
            "created_by": "System",
            "taxpayer_details": taxpayer # Store full snapshot
        }
        pid = self.db.create_proceeding(data)
        if pid:
            self.current_case_id = pid
            self.current_case_data = {'gstin': gstin, 'financial_year': fy}
            self.case_info_lbl.setText(f"{legal_name} | {gstin} | {fy}")
            self.switch_section(0) # Go to uploads
            self.stack.setCurrentIndex(1)
            self.recent_container.setVisible(False)
            self.load_recent_cases()
            QMessageBox.information(self, "Success", "Case created successfully! You can now proceed to upload files.")
        else:
            QMessageBox.critical(self, "Error", "Failed to create case database entry.")

    def close_case(self):
        self.current_case_id = None
        self.stack.setCurrentIndex(0)
        self.recent_container.setVisible(True) # Show recent list
        self.load_recent_cases()
        self.gstin_combo.setCurrentIndex(-1)
        self.details_frame.setVisible(False)
        self.clear_results_view()
        # Reset uploaders
        if hasattr(self, 'tax_group'): self.tax_group.set_state("Yearly", {})
        if hasattr(self, 'gstr3b_group'): self.gstr3b_group.set_state("Yearly", {})
        if hasattr(self, 'gstr1_group'): self.gstr1_group.set_state("Yearly", {})
        if hasattr(self, 'gstr2b_group'): self.gstr2b_group.set_state("Yearly", {})
        if hasattr(self, 'gstr9_group'): self.gstr9_group.set_state("Yearly", {})
        self.file_paths.clear()
        self.analyze_btn.setEnabled(False)



    def clear_results_view(self):
        self.summary_strip.update_summary("Unknown", "N/A")
        self.results_area.clear_results()

    def enrich_issues_with_templates(self, issues):
        """Fetches official legal language from DB for detected SOP issues."""
        enriched = []
        for issue in issues:
            desc = issue.get("description")
            # Find in DB by name
            master = self.db.get_issue_by_name(desc)
            if master:
                # Use master description/templates if available
                master_json = json.loads(master[1]) if isinstance(master[1], str) else master[1]
                issue['brief_facts'] = master_json.get('templates', {}).get('brief_facts', issue.get('description'))
                issue['category'] = master_json.get('category', issue.get('category'))
            enriched.append(issue)
        return enriched

    def populate_results_view(self, issues):
        """Populate the analysis results into collapsible cards."""
        self.results_area.clear_results()
        
        # 1. Update Summary Strip
        try:
            legal_name = self.current_case_data.get('legal_name', 'Unknown')
            # If still Unknown, try fetching again
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

        # 2. Visual check
        if not issues:
             return

        # 3. Create Cards
        self.compliance_dashboard.reset_all()
        
        # Map categories/descriptions to SOP Point Numbers
        sop_map = {
            "Outward Liability Mismatch (GSTR-1 vs 3B)": 1,
            "RCM Liability Mismatch": 2,
            "ISD ITC Mismatch": 3,
            "Excess ITC Claimed (3B vs 2B)": 4,
            "TDS/TCS Credit Mismatch": 5,
            "E-Way Bill vs GSTR-1 Mismatch": 6,
            "ITC from Cancelled Suppliers": 7,
            "ITC from Non-Filing Suppliers": 8,
            "Section 16(4) ITC Violation": 9,
            "Import ITC Mismatch (3B vs ICEGATE)": 10,
            "Rule 42/43 Reversal Mismatch": 11,
            "Interest on Delayed Filing": 12,
            "Late Fee Payment Under Section 47": 13
        }

        found_points = set()
        
        # DEBUG:
        QMessageBox.information(self, "Debug", f"Populating View with {len(issues)} issues")
        
        for issue in issues:
            shortfall = issue.get("total_shortfall", 0)
            
            # Only add to "Executive Summary" / Results List if there is an actual liability/issue
            if shortfall > 0:
                self.results_area.add_result(issue)
            
            # Update Dashboard Status (Always, even if 0 shortfall, to show "Matched")
            desc = issue.get("description")
            point_num = sop_map.get(desc)
            
            # DEBUG
            if not point_num:
               QMessageBox.warning(self, "Debug Mismatch", f"Description not found in map:\n'{desc}'")
            else:
               QMessageBox.information(self, "Debug Match", f"Mapped '{desc}' -> {point_num}")
               pass

            if point_num:
                found_points.add(point_num)
                status = "fail" if shortfall > 100 else "alert" if shortfall > 0 else "pass"
                self.compliance_dashboard.update_point(point_num, status, f"₹ {shortfall:,.0f}", details=issue)

        # Set others to 'pass' if the data for them was analyzed but no issue found
        # (For now, if analysis ran, we assume the ones NOT found are 'pass' if they are basic checks)
        for num in range(1, 14):
            if num not in found_points:
                # Basic checks depend on whether file was provided
                if num in [1, 2, 4, 10]: # Always in main file
                    self.compliance_dashboard.update_point(num, "pass", "Matched")
                elif num in [7, 8] and 'gstr_2a_invoices' in self.file_paths:
                    self.compliance_dashboard.update_point(num, "pass", "Clean")
                elif num == 6 and 'eway_bill_summary' in self.file_paths:
                    self.compliance_dashboard.update_point(num, "pass", "Matched")
                elif num == 5 and 'tds_tcs_credit' in self.file_paths:
                    self.compliance_dashboard.update_point(num, "pass", "Matched")
            
        # 4. Switch to Compliance Dashboard (Index 1) instead of Exec Summary
        self.switch_section(1)
        self.nav_cards[1].set_summary(f"{len(issues)} issues identified")


    def refresh_asmt10_preview(self):
        """Generates and displays the ASMT-10 HTML in the preview pane."""
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
        if not self.scrutiny_results:
            QMessageBox.warning(self, "No Data", "Please analyze a case first.")
            return
            
        # Ensure we have the latest HTML
        proc = self.db.get_proceeding(self.current_case_id)
        if not proc: return
        html = ASMT10Generator.generate_html(proc, self.scrutiny_results)
        
        if format_type == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Save ASMT-10 PDF", f"ASMT10_{proc['gstin']}.pdf", "PDF Files (*.pdf)")
            if path:
                # Use WebEngine's built-in printToPdf for true WYSIWYG
                layout = QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(15, 15, 15, 15), # 15mm margins
                    QPageLayout.Unit.Millimeter
                )
                self.asmt_preview.page().printToPdf(path, layout)
                # Success checks handled in on_pdf_finished
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
        # Default: Notice Date + 30 days
        self.reply_date_edit.setMinimumDate(date)
        self.reply_date_edit.setMaximumDate(date.addDays(30))
        self.reply_date_edit.setDate(date.addDays(30))

    def save_findings(self, silent=False):
        """Consolidated save method for both issue findings and case details."""
        if not self.current_case_id: return
        
        # 1. Gather issue findings
        updated_issues = self.results_area.get_all_data()
        self.scrutiny_results = updated_issues
        
        # 2. Gather Case Details
        oc_num = self.oc_num_input.text().strip()
        
        notice_date = self.notice_date_edit.date().toString("yyyy-MM-dd")
        reply_date = self.reply_date_edit.date().toString("yyyy-MM-dd")
        
        # 3. Update Database
        group_configs = {
            "gstr3b": {"frequency": self.gstr3b_group.selected_freq},
            "gstr1": {"frequency": self.gstr1_group.selected_freq},
            "gstr2b": {"frequency": self.gstr2b_group.selected_freq},
            "gstr9": {"frequency": self.gstr9_group.selected_freq}
        }
        
        add_details = {
            'file_paths': self.file_paths,
            'group_configs': group_configs
        }
        
        updates = {
            "selected_issues": updated_issues,
            "oc_number": oc_num,
            "notice_date": notice_date,
            "last_date_to_reply": reply_date,
            "additional_details": json.dumps(add_details)
        }
        
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
        """Finalize the ASMT-10 notice and register the OC number."""
        if not self.current_case_id: return
        
        oc_num = self.oc_num_input.text().strip()
        if not oc_num:
            QMessageBox.warning(self, "OC Number Required", "Please enter an OC number before issuing.")
            self.switch_section(2) # Go to case details
            self.oc_num_input.setFocus()
            return
            
        # 1. Save finding first
        self.save_findings(silent=True)
        
        proc = self.db.get_proceeding(self.current_case_id)
        
        # 2. Register OC
        oc_data = {
            'OC_Number': oc_num,
            'OC_Date': self.notice_date_edit.date().toString("yyyy-MM-dd"),
            'OC_Content': f"ASMT-10 Issued for GSTIN {proc.get('gstin','')}. Discrepancies noted in returns.",
            'OC_To': proc.get('legal_name', '')
        }
        
        if self.db.add_oc_entry(self.current_case_id, oc_data):
            # 3. Update Status
            self.db.update_proceeding(self.current_case_id, {"status": "ASMT-10 Issued"})
            QMessageBox.information(self, "Success", f"ASMT-10 Finalized and OC '{oc_num}' registered.")
            self.load_recent_cases()
        else:
            QMessageBox.critical(self, "Error", "Failed to register OC entry.")

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
