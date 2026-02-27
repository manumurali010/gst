
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTableWidget, QTableWidgetItem, QPushButton, QSizePolicy,
                            QFrame, QCheckBox, QAbstractItemView, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from src.utils.formatting import format_indian_number
from src.utils.number_utils import safe_int

from src.ui.components.modern_card import ModernCard

class FinalizationPanel(QWidget):
    """
    A reusable component for finalizing documents (DRC-01A, SCN, etc.)
    Displays a professional summary sheet with context, financials, and confirmation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.confirmed = False
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # --- COLLAPSIBLE SUMMARY CARD ---
        self.summary_card = ModernCard(title="Case Summary & Demand Details", collapsible=True)
        self.summary_card.content_layout.setContentsMargins(20, 20, 20, 20)
        self.summary_card.content_layout.setSpacing(15)
        
        # --- 1. RECEIPT HEADER (Context) ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left: Taxpayer Details
        left_layout = QVBoxLayout()
        self.tp_name_lbl = QLabel("Taxpayer Name")
        self.tp_name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        self.tp_gstin_lbl = QLabel("GSTIN: -")
        self.tp_trade_lbl = QLabel("Trade Name: -")
        
        left_layout.addWidget(self.tp_name_lbl)
        left_layout.addWidget(self.tp_gstin_lbl)
        left_layout.addWidget(self.tp_trade_lbl)
        header_layout.addLayout(left_layout)
        
        header_layout.addStretch()
        
        # Right: Case Context
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.case_id_lbl = QLabel("Case ID: -")
        self.fy_lbl = QLabel("F.Y.: -")
        self.section_lbl = QLabel("Section: -")
        
        # Style right labels
        for lbl in [self.case_id_lbl, self.fy_lbl, self.section_lbl]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            lbl.setStyleSheet("color: #7f8c8d; font-weight: 500;")
            right_layout.addWidget(lbl)
            
        header_layout.addLayout(right_layout)
        
        self.summary_card.addWidget(header_frame)
        
        # --- 2. DOCUMENT INFO BAR ---
        doc_bar = QFrame()
        doc_bar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-left: 4px solid #3498db;
                border-radius: 4px;
            }
        """)
        doc_layout = QHBoxLayout(doc_bar)
        
        self.doc_title_lbl = QLabel("SHOW CAUSE NOTICE")
        self.doc_title_lbl.setStyleSheet("font-weight: bold; color: #3498db; letter-spacing: 1px;")
        
        self.doc_no_lbl = QLabel("No: -")
        self.doc_date_lbl = QLabel("Date: -")
        self.doc_ref_lbl = QLabel("Ref OC: -")
        
        style_meta = "font-weight: bold; color: #34495e; margin-left: 15px;"
        self.doc_no_lbl.setStyleSheet(style_meta)
        self.doc_date_lbl.setStyleSheet(style_meta)
        self.doc_ref_lbl.setStyleSheet(style_meta)
        
        doc_layout.addWidget(self.doc_title_lbl)
        doc_layout.addStretch()
        doc_layout.addWidget(self.doc_no_lbl)
        doc_layout.addWidget(self.doc_date_lbl)
        doc_layout.addWidget(self.doc_ref_lbl)
        
        self.summary_card.addWidget(doc_bar)
        
        # --- 3. SCOPE SUMMARY (Issues) ---
        scope_lbl = QLabel("Issues Involved")
        scope_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #7f8c8d;")
        self.summary_card.addWidget(scope_lbl)
        
        self.issue_list_widget = QLabel("• Issue 1\n• Issue 2")
        self.issue_list_widget.setStyleSheet("margin-left: 10px; line-height: 1.5; color: #2c3e50;")
        self.issue_list_widget.setWordWrap(True)
        self.summary_card.addWidget(self.issue_list_widget)
        
        # --- 4. FINANCIAL SUMMARY TABLE ---
        table_lbl = QLabel("Demand Summary")
        table_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #7f8c8d;")
        self.summary_card.addWidget(table_lbl)
        
        self.amounts_table = QTableWidget()
        self.amounts_table.setColumnCount(4)
        self.amounts_table.setHorizontalHeaderLabels(["Act", "Tax", "Interest", "Penalty"])
        self.amounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.amounts_table.verticalHeader().setVisible(False)
        self.amounts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.amounts_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.amounts_table.setFixedHeight(120)
        self.amounts_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                gridline-color: #eee;
            }
            QHeaderView::section {
                background-color: #f1f2f6;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        self.summary_card.addWidget(self.amounts_table)
        
        # Grand Total Display
        total_frame = QFrame()
        total_frame.setStyleSheet("background-color: #2c3e50; border-radius: 6px;")
        total_layout = QHBoxLayout(total_frame)
        
        t_label = QLabel("Total Demand Liability")
        t_label.setStyleSheet("color: #bdc3c7; font-weight: bold;")
        
        self.grand_total_lbl = QLabel(format_indian_number(0, prefix_rs=True))
        self.grand_total_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.grand_total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        total_layout.addWidget(t_label)
        total_layout.addWidget(self.grand_total_lbl)
        self.summary_card.addWidget(total_frame)
        
        self.summary_card.addWidget(total_frame)
        
        self.layout.addWidget(self.summary_card)
        
        # --- PREVIEW BROWSER (New) ---
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self.browser = QWebEngineView()
        self.browser.setMinimumHeight(120)
        self.browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.browser.setStyleSheet("border: 1px solid #bdc3c7;")
        self.layout.addWidget(self.browser)
        
        # Set individual stretch factors
        self.layout.setStretch(0, 0) # Summary Card
        self.layout.setStretch(1, 1) # Browser
        
        # --- 5. ACTION FOOTER (Always Visible) ---
        footer_frame = QFrame()
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(0, 5, 0, 5)
        
        # Save Draft Button
        self.save_btn = QPushButton("💾 Save Draft")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                color: #475569;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #3498db;
                color: #3498db;
            }
        """)
        footer_layout.addWidget(self.save_btn)

        # Refresh Preview Button
        self.refresh_btn = QPushButton("🔄 Refresh Preview")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #3498db;
                color: #3498db;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        footer_layout.addWidget(self.refresh_btn)
        
        # Preview Button (PDF)
        self.pdf_btn = QPushButton("⬇️ Download Draft PDF")
        self.pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #e74c3c;
                color: #e74c3c;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fdf2f2;
            }
        """)
        footer_layout.addWidget(self.pdf_btn)

        # DOCX Button
        self.docx_btn = QPushButton("⬇️ Download Draft Word")
        self.docx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.docx_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #3498db;
                color: #3498db;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ebf5fb;
            }
        """)
        footer_layout.addWidget(self.docx_btn)
        
        footer_layout.addStretch()
        
        # Confirmation
        right_action_layout = QVBoxLayout()
        right_action_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.confirm_chk = QCheckBox("I verify that the details above are correct and final.")
        self.confirm_chk.setStyleSheet("font-weight: 500; color: #e74c3c;")
        self.confirm_chk.toggled.connect(self.on_verify_toggled)
        
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("border: none; color: #7f8c8d; font-weight: bold;")
        
        self.finalize_btn = QPushButton("Confirm & Finalize")
        self.finalize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.finalize_btn.setEnabled(False) # Disabled by default
        self.finalize_btn.setStyleSheet("""
            QPushButton {
                background-color: #bdc3c7; /* Disabled Gray */
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:enabled {
                background-color: #27ae60; /* Green */
            }
            QPushButton:enabled:hover {
                background-color: #219150;
            }
        """)
        
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.finalize_btn)
        
        right_action_layout.addWidget(self.confirm_chk)
        right_action_layout.addLayout(btn_row)
        
        footer_layout.addLayout(right_action_layout)
        self.layout.addWidget(footer_frame)

    def on_verify_toggled(self, checked):
        self.finalize_btn.setEnabled(checked)

    def load_data(self, proceeding_data, issues_list, doc_type="SCN", doc_no="", doc_date="", ref_no=""):
        """
        Populate the panel with data.
        proceeding_data: Dict with 'taxpayer' keys, 'section', 'financial_year', etc.
        issues_list: List of issue dicts/objects with 'issue_name' and tax breakdown.
        """
        # 1. Taxpayer & Case
        # Priority: 1. taxpayer_details (nested), 2. taxpayer (nested), 3. proceeding_data (root)
        taxpayer = proceeding_data.get('taxpayer_details', proceeding_data.get('taxpayer', {}))
        
        # Helper to get value from nested source or root source
        def get_val(key):
            val = taxpayer.get(key)
            if not val or val == '-':
                val = proceeding_data.get(key, '-')
            return val
            
        trade_name = get_val('trade_name')
        if trade_name == '-': trade_name = 'Unknown Taxpayer'
            
        self.tp_name_lbl.setText(trade_name)
        self.tp_gstin_lbl.setText(f"GSTIN: {get_val('gstin')}")
        self.tp_trade_lbl.setText(f"Legal Name: {get_val('legal_name')}")
        
        self.case_id_lbl.setText(f"Case ID: {proceeding_data.get('case_id', '-')}")
        self.fy_lbl.setText(f"F.Y.: {proceeding_data.get('financial_year', '-')}")
        
        # Format Section nicely
        sections = proceeding_data.get('section', [])
        if isinstance(sections, list):
            sec_str = ", ".join(sections)
        else:
            sec_str = str(sections)
        self.section_lbl.setText(f"Section: {sec_str}")
        
        # 2. Document Info
        if doc_type == "DRC-01A":
            self.doc_title_lbl.setText("FORM GST DRC-01A")
            self.doc_title_lbl.setStyleSheet("font-weight: bold; color: #e67e22; letter-spacing: 1px;")
        else:
            self.doc_title_lbl.setText("SHOW CAUSE NOTICE")
            self.doc_title_lbl.setStyleSheet("font-weight: bold; color: #3498db; letter-spacing: 1px;")
            
        self.doc_no_lbl.setText(f"No: {doc_no}")
        self.doc_date_lbl.setText(f"Date: {doc_date}")
        
        if ref_no and ref_no != "-":
            self.doc_ref_lbl.setVisible(True)
            self.doc_ref_lbl.setText(f"Ref OC: {ref_no}")
        else:
            self.doc_ref_lbl.setVisible(False)
        
        # 3. Issues List
        issue_names = []
        act_totals = {
            'CGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'SGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'IGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'Cess': {'tax': 0, 'interest': 0, 'penalty': 0}
        }
        
        grand_total = 0
        
        # Handle both list of dicts (from DB) or list of objects (IssueCard)
        for issue in issues_list:
            # Name
            name = "Unknown Issue"
            if isinstance(issue, dict):
                # Saved record format
                name = issue.get('template_name', issue.get('issue_id', 'Issue')) # Might need to fetch name
                # If we passed raw cards or structured data with names, use that
                if 'issue_name' in issue: name = issue['issue_name']
                
                # Breakdown
                # If it's a raw dict from get_case_issues, 'data' has the variables
                # But calculating tax from raw vars is hard here without logic.
                # Ideally, we pass the *calculated* breakdown to this panel.
                breakdown = issue.get('tax_breakdown', {})
                
            elif hasattr(issue, 'template'):
                # IssueCard object
                name = issue.template.get('issue_name', 'Issue')
                breakdown = issue.get_tax_breakdown() if hasattr(issue, 'get_tax_breakdown') else {}
            
            issue_names.append(f"• {name}")
            
            # Aggregate Totals
            for act, vals in breakdown.items():
                if act in act_totals:
                    t = safe_int(vals.get('tax', 0))
                    i = safe_int(vals.get('interest', 0))
                    p = safe_int(vals.get('penalty', 0))
                    
                    act_totals[act]['tax'] += t
                    act_totals[act]['interest'] += i
                    act_totals[act]['penalty'] += p
                    
                    grand_total += (t + i + p)

        self.issue_list_widget.setText("\n".join(issue_names) if issue_names else "No specific issues selected.")
        
        # 4. Populate Table
        self.amounts_table.setRowCount(0)
        for act, totals in act_totals.items():
            if totals['tax'] > 0 or totals['interest'] > 0 or totals['penalty'] > 0:
                r = self.amounts_table.rowCount()
                self.amounts_table.insertRow(r)
                self.amounts_table.setItem(r, 0, QTableWidgetItem(act))
                self.amounts_table.setItem(r, 1, QTableWidgetItem(format_indian_number(totals['tax'])))
                self.amounts_table.setItem(r, 2, QTableWidgetItem(format_indian_number(totals['interest'])))
                self.amounts_table.setItem(r, 3, QTableWidgetItem(format_indian_number(totals['penalty'])))
        
        # 5. Grand Total
        self.grand_total_lbl.setText(format_indian_number(grand_total, prefix_rs=True))

    def clear_data(self):
        """Reset the panel to default state"""
        self.tp_name_lbl.setText("Taxpayer Name")
        self.tp_gstin_lbl.setText("GSTIN: -")
        self.tp_trade_lbl.setText("Trade Name: -")
        self.case_id_lbl.setText("Case ID: -")
        self.fy_lbl.setText("F.Y.: -")
        self.section_lbl.setText("Section: -")
        self.doc_no_lbl.setText("No: -")
        self.doc_date_lbl.setText("Date: -")
        self.doc_ref_lbl.setText("Ref OC: -")
        self.issue_list_widget.setText("-")
        self.amounts_table.setRowCount(0)
        self.grand_total_lbl.setText(format_indian_number(0, prefix_rs=True))
        self.finalize_btn.setEnabled(False)
        self.confirm_chk.setChecked(False)

    def set_read_only(self, read_only=True):
        """Toggle read-only mode (hide action footer)"""
        if read_only:
            # Hide the entire footer layout items
            self.save_btn.setVisible(False)
            self.refresh_btn.setVisible(False)
            self.pdf_btn.setVisible(False)
            self.docx_btn.setVisible(False)
            self.confirm_chk.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.finalize_btn.setVisible(False)
        else:
            self.save_btn.setVisible(True)
            self.refresh_btn.setVisible(True)
            self.pdf_btn.setVisible(True)
            self.docx_btn.setVisible(True)
            self.confirm_chk.setVisible(True)
            self.cancel_btn.setVisible(True)
            self.finalize_btn.setVisible(True)

    def set_preview_html(self, html_content):
        """Render the HTML preview in the embedded browser"""
        if hasattr(self, 'browser'):
            self.browser.setHtml(html_content)
