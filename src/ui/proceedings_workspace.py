from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QStackedWidget, QSplitter, QScrollArea, QTextEdit, QTextBrowser,
                             QMessageBox, QFrame, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, QLineEdit, QFileDialog, QDialog, QGridLayout, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QDate, pyqtSignal
from PyQt6 import QtCore
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence, QIcon, QResizeEvent
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from src.database.db_manager import DatabaseManager
from src.utils.preview_generator import PreviewGenerator
from src.ui.collapsible_box import CollapsibleBox
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard
from src.ui.issue_card import IssueCard
from src.ui.adjudication_setup_dialog import AdjudicationSetupDialog
from src.ui.components.side_nav_card import SideNavCard # Canonical import
from src.ui.components.finalization_panel import FinalizationPanel
from src.services.asmt10_generator import ASMT10Generator
import os
import json
import copy
from jinja2 import Template, Environment, FileSystemLoader
import datetime

class ASMT10ReferenceDialog(QDialog):
    """
    Modal Dialog for viewing ASMT-10 as a reference while drafting.
    """
    def __init__(self, parent, html):
        super().__init__(parent)
        self.setWindowTitle("🔒 Finalised ASMT-10 (Read-Only Reference)")
        self.resize(1000, 800)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll Area for preview
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Close Button
        btn_close = QPushButton("Close Reference")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dcdde1;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        layout.addWidget(btn_close)
        
        # Render HTML to images
        if html:
            images = PreviewGenerator.generate_preview_image(html, all_pages=True)
            if images:
                for img_bytes in images:
                    pixmap = PreviewGenerator.get_qpixmap_from_bytes(img_bytes)
                    if pixmap:
                        lbl = QLabel()
                        # Fixed width for modal
                        lbl.setPixmap(pixmap.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation))
                        lbl.setStyleSheet("border: 1px solid #ccc; background-color: white;")
                        container_layout.addWidget(lbl)
            else:
                container_layout.addWidget(QLabel("Preview Generation Failed"))
        else:
            container_layout.addWidget(QLabel("No ASMT-10 Data Found"))

class ProceedingsWorkspace(QWidget):
    def __init__(self, navigate_callback, sidebar=None, proceeding_id=None):
        super().__init__()
        print("ProceedingsWorkspace: init start")
        self.navigate_callback = navigate_callback
        self.sidebar = sidebar # Store sidebar reference
        self.db = DatabaseManager()
        self.db.init_sqlite()
        print("ProceedingsWorkspace: DB initialized")
        
        self.proceeding_id = proceeding_id
        self.proceeding_data = {}
        self.is_hydrated = False
        
        # Debounce Timer
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(500)
        self.preview_timer.timeout.connect(self.update_preview)
        
        self.asmt10_zoom_level = 1.0
        self.asmt10_show_letterhead = True
        
        # Collapsible Preview State
        self.preview_visible = False
        
        self.active_scn_step = 0
        self.scn_workflow_phase = "METADATA" # Authority state: METADATA | DRAFTING
        
        print("ProceedingsWorkspace: calling init_ui")
        self.init_ui()
        print("ProceedingsWorkspace: init_ui done")
        
        
        if self.proceeding_id:
            self.load_proceeding(self.proceeding_id)

    def init_ui(self):
        print("ProceedingsWorkspace: init_ui start")
        self.setObjectName("ProceedingsWorkspace")
        
        # Load Stylesheet
        try:
            style_path = os.path.join(os.path.dirname(__file__), "styles", "proceedings.qss")
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. Main Workspace Splitter (Context-Driven)
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setHandleWidth(1)
        self.workspace_splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")
        
        # Center Pane: Content (Stacked)
        self.content_stack = QStackedWidget()
        
        # Tab 0: Summary
        print("ProceedingsWorkspace: creating summary tab")
        self.summary_tab = self.create_summary_tab()
        self.content_stack.addWidget(self.summary_tab)
        
        # Tab 1: DRC-01A Editor
        print("ProceedingsWorkspace: creating drc01a tab")
        self.drc01a_tab = self.create_drc01a_tab()
        self.content_stack.addWidget(self.drc01a_tab)

        # Tab 1.5: ASMT-10 (Read-Only)
        print("ProceedingsWorkspace: creating asmt10 tab")
        self.asmt10_tab = self.create_asmt10_tab()
        self.content_stack.addWidget(self.asmt10_tab)
        
        # Tab 2: SCN (Show Cause Notice)
        print("ProceedingsWorkspace: creating scn tab")
        self.scn_tab = self.create_scn_tab()
        self.content_stack.addWidget(self.scn_tab)
        
        # Tab 3: PH Intimation (Personal Hearing)
        print("ProceedingsWorkspace: creating ph_intimation tab")
        self.ph_tab = self.create_ph_intimation_tab()
        self.content_stack.addWidget(self.ph_tab)
        
        # Tab 4: Order
        print("ProceedingsWorkspace: creating order_tab")
        self.order_tab = self.create_order_tab()
        self.content_stack.addWidget(self.order_tab)
        print("ProceedingsWorkspace: order_tab added")
        
        # Placeholders for Documents and Timeline
        for i, name in enumerate(["Documents", "Timeline"]):
            lbl = QLabel(f"{name} - Coming Soon")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 12pt; color: #7f8c8d;")
            self.content_stack.addWidget(lbl)
            
        # 2a. Central Container (Header + Content Stack)
        self.central_container_widget = QWidget()
        self.central_container_layout = QVBoxLayout(self.central_container_widget)
        self.central_container_layout.setContentsMargins(0, 0, 0, 0)
        self.central_container_layout.setSpacing(0)

        # Header
        self.central_header = QWidget()
        self.central_header.setFixedHeight(40)
        self.central_header.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #e0e0e0;")
        header_layout = QHBoxLayout(self.central_header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        self.context_title_lbl = QLabel("") # Dynamic Title
        self.context_title_lbl.setStyleSheet("font-weight: bold; color: #5f6368;")
        
        # Preview Toggle Button
        self.btn_preview_toggle = QPushButton("Show Preview")
        self.btn_preview_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_toggle.setCheckable(True)
        self.btn_preview_toggle.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: #5f6368;
                font-weight: 500;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
                color: #1a73e8;
            }
            QPushButton:checked {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        self.btn_preview_toggle.clicked.connect(self.toggle_preview)
        
        header_layout.addWidget(self.context_title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_preview_toggle)
        
        self.central_container_layout.addWidget(self.central_header)
        self.central_container_layout.addWidget(self.content_stack)

        self.central_container_layout.addWidget(self.central_header)
        self.central_container_layout.addWidget(self.content_stack)

        self.layout.addWidget(self.central_container_widget)
        
        # 3. Floating Preview Pane (Overlay)
        # Parented to self, but NOT added to layout
        print("ProceedingsWorkspace: creating preview_pane")
        self.create_preview_pane()
        print("ProceedingsWorkspace: preview_pane created")
        
        # Setup Shortcuts
        self.shortcut_preview = QShortcut(QKeySequence("Ctrl+P"), self)
        self.shortcut_preview.activated.connect(self.toggle_preview)
        
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.close_preview_on_esc)

        # Set initial state
        self.preview_container.hide()
        self.btn_preview_toggle.setChecked(False)
        
        # Initial Context
        self.apply_context_layout("summary")

    def handle_sidebar_action(self, action):
        """Switch tabs based on sidebar action"""
        action_map = {
            "summary": 0,
            "drc01a": 1,
            "asmt10": 2, # Stacks at index 2 (summary=0, drc01a=1, asmt10=2, scn=3...)
            "scn": 3,
            "ph": 4,
            "order": 5,
            "documents": 6,
            "timeline": 7
        }
        
        # Safety Check (Fail Fast)
        is_scrutiny = bool(self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id'))
        if is_scrutiny and action == "drc01a":
             raise RuntimeError("DRC-01A must not exist for scrutiny-origin adjudication")

        if action in action_map:
            index = action_map[action]
            self.content_stack.setCurrentIndex(index)
            
            # Apply Layout context
            self.apply_context_layout(action)
            
            # Auto-load issues when switching to SCN tab
            if action == "scn":
                self.load_scn_issue_templates()
                # The actual load_scn_issues() is now triggered by on_scn_page_changed for Step 2
            
            # Trigger preview update
            if self.preview_visible:
                self.update_preview(action)

    def toggle_preview(self):
        """Toggle the visibility of the floating preview pane."""
        self.preview_visible = not self.preview_visible
        
        if self.preview_visible:
            self.btn_preview_toggle.setText("Hide Preview")
            self.btn_preview_toggle.setToolTip("Hide Live Preview (Ctrl+P / Esc)")
            
            # Show and Raise
            self.update_preview_geometry()
            self.preview_container.setVisible(True)
            self.preview_container.raise_()
            
            # Trigger immediate update
            self.update_preview()
        else:
            self.btn_preview_toggle.setText("Show Preview")
            self.btn_preview_toggle.setToolTip("Show Live Preview (Ctrl+P)")
            self.preview_container.hide()
            
        self.btn_preview_toggle.setChecked(self.preview_visible)

    def close_preview_on_esc(self):
        """Close preview if visible when Esc is pressed"""
        if self.preview_visible:
            self.toggle_preview()
            
    def resizeEvent(self, event: QResizeEvent):
        """Update floating preview geometry on resize"""
        super().resizeEvent(event)
        if self.preview_visible:
            self.update_preview_geometry()
            
    def update_preview_geometry(self):
        """Calculate and apply geometry for the floating preview panel"""
        if not hasattr(self, 'preview_container') or not self.preview_visible:
            return
            
        # Get dimensions
        ws_width = self.width()
        ws_height = self.height()
        header_height = self.central_header.height() if hasattr(self, 'central_header') else 40
        
        # Calculate Preview Width (40% of workspace, clamped)
        target_width = int(ws_width * 0.40)
        target_width = max(400, min(target_width, 800))
        
        # Geometry
        x = ws_width - target_width
        y = header_height
        h = ws_height - header_height
        
        self.preview_container.setGeometry(x, y, target_width, h)

    def apply_context_layout(self, context_key):
        """
        Enforce single legal context layout rules.
        """
        # Define rules
        # Context -> (DraftVisible, PreviewAllowed)
        rules = {
            "summary":   (True,  False),
            "asmt10":    (True,  False), 
            "scn":       (True,  True),
            "drc01a":    (True,  True),
            "ph":        (True,  True),
            "order":     (True,  True),
        }
        
        draft_visible, preview_allowed = rules.get(context_key, (True, False))
        
        # 1. Force Preview Hidden on Context Switch (Review Requirement)
        self.preview_visible = False
        self.preview_container.hide()
        self.btn_preview_toggle.setChecked(False)
        self.btn_preview_toggle.setText("Show Preview")
            
        # 2. Toggle Button Visibility/State
        self.btn_preview_toggle.setVisible(preview_allowed)
        self.shortcut_preview.setEnabled(preview_allowed)
        
        # 3. Dynamic Title (Optional)
        titles = {
            "scn": "Show Cause Notice Drafting",
            "drc01a": "DRC-01A Drafting",
            "summary": "Case Summary",
            "asmt10": "ASMT-10 Reference",
            "ph": "Personal Hearing Intimation", 
            "order": "Adjudication Order"
        }
        self.context_title_lbl.setText(titles.get(context_key, ""))
        
        self.content_stack.setVisible(draft_visible)

    def create_asmt10_tab(self):
        """Create Read-Only ASMT-10 Tab with Professional Document Framing"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Document Toolbar
        self.asmt10_toolbar = QFrame()
        self.asmt10_toolbar.setFixedHeight(50)
        self.asmt10_toolbar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e0e6ed;
            }
        """)
        toolbar_layout = QHBoxLayout(self.asmt10_toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.asmt10_title_lbl = QLabel("🔒 Finalised ASMT-10 — Read-Only Reference")
        self.asmt10_title_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #1e293b;")
        title_vbox.addWidget(self.asmt10_title_lbl)
        
        self.asmt10_meta_lbl = QLabel("OC No. - | Date: -")
        self.asmt10_meta_lbl.setStyleSheet("font-size: 8pt; color: #64748b;")
        title_vbox.addWidget(self.asmt10_meta_lbl)
        
        toolbar_layout.addLayout(title_vbox)
        toolbar_layout.addStretch()
        
        # Letterhead Toggle
        self.asmt10_lh_cb = QCheckBox("Show Letterhead")
        self.asmt10_lh_cb.setChecked(True)
        self.asmt10_lh_cb.stateChanged.connect(self._on_asmt10_lh_toggled)
        toolbar_layout.addWidget(self.asmt10_lh_cb)
        
        toolbar_layout.addSpacing(20)
        
        # Zoom Controls (Now controls font size / scale in TextBrowser if possible, 
        # or we just remove them because TextBrowser handles standard zoom via Ctrl+Wheel)
        # Keeping them for consistency, but mapping to zoomIn/zoomOut
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)
        
        for icon, cmd in [("➖", self._zoom_asmt10_out), ("100%", self._zoom_asmt10_reset), ("➕", self._zoom_asmt10_in)]:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    font-size: 9pt;
                }
                QPushButton:hover { background-color: #f1f5f9; }
            """)
            btn.clicked.connect(cmd)
            zoom_layout.addWidget(btn)
        
        toolbar_layout.addLayout(zoom_layout)
        layout.addWidget(self.asmt10_toolbar)
        
        # 2. Native HTML Preview (QTextBrowser)
        # [FIX] Switched from Image/WeasyPrint to Native Browser for robustness
        self.asmt10_browser = QTextBrowser()
        self.asmt10_browser.setStyleSheet("border: none; background-color: #525659;") 
        self.asmt10_browser.setOpenExternalLinks(False)
        self.asmt10_browser.zoomIn(0) # Reset zoom to normal
        
        layout.addWidget(self.asmt10_browser)
        
        return widget

    def render_asmt10_preview(self, source_scrutiny_id):
        """
        Fetch structured Scrutiny Data and render ASMT-10 Preview.
        Strictly Read-Only and Runtime Generated.
        """
        scrutiny_data = self.db.get_scrutiny_case_data(source_scrutiny_id)
        
        if not scrutiny_data:
            self.asmt10_browser.setHtml("<h3 style='color:white; text-align:center; margin-top:50px;'>Source Scrutiny Data not found.</h3>")
            return

        # Update Toolbar Meta
        oc = scrutiny_data.get('oc_number', 'DRAFT')
        dt = scrutiny_data.get('asmt10_finalised_on', '-')
        self.asmt10_meta_lbl.setText(f"OC No. {oc} | Date: {dt}")
        
        try:
            case_info = {
                'case_id': scrutiny_data.get('case_id'),
                'financial_year': scrutiny_data.get('financial_year'),
                'section': scrutiny_data.get('section'),
                'notice_date': dt,
                'oc_number': oc,
                'last_date_to_reply': scrutiny_data.get('last_date_to_reply', 'N/A')
            }
            
            taxpayer = scrutiny_data.get('taxpayer_details', {})
            if not isinstance(taxpayer, dict): taxpayer = {}
            
            # [ENRICHMENT] Strictly preview-only: Fetch fresh taxpayer details
            # Ensure we use the correct key for GSTIN (handle both 'gstin' and 'taxpayer_gstin')
            gstin = scrutiny_data.get('gstin') or scrutiny_data.get('taxpayer_gstin')
            if not gstin and taxpayer:
                 gstin = taxpayer.get('GSTIN') or taxpayer.get('gstin')
                 
            if gstin:
                fresh_taxpayer = self.db.get_taxpayer(gstin)
                if fresh_taxpayer:
                    # Update preview dictionary with fresh data if missing or N/A
                    if taxpayer.get('Legal Name', 'N/A') in ['N/A', '', None]:
                        taxpayer['Legal Name'] = fresh_taxpayer.get('Legal Name', taxpayer.get('Legal Name', 'N/A'))
                    
                    if taxpayer.get('Address', 'Address not available') in ['Address not available', '', None]:
                         taxpayer['Address'] = (fresh_taxpayer.get('Address') or 
                                               fresh_taxpayer.get('Address of Principal Place of Business') or 
                                               taxpayer.get('Address', 'Address not available'))
                    
                # Also update gstin in case_info for the header
                case_info['gstin'] = gstin
            
            # Fix double fetch logic in original code
            issues = scrutiny_data.get('selected_issues', [])
            
            # Handle new parser format which returns {"metadata":..., "issues": [...]}
            if isinstance(issues, dict) and 'issues' in issues:
                 issues = issues['issues']
            
            generator = ASMT10Generator()
            full_data = case_info.copy()
            full_data['taxpayer_details'] = taxpayer
            full_data['gstin'] = gstin
            
            # [ALIGNMENT] Use "legacy" style mode for visual parity with Scrutiny module
            html_content = generator.generate_html(full_data, issues, for_preview=True, show_letterhead=self.asmt10_show_letterhead, style_mode="legacy")
            
            # Update the browser directly
            self.asmt10_browser.setHtml(html_content)
                
        except Exception as e:
            print(f"ASMT-10 Render Error: {e}")
            self.asmt10_browser.setHtml(f"<h3 style='color:red; text-align:center;'>Error rendering ASMT-10: {e}</h3>")

    def _on_asmt10_lh_toggled(self, state):
        self.asmt10_show_letterhead = (state == Qt.CheckState.Checked.value or state == True)
        source_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
        if source_id:
            self.render_asmt10_preview(source_id)

    def _zoom_asmt10_in(self):
        self.asmt10_browser.zoomIn(1)

    def _zoom_asmt10_out(self):
        self.asmt10_browser.zoomOut(1)

    def _zoom_asmt10_reset(self):
        # Reset is tricky without tracking, but we can set font size or just zoom to default
        # QTextBrowser doesn't have absolute zoom set.
        pass # Todo: Implement reset logic if needed

    def _show_preview_error(self, message):
         self.asmt10_browser.setHtml(f"<h3 style='color:red; text-align:center;'>{message}</h3>")

    def _clear_asmt10_preview(self):
        """Helper to safely clear the ASMT-10 page container"""
        if not hasattr(self, 'asmt10_page_layout'):
            return
        while self.asmt10_page_layout.count():
            child = self.asmt10_page_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _ensure_dict(self, data):
        """Helper to safely ensure data is a dict, handling double-serialized JSON strings."""
        if isinstance(data, dict):
            return data
        if not data:
            return {}
        
        # If it's a string, try to parse
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                # Recursion to handle double-encoding (e.g. '"{\"a\":1}"')
                return self._ensure_dict(parsed)
            except Exception:
                # If parsing fails, return empty dict or log error? 
                # Better to return empty dict to prevent app crash on access
                print(f"Warning: Failed to parse JSON data: {data}")
                return {}
        
        return {}

    def _clear_scn_workspace_state(self):
        """Reset SCN workspace to pristine state before loading new data."""
        if hasattr(self, 'scn_issue_cards'):
            for card in self.scn_issue_cards:
                card.setParent(None)
                if hasattr(self, 'scn_issues_layout'):
                    self.scn_issues_layout.removeWidget(card)
                card.deleteLater()
            self.scn_issue_cards = []
            
        # Reset Workflow Flags
        self.scn_issues_initialized = False
        self.scn_workflow_phase = "METADATA"

    def load_proceeding(self, pid):
        # [FIX] State Persistence: Clear existing workspace first
        self._clear_scn_workspace_state()
        
        self.is_hydrated = False
        self.proceeding_id = pid
        self.proceeding_data = self.db.get_proceeding(pid)
        
        if not self.proceeding_data:
            # Critical Fix: Ensure data is never None
            self.proceeding_data = {}
            QMessageBox.critical(self, "Error", "Proceeding not found!")
            self.update_preview() # Clear preview
            return

        # CRITICAL FIX: Robust JSON Deserialization
        # Fixes legacy double-serialization issues by recursively parsing strings
        self.proceeding_data['additional_details'] = self._ensure_dict(self.proceeding_data.get('additional_details'))
        self.proceeding_data['taxpayer_details'] = self._ensure_dict(self.proceeding_data.get('taxpayer_details'))
        

            
        # Fetch associated documents
        self.documents = self.db.get_documents(pid)
            
        # Update UI
        self.update_summary_tab()
        
        source_scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
        
        if source_scrutiny_id:
            # Populate ASMT-10 Read-Only Preview
            self.render_asmt10_preview(source_scrutiny_id)
            # Scrutiny-origin: Detach DRC-01A Finalization
            self._detach_drc01a_finalization_panel()
        else:
            # Direct adjudication: Attach DRC-01A Finalization
            self._attach_drc01a_finalization_panel()
        
        # Restore Draft State (Issues, Amounts, etc.)
        self.restore_draft_state()
        
        # Hydrate SCN Initialization Flag (Authoritative from DB)
        self.scn_issues_initialized = False
        add_details = self.proceeding_data.get('additional_details', {})
        if isinstance(add_details, str):
            try: add_details = json.loads(add_details)
            except: add_details = {}
        
        self.scn_issues_initialized = add_details.get('scn_issues_initialized', False)
        print(f"ProceedingsWorkspace: SCN Hydration State = {self.scn_issues_initialized}")

        # Check for existing generated documents to toggle View Mode
        self.check_existing_documents()
        
        # --- Adjudication Setup Check ---
        if self.proceeding_data.get('is_adjudication') and not self.proceeding_data.get('adjudication_section'):
            print("Adjudication Setup Required: Launching Dialog")
            dlg = AdjudicationSetupDialog(self)
            if dlg.exec():
                # Save Section
                section = dlg.selected_section
                success = self.db.update_adjudication_case(pid, {'adjudication_section': section})
                if success:
                    # Update local data
                    self.proceeding_data['adjudication_section'] = section
                    # Also set initiating_section for compatibility if needed, but preference is distinct field
                    self.proceeding_data['initiating_section'] = section 
                    QMessageBox.information(self, "Setup Complete", f"Case initialized under Section {section}.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save adjudication section.")
            else:
                QMessageBox.warning(self, "Setup Incomplete", "SCN drafting is disabled until section is selected.")
                # We should probably disable tabs here or mark as incomplete
        
        self.is_hydrated = True
        self.trigger_preview()

    def create_preview_pane(self):
        """Create the universal floating preview pane (Overlay)."""
        self.preview_pane_widget = QFrame(self) # Parent directly to self (overlay)
        self.preview_pane_widget.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Floating Styling
        self.preview_pane_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-left: 1px solid #dadce0;
                border-bottom: 1px solid #dadce0;
                /* [FIX] Pure White, No Shadow as requested */
            }
        """)
        
        # [FIX] Removed Shadow Effect
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(15)
        # shadow.setOffset(-2, 0)
        # shadow.setColor(Qt.GlobalColor.lightGray) # Using global color enum
        # self.preview_pane_widget.setGraphicsEffect(shadow)
        
        # Focus Safety (Critical)
        self.preview_pane_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview_pane_widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.preview_pane_layout = QVBoxLayout(self.preview_pane_widget)
        self.preview_pane_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with Options
        preview_header = QHBoxLayout()
        preview_header.setContentsMargins(10, 5, 10, 5)
        self.preview_label_widget = QLabel("Live Preview")
        self.preview_label_widget.setStyleSheet("font-weight: bold; color: #202124; border: none; background: transparent;")
        
        self.show_letterhead_cb = QCheckBox("Show Letterhead")
        self.show_letterhead_cb.setChecked(True)
        self.show_letterhead_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_letterhead_cb.setStyleSheet("background: transparent; border: none;")
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview)
        
        # Close Button X (Small utility)
        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedWidth(24)
        btn_close.setStyleSheet("""
            QPushButton { border: none; background: transparent; color: #5f6368; font-weight: bold; }
            QPushButton:hover { background-color: #f1f3f4; border-radius: 12px; color: #d93025; }
        """)
        btn_close.clicked.connect(self.toggle_preview)
        
        preview_header.addWidget(self.preview_label_widget)
        preview_header.addStretch()
        preview_header.addWidget(self.show_letterhead_cb)
        preview_header.addSpacing(10)
        preview_header.addWidget(btn_close)
        
        self.preview_pane_layout.addLayout(preview_header)
    
        # [FIX] Switched from Image-based (WeasyPrint PNG) to Native HTML Preview (QTextBrowser)
        # Reason 1: WeasyPrint new versions dropped write_png support, causing crashes.
        # Reason 2: QTextBrowser provides native scrolling and text selection.
        
        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(False) # or True if we want to allow links
        self.preview_browser.setStyleSheet("border: none; background-color: white;")
        self.preview_browser.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.preview_pane_layout.addWidget(self.preview_browser)
        
        # Canonical pointer (kept for compatibility with resize logic usage)
        self.preview_container = self.preview_pane_widget

    def create_side_nav_layout(self, items, page_changed_callback=None):
        """
        Creates a side navigation layout (Accordion/Master-Detail).
        items: list of tuples (title, icon_char, widget)
        page_changed_callback: optional function(index) called when page switches
        Returns: main_widget containing the layout
        """
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: white; border-right: 1px solid #e0e0e0;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)
        
        nav_cards = []
        content_stack = QStackedWidget()
        
        # Store cards on the widget so they can be accessed externally
        main_widget.nav_cards = nav_cards 
        
        def switch_page(index):
            # Guard
            if index < len(nav_cards) and not nav_cards[index].is_enabled():
                return

            # Update Active State
            for i, card in enumerate(nav_cards):
                card.set_active(i == index)
            content_stack.setCurrentIndex(index)
            
            # Call callback if provided
            if page_changed_callback:
                page_changed_callback(index)

        for i, (title, icon, page_widget) in enumerate(items):
            # Create Nav Card
            card = SideNavCard(i, icon, title)
            card.clicked.connect(switch_page)
            sidebar_layout.addWidget(card)
            nav_cards.append(card)
            
            # Add Page to Stack
            # Wrap page in scroll area if needed, but usually the page itself handles it
            # Let's ensure uniform styling for pages
            page_container = QWidget()
            page_layout = QVBoxLayout(page_container)
            page_layout.setContentsMargins(20, 20, 20, 20)
            
            # Header for the page
            header = QLabel(title)
            header.setStyleSheet("font-size: 15pt; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
            page_layout.addWidget(header)
            
            page_layout.addWidget(page_widget)
            page_layout.addStretch() # Push content up
            
            # Scroll Area for the page content
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page_container)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("background-color: #f8f9fa;")
            
            content_stack.addWidget(scroll)
            
        sidebar_layout.addStretch()
        
        # Set first item active
        if nav_cards:
            switch_page(0)
            
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_stack)
        
        return main_widget


    def create_summary_tab(self):
        """
        Create Read-Only Summary Tab with Refined Case Cockpit Layout.
        Focus: Legal Authority and Procedural Context.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #f8fafc;")

        self.summary_content = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_content)
        self.summary_layout.setContentsMargins(20, 20, 20, 20)
        self.summary_layout.setSpacing(15)

        # 1. Header Card (Case Identity)
        self.header_card = QFrame()
        self.header_card.setObjectName("HeaderCard")
        self.header_card.setStyleSheet("""
            #HeaderCard {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_layout = QHBoxLayout(self.header_card)
        
        info_layout = QVBoxLayout()
        self.lbl_legal_name = QLabel("-")
        self.lbl_legal_name.setStyleSheet("font-size: 18pt; font-weight: bold; color: #1e293b;")
        info_layout.addWidget(self.lbl_legal_name)
        
        self.lbl_gstin = QLabel("-")
        self.lbl_gstin.setStyleSheet("font-family: monospace; font-size: 10pt; color: #64748b;")
        info_layout.addWidget(self.lbl_gstin)
        header_layout.addLayout(info_layout)
        
        header_layout.addStretch()
        
        # FY Badge
        self.fy_badge = QLabel("-")
        self.fy_badge.setStyleSheet("""
            background-color: #f1f5f9;
            color: #475569;
            border-radius: 12px;
            padding: 5px 15px;
            font-weight: bold;
            font-size: 10pt;
            border: 1px solid #e2e8f0;
        """)
        header_layout.addWidget(self.fy_badge, 0, Qt.AlignmentFlag.AlignTop)
        
        self.summary_layout.addWidget(self.header_card)

        # 2. Status Banner (Dominant Element)
        self.status_banner = QLabel("-")
        self.status_banner.setWordWrap(True)
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setFixedHeight(50)
        self.status_banner.setStyleSheet("""
            font-weight: 800;
            font-size: 11pt;
            border-radius: 8px;
            padding: 12px;
            border: 1px solid transparent;
        """)
        self.summary_layout.addWidget(self.status_banner)

        # 3. Legal Basis (Chips)
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(10)
        
        self.chip_origin = QLabel("-")
        self.chip_section = QLabel("-")
        
        for chip in [self.chip_origin, self.chip_section]:
            chip.setStyleSheet("""
                background-color: #f1f5f9;
                color: #475569;
                border-radius: 15px;
                padding: 4px 12px;
                font-size: 8pt;
                font-weight: 600;
                border: 1px solid #e2e8f0;
            """)
            self.chips_layout.addWidget(chip)
        
        self.chips_layout.addStretch()
        self.summary_layout.addLayout(self.chips_layout)

        # 4. Authority Block (Issuance Metadata) - Softened Visuals
        auth_container = QWidget()
        auth_layout = QVBoxLayout(auth_container)
        auth_layout.setContentsMargins(0, 5, 0, 5)
        auth_layout.setSpacing(0)
        
        # Header Row (Subtle)
        h_row = QWidget()
        h_layout = QHBoxLayout(h_row)
        h_layout.setContentsMargins(15, 10, 15, 10)
        for text in ["Document", "O.C. Number / Reference", "Date", "Status"]:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.5px;")
            h_layout.addWidget(lbl, 1)
        auth_layout.addWidget(h_row)
        
        # Subtle Divider Line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #f1f5f9;")
        auth_layout.addWidget(divider)
        
        # Rows
        self.auth_rows = []
        for i, doc_name in enumerate(["ASMT-10", "SCN", "Order"]):
            row = QFrame()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 12, 15, 12)
            
            name_lbl = QLabel(doc_name)
            ref_lbl = QLabel("—")
            date_lbl = QLabel("—")
            stat_lbl = QLabel("—")
            
            for lbl in [name_lbl, ref_lbl, date_lbl, stat_lbl]:
                lbl.setStyleSheet("font-size: 10pt; color: #1e293b;")
                row_layout.addWidget(lbl, 1)
            
            # Special highlighting for ASMT-10 (First Row)
            if i == 0:
                name_lbl.setStyleSheet("font-weight: bold; font-size: 10pt; color: #1e293b;")
            
            auth_layout.addWidget(row)
            self.auth_rows.append({
                'name': name_lbl, 'ref': ref_lbl, 'date': date_lbl, 'status': stat_lbl, 'frame': row
            })
            
            # Row Divider
            if i < 2:
                r_div = QFrame()
                r_div.setFrameShape(QFrame.Shape.HLine)
                r_div.setStyleSheet("color: #f8fafc;")
                auth_layout.addWidget(r_div)
            
        self.summary_layout.addWidget(auth_container)

        # 5. Next Action Hint
        self.next_action_hint = QLabel("")
        self.next_action_hint.setStyleSheet("color: #64748b; font-style: italic; font-size: 10pt; margin-top: 20px; font-weight: 500;")
        self.next_action_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_layout.addWidget(self.next_action_hint)

        self.summary_layout.addStretch()
        scroll.setWidget(self.summary_content)
        return scroll

    def update_summary_tab(self):
        if not self.proceeding_data:
            return
            
        data = self.proceeding_data
        
        # 1. Header Card
        self.lbl_legal_name.setText(data.get('legal_name', 'Unknown Taxpayer'))
        self.lbl_gstin.setText(data.get('gstin', '-'))
        self.fy_badge.setText(f"FY {data.get('financial_year', '-')}")
        
        # 2. Status Banner (Strict logic derived from issuance facts)
        status = data.get('status', 'Draft')
        asmt10_status = data.get('asmt10_status')
        source_id = data.get('source_scrutiny_id') or data.get('scrutiny_id')
        
        # Issuance facts
        asmt_issued = source_id and data.get('oc_number')
        scn_issued = data.get('scn_number')
        ord_issued = data.get('order_number')
        scn_draft_exists = "Draft" in status and "SCN" in status
        
        banner_text = "Status: - " # Should be overwritten
        banner_style = ""
        
        if ord_issued:
            banner_text = "⚖️ Order Issued"
            banner_style = "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;"
        elif scn_draft_exists and not scn_issued:
            banner_text = "✏️ SCN Draft in Progress"
            banner_style = "background-color: #fffbeb; color: #92400e; border: 1px solid #fde68a;"
        elif scn_issued:
            banner_text = "⚖️ Show Cause Notice Issued"
            banner_style = "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;"
        elif asmt_issued and not scn_issued:
            banner_text = "🔒 ASMT-10 Finalised — SCN Pending"
            banner_style = "background-color: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;"
        else:
            banner_text = f"Status: {status}"
            banner_style = "background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;"
            
        self.status_banner.setText(banner_text)
        self.status_banner.setStyleSheet(self.status_banner.styleSheet() + banner_style)
        
        # 3. Legal Basis Chips
        origin_text = "Scrutiny-origin Adjudication" if source_id else "Direct Adjudication"
        self.chip_origin.setText(origin_text)
        
        adj_section = data.get('adjudication_section') or "Section Pending"
        self.chip_section.setText(f"Section {adj_section}" if adj_section != "Section Pending" else adj_section)
        
        # 4. Authority Block (Hierarchy & Emphasis)
        # Row 0: ASMT-10 (The Legal Foundation)
        row_asmt = self.auth_rows[0]
        asmt_oc = data.get('oc_number') if source_id else "—"
        asmt_date = data.get('asmt10_finalised_on') or data.get('notice_date') if source_id else "—"
        
        if asmt_issued:
            row_asmt['ref'].setText(asmt_oc)
            row_asmt['date'].setText(asmt_date or "—")
            row_asmt['status'].setText("✔ Issued")
            row_asmt['status'].setStyleSheet("color: #166534; font-weight: 800; font-size: 8pt;")
            row_asmt['frame'].setStyleSheet("background-color: #f0fdf4; border-radius: 6px; border-bottom: 1px solid #dcfce7;")
            row_asmt['name'].setStyleSheet("font-weight: 800; color: #1e293b;")
        else:
            for k in ['ref', 'date', 'status']: row_asmt[k].setText("—")
            row_asmt['frame'].setStyleSheet("opacity: 0.5;")
            row_asmt['status'].setStyleSheet("color: #94a3b8;")

        # Row 1: SCN
        row_scn = self.auth_rows[1]
        if scn_issued:
            row_scn['ref'].setText(scn_issued)
            row_scn['date'].setText(data.get('scn_date') or "—")
            row_scn['status'].setText("✔ Issued")
            row_scn['status'].setStyleSheet("color: #166534; font-weight: bold;")
            row_scn['frame'].setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #f1f5f9;")
            row_scn['name'].setStyleSheet("font-weight: bold; color: #1e293b;")
        else:
            row_scn['ref'].setText("—")
            row_scn['date'].setText("—")
            row_scn['status'].setText("Not Issued")
            row_scn['status'].setStyleSheet("color: #94a3b8;")
            row_scn['name'].setStyleSheet("color: #94a3b8;")
            row_scn['frame'].setStyleSheet("opacity: 0.5;") # Muted until issued

        # Row 2: Order
        row_ord = self.auth_rows[2]
        if ord_issued:
            row_ord['ref'].setText(ord_issued)
            row_ord['date'].setText(data.get('order_date') or "—")
            row_ord['status'].setText("✔ Issued")
            row_ord['status'].setStyleSheet("color: #166534; font-weight: bold;")
            row_ord['frame'].setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #f1f5f9;")
            row_ord['name'].setStyleSheet("font-weight: bold; color: #1e293b;")
        else:
            for k in ['ref', 'date']: row_ord[k].setText("—")
            row_ord['status'].setText("—")
            row_ord['status'].setStyleSheet("color: #94a3b8;")
            row_ord['name'].setStyleSheet("color: #94a3b8;")
            row_ord['frame'].setStyleSheet("opacity: 0.5;") # Muted

        # 5. Next Action Guidance (Informational)
        hint = ""
        if not ord_issued:
            if asmt_issued and not scn_issued:
                hint = "Next Action: Draft Show Cause Notice (SCN)"
            elif scn_issued and not ord_issued:
                hint = "Next Action: Issue Personal Hearing Intimation"
        
        self.next_action_hint.setText(hint)

    def create_drc01a_tab(self):
        print("ProceedingsWorkspace: create_drc01a_tab start")
        # Initialize list of issue cards
        self.issue_cards = []
        
        # --- DRAFT CONTAINER ---
        self.drc01a_draft_container = QWidget()
        draft_layout = QVBoxLayout(self.drc01a_draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        
        # Prepare Pages for Side Nav
        
        # 1. Reference Details
        ref_widget = QWidget()
        ref_layout = QVBoxLayout(ref_widget)
        ref_layout.setContentsMargins(0,0,0,0)
        
        ref_card = QWidget() # Was ModernCard
        ref_inner_layout = QHBoxLayout(ref_card)
        
        oc_label = QLabel("OC No:")
        self.oc_number_input = QLineEdit()
        self.oc_number_input.setPlaceholderText("Format: No./Year (e.g. 123/2025)")
        self.oc_number_input.textChanged.connect(self.trigger_preview)
        
        # Suggest Button
        suggest_btn = QPushButton("Get Next")
        suggest_btn.setToolTip("Get next available OC Number")
        suggest_btn.setStyleSheet("padding: 2px 8px; background-color: #3498db; color: white; border-radius: 4px; font-size: 8pt;")
        suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.oc_number_input))
        
        ref_inner_layout.addWidget(oc_label)
        ref_inner_layout.addWidget(self.oc_number_input)
        ref_inner_layout.addWidget(suggest_btn)
        
        oc_date_label = QLabel("OC Date:")
        self.oc_date_input = QDateEdit()
        self.oc_date_input.setCalendarPopup(True)
        self.oc_date_input.setDate(QDate.currentDate())
        self.oc_date_input.setMinimumDate(QDate.currentDate())
        self.oc_date_input.dateChanged.connect(self.trigger_preview)
        ref_inner_layout.addWidget(oc_date_label)
        ref_inner_layout.addWidget(self.oc_date_input)
        ref_inner_layout.addStretch()
        
        ref_layout.addWidget(ref_card)
        ref_layout.addStretch()
        
        # 2. Issues Involved
        issues_widget = QWidget()
        issues_layout = QVBoxLayout(issues_widget)
        issues_layout.setContentsMargins(0,0,0,0)
        
        # Issue Selection Toolbar
        issue_selection_layout = QHBoxLayout()
        issue_label = QLabel("Select Issue:")
        self.issue_combo = QComboBox()
        self.issue_combo.addItem("Select an issue...", None)
        self.load_issue_templates()
        
        refresh_issues_btn = QPushButton("🔄")
        refresh_issues_btn.setToolTip("Refresh issue list")
        refresh_issues_btn.clicked.connect(self.load_issue_templates)
        
        insert_issue_btn = QPushButton("Insert Issue Template")
        insert_issue_btn.setProperty("class", "primary")
        insert_issue_btn.clicked.connect(self.insert_selected_issue)
        
        issue_selection_layout.addWidget(issue_label)
        issue_selection_layout.addWidget(self.issue_combo)
        issue_selection_layout.addWidget(refresh_issues_btn)
        issue_selection_layout.addWidget(insert_issue_btn)
        issue_selection_layout.addStretch()
        issues_layout.addLayout(issue_selection_layout)
        
        self.issues_container = QWidget()
        self.issues_layout = QVBoxLayout(self.issues_container)
        self.issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.issues_layout.setSpacing(15)
        
        # Use existing issue cards logic (they are ModernCards, so they fit well)
        issues_layout.addWidget(self.issues_container)
        issues_layout.addStretch()

        # 3. Sections Violated
        sections_widget = QWidget()
        sec_layout = QVBoxLayout(sections_widget)
        sec_layout.setContentsMargins(0,0,0,0)
        
        section_selection_layout = QHBoxLayout()
        section_label = QLabel("Select Section:")
        self.section_combo = QComboBox()
        self.section_combo.addItem("Select a section...", None)
        self.load_sections()
        
        add_section_btn = QPushButton("Add Section")
        add_section_btn.setProperty("class", "primary")
        add_section_btn.clicked.connect(self.add_section_to_editor)
        
        section_selection_layout.addWidget(section_label)
        section_selection_layout.addWidget(self.section_combo)
        section_selection_layout.addWidget(add_section_btn)
        section_selection_layout.addStretch()
        sec_layout.addLayout(section_selection_layout)
        
        self.sections_editor = RichTextEditor("Enter the sections of law that were violated...")
        self.sections_editor.setMinimumHeight(400)
        self.sections_editor.textChanged.connect(self.trigger_preview)
        sec_layout.addWidget(self.sections_editor)
        
        # 4. Tax Demand Details
        tax_widget = QWidget()
        tax_layout = QVBoxLayout(tax_widget)
        tax_layout.setContentsMargins(0,0,0,0)
        
        act_selection_layout = QHBoxLayout()
        act_label = QLabel("Select Acts:")
        act_label.setStyleSheet("font-weight: bold;")
        act_selection_layout.addWidget(act_label)
        
        self.act_checkboxes = {}
        for act in ["CGST", "SGST", "IGST", "Cess"]:
            cb = QCheckBox(act)
            cb.stateChanged.connect(lambda state, a=act: self.toggle_act_row(a, state))
            self.act_checkboxes[act] = cb
            act_selection_layout.addWidget(cb)
        act_selection_layout.addStretch()
        tax_layout.addLayout(act_selection_layout)
        
        self.tax_table = QTableWidget()
        self.tax_table.setColumnCount(7)
        self.tax_table.setHorizontalHeaderLabels([
            "Act", "Tax Period From", "Tax Period To", "Tax (₹)", "Interest (₹)", "Penalty (₹)", "Total (₹)"
        ])
        self.tax_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tax_table.setMinimumHeight(300)
        tax_layout.addWidget(self.tax_table)
        self.add_total_row()
        
        # 5. Dates & Compliance
        dates_widget = QWidget()
        dates_layout = QVBoxLayout(dates_widget)
        dates_layout.setContentsMargins(0,0,0,0)
        
        # Last Date for Reply
        reply_label = QLabel("Last Date for Reply")
        self.reply_date = QDateEdit()
        self.reply_date.setCalendarPopup(True)
        self.reply_date.setDate(QDate.currentDate().addDays(30))
        self.reply_date.setMinimumDate(QDate.currentDate())
        self.reply_date.dateChanged.connect(self.trigger_preview)
        dates_layout.addWidget(reply_label)
        dates_layout.addWidget(self.reply_date)
        
        # Last Date for Payment
        payment_label = QLabel("Last Date for Payment")
        self.payment_date = QDateEdit()
        self.payment_date.setCalendarPopup(True)
        self.payment_date.setDate(QDate.currentDate().addDays(30))
        self.payment_date.setMinimumDate(QDate.currentDate())
        self.payment_date.dateChanged.connect(self.trigger_preview)
        dates_layout.addWidget(payment_label)
        dates_layout.addWidget(self.payment_date)
        dates_layout.addStretch()
        
        # 6. Actions
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        
        actions_desc = QLabel("Review the generated document in the right panel and proceed.")
        actions_layout.addWidget(actions_desc)
        
        # Letterhead Checkbox
        self.show_letterhead_cb = QCheckBox("Include Letterhead in Generation")
        self.show_letterhead_cb.setChecked(True)
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview)
        actions_layout.addWidget(self.show_letterhead_cb)
        
        action_btns_layout = QHBoxLayout()
        save_btn = QPushButton("Save Draft")
        save_btn.clicked.connect(self.save_drc01a)
        action_btns_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setProperty("class", "danger")
        pdf_btn.clicked.connect(self.generate_pdf)
        action_btns_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setProperty("class", "primary")
        docx_btn.clicked.connect(self.generate_docx)
        action_btns_layout.addWidget(docx_btn)
        
        finalize_btn = QPushButton("Finalize & Issue")
        finalize_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        finalize_btn.clicked.connect(self.show_drc01a_finalization_panel)
        action_btns_layout.addWidget(finalize_btn)
        
        action_btns_layout.addStretch()
        actions_layout.addLayout(action_btns_layout)
        actions_layout.addStretch()
        
        # Build Side Nav Items
        nav_items = [
            ("Reference Details", "1", ref_widget),
            ("Issues Involved", "2", issues_widget),
            ("Sections Violated", "3", sections_widget),
            ("Tax Demand Details", "4", tax_widget),
            ("Dates & Compliance", "5", dates_widget),
            ("Actions & Finalize", "✓", actions_widget)
        ]
        
        side_nav = self.create_side_nav_layout(nav_items)
        draft_layout.addWidget(side_nav)
        
        # --- FINALIZATION CONTAINER (Initially Hidden) ---
        self.drc01a_finalization_container = self.create_drc01a_finalization_panel()
        self.drc01a_finalization_container.hide()
        
        # --- VIEW CONTAINER (Initially Hidden) ---
        self.drc01a_view_container = QWidget()
        self.drc01a_view_container.hide()
        view_layout = QVBoxLayout(self.drc01a_view_container)
        
        view_title = QLabel("<b>DRC-01A Generated</b>")
        view_title.setStyleSheet("font-size: 14pt; color: #27ae60; margin-bottom: 20px;")
        view_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_title)
        
        view_msg = QLabel("A DRC-01A document has already been generated for this case.")
        view_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_msg)
        
        summary_lbl = QLabel("Document Generated Successfully.\nClick 'Edit / Revise Draft' to make changes.")
        summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_lbl.setStyleSheet("color: #7f8c8d; font-size: 10pt; margin: 20px;")
        view_layout.addWidget(summary_lbl)
        
        # Edit Button
        edit_btn = QPushButton("Edit / Revise Draft")
        edit_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; font-weight: bold;")
        edit_btn.clicked.connect(lambda: self.toggle_view_mode("drc01a", False))
        view_layout.addWidget(edit_btn)
        
        view_layout.addStretch()

        # Add containers to a main widget switching wrapper
        # Since we refactored, we can just return a container that holds all three
        
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0,0,0,0)
        wrapper_layout.addWidget(self.drc01a_draft_container)
        wrapper_layout.addWidget(self.drc01a_finalization_container)
        wrapper_layout.addWidget(self.drc01a_view_container)
        
        return wrapper

    def create_drc01a_finalization_panel(self):
        """Create the DRC-01A Finalization Summary Container (Lazy)"""
        container = QWidget()
        self.drc01a_finalization_layout = QVBoxLayout(container)
        self.drc01a_finalization_layout.setContentsMargins(0, 0, 0, 0)
        return container

    def _attach_drc01a_finalization_panel(self):
        """Instantiate and attach FinalizationPanel only for direct adjudication cases."""
        if hasattr(self, "drc_fin_panel"):
            return
            
        self.drc_fin_panel = FinalizationPanel()
        
        # Connect Signals
        self.drc_fin_panel.cancel_btn.clicked.connect(self.hide_drc01a_finalization_panel)
        self.drc_fin_panel.finalize_btn.clicked.connect(self.confirm_drc01a_finalization)
        self.drc_fin_panel.preview_btn.clicked.connect(self.generate_pdf)
        
        self.drc01a_finalization_layout.addWidget(self.drc_fin_panel)
        print("FinalizationPanel Attached (Direct Adjudication)")

    def _detach_drc01a_finalization_panel(self):
        """Detach and destroy FinalizationPanel for scrutiny-origin cases."""
        if hasattr(self, "drc_fin_panel"):
            self.drc_fin_panel.setParent(None)
            self.drc_fin_panel.deleteLater()
            del self.drc_fin_panel
            print("FinalizationPanel Detached")

    def show_drc01a_finalization_panel(self):
        """Review and Show Finalization Panel"""
        # 1. Validate Inputs
        if not self.oc_number_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "OC Number is mandatory for finalization.")
            self.oc_number_input.setFocus()
            return

        oc_no = self.oc_number_input.text()
        oc_date = self.oc_date_input.date().toString('dd-MM-yyyy')
        
        self.drc_fin_panel.load_data(
            proceeding_data=self.proceeding_data,
            issues_list=self.issue_cards, # Passing rich objects
            doc_type="DRC-01A",
            doc_no=oc_no, # For DRC-01A, OC No is the main ref
            doc_date=oc_date,
            ref_no="-" # No sep ref for DRC
        )

        # 3. Switch View
        self.drc01a_draft_container.hide()
        self.drc01a_finalization_container.show()
        
    def hide_drc01a_finalization_panel(self):
        self.drc01a_finalization_container.hide()
        self.drc01a_draft_container.show()

    def confirm_drc01a_finalization(self):
        """Commit Finalization"""
        try:
            # 1. Save Document as Final
            self.save_drc01a() # Ensure latest draft is saved
            
            # 2. Update Proceeding Status
            self.db.update_proceeding(self.proceeding_id, {
                "status": "DRC-01A Issued"
            })
            
            # 3. Update Register
            oc_data = {
                'OC_Number': self.oc_number_input.text(),
                'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"),
                'OC_Content': f"DRC-01A Issued for GSTIN {self.proceeding_data.get('gstin','')}. {self.drc_fin_panel.fin_scn_remarks.toPlainText()}",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            # Use proceeding_id (case_id used in SQLite)
            self.db.add_oc_entry(self.proceeding_id, oc_data, is_issuance=True)
            
            QMessageBox.information(self, "Success", "DRC-01A Finalized Successfully.")
            
            # 4. Switch to View Mode
            self.drc01a_finalization_container.hide()
            self.drc01a_view_container.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Finalization failed: {e}")
            import traceback
            traceback.print_exc()

    def load_issue_templates(self):
        """Load issue templates from DB (Active Issues)"""
        try:
            # Fetch active issues from DB
            issues = self.db.get_active_issues()
            
            # Convert list to dict keyed by issue_id
            self.issue_templates = {}
            self.issue_combo.clear()
            self.issue_combo.addItem("Select Issue...", None)
            
            for issue in issues:
                self.issue_templates[issue['issue_id']] = issue
                self.issue_combo.addItem(issue['issue_name'], issue['issue_id'])
                
        except Exception as e:
            print(f"Error loading issue templates: {e}")

    def load_sections(self):
        """Load CGST sections from DB"""
        try:
            sections = self.db.get_cgst_sections()
            self.section_combo.clear()
            self.section_combo.addItem("Select Section...", None)
            
            for section in sections:
                title = section.get('title', '')
                # Store full content in user data if needed, or just title
                self.section_combo.addItem(title, section)
                
        except Exception as e:
            print(f"Error loading sections: {e}")

    def add_section_to_editor(self):
        """Insert selected section into the editor"""
        section_data = self.section_combo.currentData()
        if not section_data:
            return
            
        title = section_data.get('title', '')
        # content = section_data.get('content', '') # Optional: Add content too?
        
        # Append to editor
        current_html = self.sections_editor.toHtml()
        new_html = f"{current_html}<p><b>{title}</b></p>"
        self.sections_editor.setHtml(new_html)

    def insert_selected_issue(self):
        """Insert selected issue template as a new card"""
        issue_id = self.issue_combo.currentData()
        if not issue_id:
            return
            
        template = self.issue_templates.get(issue_id)
        if not template:
            return
            
        card = IssueCard(template)
        card.valuesChanged.connect(self.calculate_grand_totals)
        card.valuesChanged.connect(self.trigger_preview)  # Add preview trigger
        card.removeClicked.connect(lambda: self.remove_issue_card(card))
        
        self.issues_layout.addWidget(card)
        self.issue_cards.append(card)
        
        # Trigger initial calculation and preview
        self.calculate_grand_totals()
        self.trigger_preview()

    def remove_issue_card(self, card):
        self.issues_layout.removeWidget(card)
        card.deleteLater()
        if card in self.issue_cards:
            self.issue_cards.remove(card)
        self.calculate_grand_totals()

    def calculate_grand_totals(self, _=None):
        """Sum up totals from all issue cards and update main table"""
        # Initialize totals for each Act
        act_totals = {
            'CGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'SGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'IGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'Cess': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
        }
        
        # Aggregate from all issue cards
        for card in self.issue_cards:
            if hasattr(card, 'get_tax_breakdown'):
                breakdown = card.get_tax_breakdown()
                for act, values in breakdown.items():
                    if act in act_totals:
                        act_totals[act]['tax'] += values.get('tax', 0.0)
                        act_totals[act]['interest'] += values.get('interest', 0.0)
                        act_totals[act]['penalty'] += values.get('penalty', 0.0)
        
        # Auto-select Acts based on non-zero totals
        # This ensures the rows exist in the table
        for act, totals in act_totals.items():
            has_liability = (totals['tax'] > 0 or totals['interest'] > 0 or totals['penalty'] > 0)
            if has_liability:
                # Find the checkbox for this act
                # keys in act_checkboxes match keys in act_totals (CGST, SGST, IGST, Cess)
                if act in self.act_checkboxes:
                    cb = self.act_checkboxes[act]
                    if not cb.isChecked():
                        # This will trigger toggle_act_row and create the row
                        cb.setChecked(True)
        
        # Update the Tax Table rows
        # We iterate through the table rows (excluding the last Total row)
        # and match the Act name in column 0
        
        # Temporarily block signals to prevent infinite loops
        self.tax_table.blockSignals(True)
        
        row_count = self.tax_table.rowCount()
        # The last row is "Total", so we iterate up to row_count - 1
        for row in range(row_count - 1):
            item = self.tax_table.item(row, 0)
            if not item: continue
            
            act_name = item.text().strip()
            
            # Map "Cess" variations if needed
            if act_name.lower() == 'cess': act_name = 'Cess'
            
            if act_name in act_totals:
                totals = act_totals[act_name]
                
                # Update Tax (Col 3)
                self.tax_table.setItem(row, 3, QTableWidgetItem(str(totals['tax'])))
                
                # Update Interest/Penalty if extracted (otherwise leave manual/default)
                if totals['interest'] > 0:
                    self.tax_table.setItem(row, 4, QTableWidgetItem(str(totals['interest'])))
                if totals['penalty'] > 0:
                    self.tax_table.setItem(row, 5, QTableWidgetItem(str(totals['penalty'])))
                    
        self.tax_table.blockSignals(False)
        
        # Recalculate row totals and grand total
        self.calculate_totals()
        
        # Trigger preview update
        self.trigger_preview()

    def create_scn_tab(self):
        print("ProceedingsWorkspace: create_scn_tab start")
        """Create Show Cause Notice tab"""
        
        # --- DRAFT CONTAINER ---
        self.scn_draft_container = QWidget()
        self.scn_draft_container.setObjectName("SCNDraftContainer")
        draft_layout = QVBoxLayout(self.scn_draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        
        # Track initialization state for Issue Adoption
        self.scn_issues_initialized = False
        
        # Preparing Pages
        
        # 1. Reference Details (Reverted to Single-Column centered layout)
        ref_widget = QWidget()
        ref_layout = QVBoxLayout(ref_widget)
        ref_layout.setContentsMargins(20, 20, 20, 20)
        ref_layout.setSpacing(20)
        
        self.ref_card = ModernCard(title="Reference Details", collapsible=False)
        self.ref_card.setFixedWidth(450) # Keep it compact and professional
        
        # Sub-header & Helper text
        ref_subheader = QLabel("SCN Identity Setup")
        ref_subheader.setStyleSheet("font-size: 10pt; color: #7f8c8d; margin-top: -10px; margin-bottom: 5px;")
        self.ref_card.addLayout(QVBoxLayout()) # Internal layout access
        self.ref_card.content_layout.insertWidget(0, ref_subheader)
        
        ref_helper = QLabel("These details identify the Show Cause Notice and are saved even if you exit early.")
        ref_helper.setWordWrap(True)
        ref_helper.setStyleSheet("font-size: 8pt; color: #95a5a6; font-style: italic; margin-bottom: 15px;")
        self.ref_card.content_layout.insertWidget(1, ref_helper)
        
        # Grid for inputs
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(15)
        
        label_style = "color: #5f6368; font-weight: 500; font-size: 9pt;"
        input_style = "padding: 8px; border: 1px solid #dadce0; border-radius: 4px; font-size: 10pt;"
        
        # SCN No
        scn_no_label = QLabel("SCN No.")
        scn_no_label.setStyleSheet(label_style)
        self.scn_no_input = QLineEdit()
        self.scn_no_input.setPlaceholderText("e.g. SCN/2026/001")
        self.scn_no_input.setStyleSheet(input_style)
        self.scn_no_input.textChanged.connect(self.trigger_preview)
        self.scn_no_input.textChanged.connect(self.evaluate_scn_workflow_phase)
        
        grid.addWidget(scn_no_label, 0, 0)
        grid.addWidget(self.scn_no_input, 0, 1, 1, 2)
        
        # O.C. No (with Inline Auto-Generate)
        oc_label = QLabel("O.C. No.")
        oc_label.setStyleSheet(label_style)
        self.scn_oc_input = QLineEdit()
        self.scn_oc_input.setPlaceholderText("e.g. 123/2026")
        self.scn_oc_input.setStyleSheet(input_style)
        self.scn_oc_input.textChanged.connect(self._on_scn_oc_changed)
        
        # Auto-Generate Button (Utility)
        self.btn_auto_oc = QPushButton("Auto-Generate")
        self.btn_auto_oc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_oc.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                color: #475569;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 8pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #3498db;
                color: #3498db;
            }
        """)
        self.btn_auto_oc.clicked.connect(self._on_auto_generate_oc)
        
        # Provenance Indicator
        self.oc_provenance_lbl = QLabel("")
        self.oc_provenance_lbl.setStyleSheet("font-size: 8pt; color: #3498db; font-style: italic;")
        self.oc_provenance_lbl.hide()
        
        grid.addWidget(oc_label, 1, 0)
        grid.addWidget(self.scn_oc_input, 1, 1)
        grid.addWidget(self.btn_auto_oc, 1, 2)
        grid.addWidget(self.oc_provenance_lbl, 2, 1, 1, 2)
        
        # SCN Date
        date_label = QLabel("SCN Date")
        date_label.setStyleSheet(label_style)
        self.scn_date_input = QDateEdit()
        self.scn_date_input.setCalendarPopup(True)
        self.scn_date_input.setDate(QDate.currentDate())
        self.scn_date_input.setMinimumDate(QDate.currentDate())
        self.scn_date_input.setStyleSheet(input_style + " padding: 6px;")
        self.scn_date_input.dateChanged.connect(self.trigger_preview)
        self.scn_date_input.dateChanged.connect(self.evaluate_scn_workflow_phase)
        
        grid.addWidget(date_label, 3, 0)
        grid.addWidget(self.scn_date_input, 3, 1, 1, 2)
        
        self.ref_card.addWidget(grid_widget)
        self.ref_card.content_layout.addStretch()
        
        # Action Buttons Hierarchy
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(0, 20, 0, 0)
        
        # Save & Proceed (Primary)
        self.btn_save_scn_ref = QPushButton("Save & Proceed")
        self.btn_save_scn_ref.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:disabled {
                background-color: #dadce0;
                color: #70757a;
            }
        """)
        self.btn_save_scn_ref.clicked.connect(self.save_scn_metadata)
        btn_layout.addWidget(self.btn_save_scn_ref)
        
        # View ASMT-10 Reference (Secondary)
        self.btn_asmt10_ref = QPushButton("View ASMT-10 Reference")
        self.btn_asmt10_ref.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #dadce0;
                color: #3c4043;
                padding: 10px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #1a73e8;
                color: #1a73e8;
            }
        """)
        self.btn_asmt10_ref.clicked.connect(self.open_asmt10_reference)
        btn_layout.addWidget(self.btn_asmt10_ref)
        
        self.ref_card.addLayout(btn_layout)
        
        # Center the card in the layout
        ref_layout.addStretch()
        ref_layout.addWidget(self.ref_card, 0, Qt.AlignmentFlag.AlignHCenter)
        ref_layout.addStretch()

        # 2. Issues Involved
        issues_widget = QWidget()
        issues_layout = QVBoxLayout(issues_widget)
        issues_layout.setContentsMargins(0,0,0,0)
        
        self.scn_issue_cards = []
        
        scn_issue_selection_layout = QHBoxLayout()
        scn_issue_label = QLabel("Select Issue:")
        self.scn_issue_combo = QComboBox()
        self.scn_issue_combo.addItem("Select an issue...", None)
        print("ProceedingsWorkspace: loading scn issue templates")
        self.load_scn_issue_templates()
        print("ProceedingsWorkspace: scn issue templates loaded")
        
        scn_refresh_issues_btn = QPushButton("🔄")
        scn_refresh_issues_btn.setToolTip("Refresh issue list")
        scn_refresh_issues_btn.clicked.connect(self.load_scn_issue_templates)
        
        scn_insert_issue_btn = QPushButton("Insert Issue Template")
        scn_insert_issue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scn_insert_issue_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; 
                color: white; 
                font-weight: bold; 
                padding: 6px 15px; 
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        scn_insert_issue_btn.clicked.connect(self.insert_scn_issue)
        
        scn_reset_btn = QPushButton("Reset Adoption")
        scn_reset_btn.setStyleSheet("background-color: #f39c12; color: white; border-radius: 4px; padding: 5px 10px; font-size: 8pt; font-weight: bold;")
        scn_reset_btn.clicked.connect(self.reset_scn_adoption)
        
        scn_issue_selection_layout.addWidget(scn_issue_label)
        scn_issue_selection_layout.addWidget(self.scn_issue_combo)
        scn_issue_selection_layout.addWidget(scn_refresh_issues_btn)
        scn_issue_selection_layout.addWidget(scn_insert_issue_btn)
        scn_issue_selection_layout.addWidget(scn_reset_btn)
        scn_issue_selection_layout.addStretch()
        issues_layout.addLayout(scn_issue_selection_layout)
        
        # Proper SCN container
        self.scn_issues_container = QWidget()
        self.scn_issues_layout = QVBoxLayout(self.scn_issues_container)
        self.scn_issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scn_issues_layout.setSpacing(15)
        
        issues_layout.addWidget(self.scn_issues_container)
        issues_layout.addStretch()

        # 3. Demand & Contraventions
        demand_widget = QWidget()
        demand_layout = QVBoxLayout(demand_widget)
        demand_layout.setContentsMargins(0,0,0,0)
        
        demand_header_layout = QHBoxLayout()
        demand_header_layout.addStretch()
        regenerate_btn = QPushButton("Sync with Issues")
        regenerate_btn.setToolTip("Auto-generate demand text tiles based on added issues")
        regenerate_btn.setStyleSheet("padding: 5px; font-size: 8pt; background-color: #3498db; color: white; border-radius: 4px;")
        regenerate_btn.clicked.connect(lambda: self.sync_demand_tiles() if not self.is_scn_phase1() else None)
        demand_header_layout.addWidget(regenerate_btn)
        demand_layout.addLayout(demand_header_layout)
        
        self.demand_tiles_widget = QWidget()
        self.demand_tiles_layout = QVBoxLayout(self.demand_tiles_widget)
        self.demand_tiles_layout.setSpacing(10)
        self.demand_tiles_layout.setContentsMargins(0, 0, 0, 0)
        
        self.demand_tiles = []
        
        demand_layout.addWidget(self.demand_tiles_widget)
        demand_layout.addStretch()
        
        # 4. Reliance Placed
        reliance_widget = QWidget()
        rel_layout = QVBoxLayout(reliance_widget)
        rel_layout.setContentsMargins(0,0,0,0)
        
        self.reliance_editor = RichTextEditor("List documents here (e.g., 1. INS-01 dated...)")
        self.reliance_editor.setMinimumHeight(300)
        self.reliance_editor.textChanged.connect(lambda: self.trigger_preview() if not self.is_scn_phase1() else None)
        rel_layout.addWidget(self.reliance_editor)
        
        # 5. Copy Submitted To
        copy_widget = QWidget()
        copy_layout = QVBoxLayout(copy_widget)
        copy_layout.setContentsMargins(0,0,0,0)
        
        self.copy_to_editor = RichTextEditor("List authorities here...")
        self.copy_to_editor.setMinimumHeight(300)
        self.copy_to_editor.textChanged.connect(lambda: self.trigger_preview() if not self.is_scn_phase1() else None)
        copy_layout.addWidget(self.copy_to_editor)
        
        # 6. Actions
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        
        actions_desc = QLabel("Review and Finalize SCN")
        actions_layout.addWidget(actions_desc)
        
        action_btns_layout = QHBoxLayout()
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("SCN") if not self.is_scn_phase1() else print("Save blocked in Phase-1"))
        action_btns_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        pdf_btn.clicked.connect(self.generate_pdf)
        action_btns_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        docx_btn.clicked.connect(self.generate_docx)
        action_btns_layout.addWidget(docx_btn)
        
        finalize_btn = QPushButton("Finalize SCN")
        finalize_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        finalize_btn.clicked.connect(self.show_scn_finalization_panel)
        action_btns_layout.addWidget(finalize_btn)
        
        action_btns_layout.addStretch()
        actions_layout.addLayout(action_btns_layout)
        actions_layout.addStretch()
        
        # Build Side Nav
        nav_items = [
            ("Reference Details", "1", ref_widget),
            ("Issue Adoption", "2", issues_widget),
            ("Demand & Contraventions", "3", demand_widget),
            ("Reliance Placed", "4", reliance_widget),
            ("Copy Submitted To", "5", copy_widget),
            ("Actions & Finalize", "✓", actions_widget)
        ]
        
        self.scn_side_nav = self.create_side_nav_layout(nav_items, page_changed_callback=self.on_scn_page_changed)
        # Store for access in validation
        self.scn_nav_cards = self.scn_side_nav.nav_cards
        
        draft_layout.addWidget(self.scn_side_nav)
        
        # Lock Steps 2-6 initially
        for i in range(1, 6):
            self.scn_nav_cards[i].set_enabled(False)
        
        # --- FINALIZATION CONTAINER ---
        self.scn_finalization_container = self.create_scn_finalization_panel()
        self.scn_finalization_container.hide()
        
        # --- VIEW CONTAINER ---
        self.scn_view_container = QWidget()
        self.scn_view_container.hide()
        view_layout = QVBoxLayout(self.scn_view_container)
        
        view_title = QLabel("<b>SCN Generated</b>")
        view_title.setStyleSheet("font-size: 14pt; color: #27ae60; margin-bottom: 20px;")
        view_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_title)
        
        view_msg = QLabel("A Show Cause Notice has already been generated and issued for this case.")
        view_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_msg)
        
        summary_lbl = QLabel("Document Generated Successfully.\nClick 'Edit / Revise Draft' to make changes.")
        summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_lbl.setStyleSheet("color: #7f8c8d; font-size: 10pt; margin: 20px;")
        view_layout.addWidget(summary_lbl)
        
        edit_btn = QPushButton("Edit / Revise Draft")
        edit_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; font-weight: bold;")
        edit_btn.clicked.connect(lambda: self.toggle_view_mode("scn", False))
        view_layout.addWidget(edit_btn)
        
        view_layout.addStretch()

        # Wrapper
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0,0,0,0)
        wrapper_layout.addWidget(self.scn_draft_container)
        wrapper_layout.addWidget(self.scn_finalization_container)
        wrapper_layout.addWidget(self.scn_view_container)
        
        print("ProceedingsWorkspace: create_scn_tab done")
        return wrapper

    def validate_scn_metadata(self) -> bool:
        """Returns True only if SCN No, OC No, and Date are present"""
        if not hasattr(self, 'scn_no_input'):
            return False
            
        scn_no = self.scn_no_input.text().strip()
        oc_no = self.scn_oc_input.text().strip()
        scn_date = self.scn_date_input.date()
        
        # Valid if SCN No and OC No are not empty, and date is valid
        return bool(scn_no) and bool(oc_no) and scn_date.isValid()

    def save_scn_metadata(self):
        """Authoritative metadata persistence for Step 1. Metadata is always saved, even if incomplete."""
        if not self.proceeding_id:
            return
            
        try:
            # 1. Extract values
            scn_no = self.scn_no_input.text().strip()
            oc_no = self.scn_oc_input.text().strip()
            scn_date = self.scn_date_input.date().toString("yyyy-MM-dd")
            
            # 2. Update additional_details without touching other sections
            current_details = self.proceeding_data.get('additional_details', {})
            if isinstance(current_details, str):
                try: current_details = json.loads(current_details)
                except: current_details = {}
            
            current_details.update({
                "scn_number": scn_no,
                "scn_oc_number": oc_no,
                "scn_date": scn_date
            })
            
            # 3. Persist to DB (Routed Logic)
            if self.proceeding_data.get('is_adjudication'):
                # Adjudication Case (Table: adjudication_cases)
                success = self.db.update_adjudication_case(self.proceeding_id, {
                    "additional_details": current_details
                })
            else:
                # Standard Proceeding (Table: proceedings)
                success = self.db.update_proceeding(self.proceeding_id, {
                    "additional_details": current_details
                })
            
            # 4. Update local state
            self.proceeding_data['additional_details'] = current_details
            
            # 5. Evaluate phase (Enables Step 2 if metadata is now valid)
            self.evaluate_scn_workflow_phase()
            
            # 6. Safeguard: Navigation only if fully valid
            if self.validate_scn_metadata():
                # Navigate to Step 2 (Issue Adoption)
                if hasattr(self, 'scn_side_nav') and len(self.scn_nav_cards) > 1:
                    # trigger navigation by emitting clicked signal
                    self.scn_side_nav.nav_cards[1].clicked.emit(1)
            else:
                QMessageBox.information(self, "Saved", "Reference details saved. Complete all fields to proceed to Issue Adoption.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save metadata: {e}")
            print(f"Error saving SCN metadata: {e}")

    def evaluate_scn_workflow_phase(self):
        """Authoritative, data-driven state machine for SCN drafting phases."""
        if not hasattr(self, 'scn_nav_cards'):
            return

        metadata_valid = self.validate_scn_metadata()
        
        # Phase 2 Condition: Metadata OK + At least one issue adopted/added in Step 2
        content_valid = any(issue.is_adopted for issue in self.scn_issue_cards)
        
        # Update Authority Flag
        prev_phase = self.scn_workflow_phase
        self.scn_workflow_phase = "DRAFTING" if (metadata_valid and content_valid) else "METADATA"
            
        print(f"SCN Workflow State: metadata={metadata_valid}, content={content_valid} -> {self.scn_workflow_phase}")

        # --- UI Enforcement ---
        
        # Step 2 (Issue Adoption) depends ONLY on metadata
        self.scn_nav_cards[1].set_enabled(metadata_valid)
        
        # Steps 3-6 depend ONLY on DRAFTING phase flag
        is_drafting = (self.scn_workflow_phase == "DRAFTING")
        for i in range(2, 6):
            self.scn_nav_cards[i].set_enabled(is_drafting)
            
        # Trigger downstream updates if we just entered Drafting phase
        if is_drafting and prev_phase == "METADATA":
             self.sync_demand_tiles()
             self.trigger_preview()
        
        # Re-lock if metadata fails
        if not metadata_valid:
             for i in range(1, 6):
                 self.scn_nav_cards[i].set_enabled(False)

    def on_scn_page_changed(self, index):
        self.active_scn_step = index
        
        # Hard Entry Gate: Step 2 (Issue Adoption) for Scrutiny Cases
        if index == 1:
            source_scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
            if source_scrutiny_id:
                asmt10_status = self.proceeding_data.get('asmt10_status')
                if asmt10_status != 'finalised':
                     self._show_blocking_msg("ASMT-10 is not finalised. SCN drafting is locked.")
                     # Go back to Step 1
                     self.scn_side_nav.nav_cards[0].setChecked(True)
                     self.active_scn_step = 0
                     return
            
            # Trigger Hydration
            self.hydrate_from_snapshot()
            
        print(f"ProceedingsWorkspace: SCN Page {index} active")
        # In Step 2 (Adoption), enforce de-cluttering (handled in add_scn_issue_card)
        
        # Trigger preview update
        self.update_preview("scn")
        print(f"SCN: Moved to Step {index+1}.")

    def create_ph_intimation_tab(self):
        print("ProceedingsWorkspace: create_ph_intimation_tab start")
        """Create Personal Hearing Intimation tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("<b>Drafting Personal Hearing Intimation</b>")
        title.setStyleSheet("font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Reference Details (OC)
        ref_layout = QHBoxLayout()
        oc_label = QLabel("OC No:")
        self.ph_oc_input = QLineEdit()
        self.ph_oc_input.setPlaceholderText("Format: No./Year")
        self.ph_oc_input.textChanged.connect(self.trigger_preview)
        
        ph_oc_suggest_btn = QPushButton("Get Next")
        ph_oc_suggest_btn.setStyleSheet("padding: 2px 8px; background-color: #3498db; color: white; border-radius: 4px; font-size: 8pt;")
        ph_oc_suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.ph_oc_input))
        
        oc_date_label = QLabel("OC Date:")
        self.ph_oc_date = QDateEdit()
        self.ph_oc_date.setCalendarPopup(True)
        self.ph_oc_date.setDate(QDate.currentDate())
        self.ph_oc_date.dateChanged.connect(self.trigger_preview)
        
        ref_layout.addWidget(oc_label)
        ref_layout.addWidget(self.ph_oc_input)
        ref_layout.addWidget(ph_oc_suggest_btn)
        ref_layout.addSpacing(10)
        ref_layout.addWidget(oc_date_label)
        ref_layout.addWidget(self.ph_oc_date)
        ref_layout.addStretch()
        layout.addLayout(ref_layout)
        
        # Rich Text Editor
        print("ProceedingsWorkspace: creating ph_editor")
        self.ph_editor = RichTextEditor("Enter the Personal Hearing Intimation content here...")
        print("ProceedingsWorkspace: ph_editor created")
        self.ph_editor.setMinimumHeight(400)
        self.ph_editor.textChanged.connect(self.trigger_preview)
        layout.addWidget(self.ph_editor)
        print("ProceedingsWorkspace: ph_editor added")
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("PH"))
        buttons_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        docx_btn.clicked.connect(self.generate_docx)
        buttons_layout.addWidget(docx_btn)
        
        finalize_btn = QPushButton("Finalize & Register")
        finalize_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        finalize_btn.clicked.connect(self.confirm_ph_finalization)
        buttons_layout.addWidget(finalize_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Wrap in a centered container to constrain width
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        container_layout.addWidget(widget)
        
        # Set max width for the form content
        widget.setMaximumWidth(850) 
        
        # Wrap in Scroll Area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setWidget(container)
        
        print("ProceedingsWorkspace: create_ph_intimation_tab done")
        return main_scroll

    def create_order_tab(self):
        print("ProceedingsWorkspace: create_order_tab start")
        """Create Order tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("<b>Drafting Order</b>")
        title.setStyleSheet("font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Reference Details (OC)
        ref_layout = QHBoxLayout()
        oc_label = QLabel("OC No:")
        self.order_oc_input = QLineEdit()
        self.order_oc_input.setPlaceholderText("Format: No./Year")
        self.order_oc_input.textChanged.connect(self.trigger_preview)
        
        order_oc_suggest_btn = QPushButton("Get Next")
        order_oc_suggest_btn.setStyleSheet("padding: 2px 8px; background-color: #3498db; color: white; border-radius: 4px; font-size: 8pt;")
        order_oc_suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.order_oc_input))
        
        oc_date_label = QLabel("OC Date:")
        self.order_oc_date = QDateEdit()
        self.order_oc_date.setCalendarPopup(True)
        self.order_oc_date.setDate(QDate.currentDate())
        self.order_oc_date.dateChanged.connect(self.trigger_preview)
        
        ref_layout.addWidget(oc_label)
        ref_layout.addWidget(self.order_oc_input)
        ref_layout.addWidget(order_oc_suggest_btn)
        ref_layout.addSpacing(10)
        ref_layout.addWidget(oc_date_label)
        ref_layout.addWidget(self.order_oc_date)
        ref_layout.addStretch()
        layout.addLayout(ref_layout)
        
        # Rich Text Editor
        print("ProceedingsWorkspace: creating order_editor")
        self.order_editor = RichTextEditor("Enter the Order content here...")
        print("ProceedingsWorkspace: order_editor created")
        self.order_editor.setMinimumHeight(400)
        self.order_editor.textChanged.connect(self.trigger_preview)
        layout.addWidget(self.order_editor)
        print("ProceedingsWorkspace: order_editor added")
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("Order"))
        buttons_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        docx_btn.clicked.connect(self.generate_docx)
        buttons_layout.addWidget(docx_btn)
        
        finalize_btn = QPushButton("Finalize & Register")
        finalize_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        finalize_btn.clicked.connect(self.confirm_order_finalization)
        buttons_layout.addWidget(finalize_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Wrap in a centered container to constrain width
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        container_layout.addWidget(widget)
        
        # Set max width for the form content
        widget.setMaximumWidth(850) 
        
        # Wrap in Scroll Area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setWidget(container)
        
        print("ProceedingsWorkspace: create_order_tab done")
        return main_scroll

    
    def create_scn_finalization_panel(self):
        """Create the SCN Finalization Summary Panel using reusable component"""
        self.scn_fin_panel = FinalizationPanel()
        
        # Connect Signals
        self.scn_fin_panel.cancel_btn.clicked.connect(self.hide_scn_finalization_panel)
        self.scn_fin_panel.finalize_btn.clicked.connect(self.confirm_scn_finalization)
        self.scn_fin_panel.preview_btn.clicked.connect(self.generate_pdf) # Re-use existing PDF gen
        
        return self.scn_fin_panel

    def show_scn_finalization_panel(self):
        """Review and Show SCN Finalization Panel"""
        # 1. Validate Inputs
        if not self.scn_no_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "SCN Number is mandatory for finalization.")
            self.scn_no_input.setFocus()
            return

        scn_no = self.scn_no_input.text()
        scn_date = self.scn_date_input.date().toString('dd-MM-yyyy')
        oc_no = self.scn_oc_input.text()

        # 2. Prepare Data for Panel
        # We need to pass the issue cards directly because they have the 'get_tax_breakdown' method
        # AND we need to pass the tax payer / case info
        
        # Enrich proceeding data with taxpayer info if missing (it might be in parent/dashboard logic)
        # But self.proceeding_data usually has it from load.
        
        self.scn_fin_panel.load_data(
            proceeding_data=self.proceeding_data,
            issues_list=self.scn_issue_cards, # Passing rich objects
            doc_type="SCN",
            doc_no=scn_no,
            doc_date=scn_date,
            ref_no=oc_no
        )

        # 3. Switch View
        self.scn_draft_container.hide()
        self.scn_finalization_container.show()
        
    def hide_scn_finalization_panel(self):
        self.scn_finalization_container.hide()
        self.scn_draft_container.show()
        
    def confirm_scn_finalization(self):
        """Commit SCN Finalization"""
        try:
            # 1. Save Document as Final
            self.save_document("SCN") # Ensure latest draft is saved
            
            # 2. Update Proceeding Status
            self.db.update_proceeding(self.proceeding_id, {
                "status": "SCN Issued"
            })
            
            # 3. Update Register (SCN Register entry - implicitly done via status or explicit call?)
            # Also Add OC Entry for SCN
            oc_data = {
                'OC_Number': self.scn_oc_input.text(),
                'OC_Date': self.scn_date_input.date().toString("yyyy-MM-dd"),
                'OC_Content': f"Show Cause Notice Issued. SCN No: {self.scn_no_input.text()}. {self.scn_fin_panel.fin_scn_remarks.toPlainText()}",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            self.db.add_oc_entry(self.proceeding_id, oc_data)
            
            QMessageBox.information(self, "Success", "Show Cause Notice Finalized Successfully.")
            
            # 4. Switch to View Mode
            self.scn_finalization_container.hide()
            self.scn_view_container.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Finalization failed: {e}")
            import traceback
            traceback.print_exc()

    def load_scn_issue_templates(self):
        """Load prioritized issue templates for SCN tab (Strictly Limited for Adoption + Manual SOP)"""
        self.scn_issue_combo.clear()
        
        try:
            # Gather IDs of currently present issues in the draft
            present_issue_ids = set()
            if hasattr(self, 'scn_issue_cards'):
                present_issue_ids = {c.template['issue_id'] for c in self.scn_issue_cards}
            
            # 1. Scrutiny-Based Adoptions
            adopted_from_asmt10_ids = set()
            source_scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
            
            if source_scrutiny_id:
                finalized_issues = self.db.get_case_issues(source_scrutiny_id, stage='DRC-01A')
                if finalized_issues:
                    self.scn_issue_combo.addItem("--- ADOPT FROM ASMT-10 ---", None)
                    for record in finalized_issues:
                        issue_id = record['issue_id']
                        adopted_from_asmt10_ids.add(issue_id)
                        
                        # Skip if already present in draft (Dynamic Availability)
                        if issue_id in present_issue_ids:
                            continue

                        # Use Adapter to resolve SCN template for the dropdown
                        adapted = self.build_scn_issue_from_asmt10(record)
                        issue_name = adapted['template'].get('issue_name', 'Issue')
                        
                        # Structured Payload
                        payload = {
                            'issue_id': issue_id,
                            'origin': 'ASMT10',
                            'template': adapted['template'],
                            'data': adapted['data'],
                            'is_unique': True
                        }
                        self.scn_issue_combo.addItem(issue_name, payload)

            # 2. Manual SOP Addition (The Feature)
            self.scn_issue_combo.addItem("--- MANUAL ADDITION (SOP ISSUES) ---", None)
            
            # Fetch all active issues
            all_issues_meta = self.db.get_all_issues_metadata() # Lightweight fetch
            
            for meta in all_issues_meta:
                issue_id = meta['issue_id']
                
                # Filter: Must be SOP issue, NOT in ASMT-10 source
                if not issue_id.startswith('SOP-'): continue
                if issue_id in adopted_from_asmt10_ids: continue
                
                # Check existance for SOP issues (Unique)
                if issue_id in present_issue_ids: continue
                
                payload = {
                    'issue_id': issue_id,
                    'issue_name': meta['issue_name'],
                    'origin': 'MANUAL_SOP',
                    'is_unique': True
                }
                self.scn_issue_combo.addItem(f"{issue_id}: {meta['issue_name']}", payload)

            # 3. SCN-Origin / Custom Templates
            self.scn_issue_combo.addItem("--- OTHER TEMPLATES ---", None)
            
            # SCN Master Templates (from templates table, type SCN)
            all_templates = self.db.get_issue_templates()
            for t in all_templates:
                if t.get('type') == 'SCN':
                    payload = {
                        'issue_id': t['issue_id'],
                        'origin': 'SCN',
                        'template': t,
                        'is_unique': False # Custom SCN templates might be re-usable? Let's say yes for now.
                    }
                    self.scn_issue_combo.addItem(f"Template: {t['issue_name']}", payload)
            
            # Blank SCN Issue
            blank_payload = {
                'issue_id': "BLANK_SCN_ISSUE",
                'issue_name': "Blank SCN Issue",
                'origin': "SCN",
                'is_unique': False
            }
            self.scn_issue_combo.addItem("Add Blank SCN Issue", blank_payload)

        except Exception as e:
            print(f"Error loading SCN templates: {e}")
            import traceback
            traceback.print_exc()

    def add_scn_issue_card(self, template, data=None, source_type=None, source_id=None, origin="SCN", status="ACTIVE"):
        """Add flexible issue card to SCN layout"""
        from src.ui.issue_card import IssueCard
        card = IssueCard(template, data=data, mode="SCN", content_key="scn_content")
        
        # Apply flexible classification (informational badge)
        card.set_classification(origin=origin, status=status)
        if source_id:
            card.set_source_metadata(source_type or "ASMT10", source_id)
            # Explicitly persist source info on the object for snapshotting
            card.source_issue_id = source_id 
            card.source_proceeding_id = self.proceeding_data.get('source_scrutiny_id')
        
        # Persist origin on object for snapshotting
        card.origin = origin

        if data:
            # load_data handles restoring state from saved drafts
            # But wait, IssueCard usually takes data in constructor.
            # If load_data exists it might override.
            # Inspecting IssueCard.. it uses constructor data.
            # load_data method doesn't exist in IssueCard class shown earlier?
            # IssueCard.__init__ logic:
            # if data and 'table_data' in data ...
            # So data passed to constructor is enough.
            pass
        
        # Connect signals
        card.removeClicked.connect(lambda c_obj=card: self.remove_scn_issue_card(None, c_obj))
        card.valuesChanged.connect(self.trigger_preview)
        card.contentChanged.connect(self.trigger_preview)
        
        self.scn_issues_layout.addWidget(card)
        self.scn_issue_cards.append(card)
        
        # Trigger Phase Evaluation
        self.evaluate_scn_workflow_phase()
        
        return card

    def insert_scn_issue(self):
        """Insert a manually selected issue template into the drafting layout"""
        # Guard: Phase-1 Finalization
        if self.is_scn_finalized():
             QMessageBox.warning(self, "Action Blocked", "Show Cause Notice is already finalized.")
             return

        payload = self.scn_issue_combo.currentData()
        if not payload:
             QMessageBox.warning(self, "Invalid Selection", "Please select a valid issue from the list (not a category header).")
             return
        
        # Self-Healing: Handle Legacy String Payload (if dropdown stale)
        if isinstance(payload, str):
             print(f"Warning: Stale dropdown payload (str) detected: {payload}")
             # Force reload
             self.load_scn_issue_templates()
             QMessageBox.warning(self, "Refresh Required", "Issue list was stale. Refreshed. Please select and insert again.")
             return

        try:
            issue_id = payload['issue_id']
            origin = payload['origin']
            issue_name = payload.get('issue_name', issue_id)
            
            # Resolve Template
            # 1. If payload has full template (ASMT10 / Custom SCN cache)
            if 'template' in payload:
                template = payload['template']
                data = payload.get('data') # Pre-filled data
                source_id = issue_id if origin == 'ASMT10' else None
                
            # 2. If Manual SOP, we need to fetch master
            elif origin == "MANUAL_SOP":
                # Fetch full template now (Lazy Load)
                full_template = self.db.get_issue(issue_id)
                if not full_template:
                    QMessageBox.warning(self, "Integration Error", 
                                      f"Could not load template schema for issue '{issue_id}'.\nCheck Issue Master integrity.")
                    return
                    
                template = full_template
                data = None # Fresh issue
                source_id = None
            
            # 3. Blank/Generic
            elif issue_id == "BLANK_SCN_ISSUE":
                import uuid
                # Generate unique ID for this instance
                unique_id = f"SCN_MANUAL_{uuid.uuid4().hex[:8]}"
                template = {
                    'issue_id': unique_id,
                    'issue_name': "New SCN Issue",
                    'brief_facts_scn': "[Enter Facts]",
                    'templates': {'brief_facts_scn': "[Enter Facts]"},
                    'variables': {}
                }
                data = None
                source_id = None
                
            # 4. Enforce Structured Duplicate Check before Insertion
            # Rules:
            # - SCRUTINY/ASMT10: Unique by source_issue_id (already adopted?)
            # - MANUAL_SOP: Unique by issue_id (don't add same SOP point twice)
            # - BLANK/SCN: Multi-instance allowed (though blank usually usually unique until saved with content)
            
            is_duplicate = False
            for card in self.scn_issue_cards:
                 existing_origin = getattr(card, 'origin', 'SCN')
                 existing_template_id = card.template.get('issue_id')
                 existing_source_id = getattr(card, 'source_issue_id', None)
                 
                 # duplicate check
                 if origin in ["ASMT10", "SCRUTINY"] and source_id:
                      if existing_source_id == source_id: 
                           is_duplicate = True; break
                 elif origin == "MANUAL_SOP":
                      if existing_template_id == issue_id:
                           is_duplicate = True; break
                           
            if is_duplicate:
                 QMessageBox.information(self, "Issue Already Added", 
                                       f"The issue '{issue_name}' has already been added to the draft.")
                 return

            # [FIX] JIT Repair for Insertion (Safety Net)
            if template:
                tgt_grid = template.get('grid_data')
                if tgt_grid and isinstance(tgt_grid, dict):
                    cols = tgt_grid.get('columns')
                    if isinstance(cols, list) and cols and not isinstance(cols[0], dict):
                         print(f"  - JIT Repair (Insert): Upgrading string columns for {template.get('issue_id')}")
                         new_cols = [{"id": f"col{i}", "label": str(c)} for i, c in enumerate(cols)]
                         tgt_grid['columns'] = new_cols

            self.add_scn_issue_card(
                template=template,
                data=data,
                origin=origin,
                source_id=source_id
            )
            
            # Immediate Persistence for Manual Issues
            if origin == "MANUAL_SOP":
                 self.persist_scn_issues()

        except Exception as e:
            QMessageBox.critical(self, "Insertion Error", f"Failed to insert issue: {e}")
            import traceback
            traceback.print_exc()

        # Phase-1 Isolation: Guarded at highest call-site
        if not self.is_scn_phase1():
            self.sync_demand_tiles()
            self.trigger_preview()
            self.save_document("SCN")

    def remove_scn_issue_card(self, modern_card, card):
        # Guard: Phase-1 Finalization
        if self.is_scn_finalized():
             QMessageBox.warning(self, "Action Blocked", "Show Cause Notice is already finalized.")
             return

        # Guard: Manual SOP Deletion Warning
        if getattr(card, 'origin', 'SCRUTINY') == "MANUAL_SOP":
             # Requirement: Explicit Warning
             reply = QMessageBox.question(self, "Delete Manual Issue", 
                                        "You are deleting a manually added SOP issue. This cannot be undone.\n\nProceed?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                  return

        if modern_card:
            self.scn_issues_layout.removeWidget(modern_card)
            modern_card.deleteLater()
        else:
            self.scn_issues_layout.removeWidget(card)
            card.deleteLater()
            
        if card in self.scn_issue_cards:
            self.scn_issue_cards.remove(card)
            
        # Trigger Phase Evaluation
        self.evaluate_scn_workflow_phase()
        # Phase-1 Isolation: Guarded at highest call-site
        if not self.is_scn_phase1():
            self.sync_demand_tiles()
            self.trigger_preview()
            self.save_document("SCN")

    def is_scn_phase1(self):
        """State-Absolute Phase-1 detection: True only if we are still in METADATA phase."""
        return self.scn_workflow_phase == "METADATA"

    def hydrate_from_snapshot(self):
        """
        Snapshot-Only Hydration Strategy.
        Rules:
        1. If 'SCN' stage issues exist: Load strictly from case_issues.data_json. 
           NEVER consult Issue Master.
        2. If NO 'SCN' issues exist: Clone from ASMT-10 (Initial Setup).
        """
        # 1. Idempotency Gate
        if self.scn_issues_initialized and self.scn_issue_cards:
            return

        # 2. Hard Clear UI
        while self.scn_issues_layout.count():
            item = self.scn_issues_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
        self.scn_issue_cards = []

        try:
            # 3. Fetch Existing SCN Draft from DB
            existing_scn_draft = self.db.get_case_issues(self.proceeding_id, stage='SCN')
            
            if existing_scn_draft:
                print(f"SCN Load: Restoring {len(existing_scn_draft)} cards from snapshot.")
                self._hydrate_cards_from_records(existing_scn_draft, is_initial_hydration=False)
                
            else:
                # 4. First-Time Initialization: Clone from ASMT-10
                source_scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
                
                if source_scrutiny_id:
                    finalized_asmt10_records = self.db.get_case_issues(source_scrutiny_id, stage='DRC-01A')
                    
                    if finalized_asmt10_records:
                        print(f"SCN Load: Initializing from ASMT-10 ({len(finalized_asmt10_records)} issues).")
                        
                        # Prepare Clone Batch
                        clone_batch = []
                        for record in finalized_asmt10_records:
                            # Clone Structure
                            new_record = {
                                'issue_id': record['issue_id'],
                                'data': record['data'], # This is ASMT-10 data. 
                                # Note: For strict independent lifecycle, we probably should bake the template here too?
                                # But ASMT-10 data usually implies using the adapter to build the SCN template.
                                # The adapter `build_scn_issue_from_asmt10` does the translation.
                                # So for *initial* clone, we rely on the adapter logic which fetches template. 
                                # This is allowed ("Issue Master used at insertion time"). 
                                # Initial clone counts as insertion.
                                'origin': 'SCRUTINY',
                                'source_proceeding_id': source_scrutiny_id,
                                'added_by': 'System'
                            }
                            clone_batch.append(new_record)
                        
                        # Persist Initial State (So next time we hit Priority 1)
                        # We use _hydrate_cards_from_records with is_initial_hydration=True which calls build_scn_issue_from_asmt10
                        # Wait, we need to save the RESULT of the adaptation (the SCN template) to the DB.
                        # The clone_batch above saves the raw ASMT-10 data? 
                        # No, `save_scn_issue_snapshot` saves whatever we pass.
                        # Ideally, we should perform the adaptation *before* saving the snapshot if we want strict independence immediately.
                        # However, `_hydrate_cards_from_records(is_initial=True)` adapts it.
                        # Let's persist *after* hydration to capture the adapted templates.
                        
                        # So:
                        # 1. Hydrate UI from ASMT-10 records (Adapter runs here)
                        self._hydrate_cards_from_records(finalized_asmt10_records, is_initial_hydration=True)
                        
                        # 2. Immediately Persist the RESULTING UI state (which includes the SCN templates)
                        self.persist_scn_issues()
                        
                        # 3. Reload from snapshot to verify? No, we are already hydrated.
                        # But strictly speaking, the prompt says "Once ... exist ... never be queried".
                        # If I persist now, next reload will use snapshot.
                        
                    else:
                        print("SCN Load: No ASMT-10 issues found to adopt.")
                else:
                    print("SCN Load: Direct SCN mode (No source scrutiny).")

            self.scn_issues_initialized = True
            self._persist_scn_init_flag()

        except Exception as e:
            print(f"SCN Hydration Error: {e}")
            import traceback
            traceback.print_exc()

    def persist_scn_issues(self):
        """
        Orchestrate saving the current SCN issue state to DB (case_issues).
        Captures the exact snapshot of the drafting area INCLUDING TEMPLATES.
        Requirement: Snapshot-Only Hydration (Independent of Master)
        """
        # Guard: Phase-1 Finalization
        if self.is_scn_finalized():
             # Technically Save Button should be disabled, but strict backend guard is needed
             print("SCN is Finalized. Writes blocked.")
             return

        try:
            current_snapshot = []
            
            for card in self.scn_issue_cards:
                # Issue Card MUST expose its origin and source info
                
                # Extract Origin
                origin = getattr(card, 'origin', 'SCRUTINY')
                source_pid = getattr(card, 'source_proceeding_id', None)
                
                card_data = card.get_data()
                
                # CRITICAL HARDENING: Save the Template Structure
                # This ensures we don't need to consult Master when re-hydrating.
                # card.template contains the structure used to render the card.
                # We inject it into the 'data_json' blob.
                # NOTE: This increases DB size but guarantees legal immutability.
                
                data_payload = {
                     'values': card_data.get('variables', {}),
                     'table_data': card_data.get('table_data'),
                     'template_snapshot': card.template, # FULL TEMPLATE
                     # Persist other state flags if needed
                     'status': getattr(card, 'status', 'ACTIVE')
                }
                
                print(f"[BRIDGE DIAG] persist_scn: Card {card.template.get('issue_id')} table_data type: {type(data_payload['table_data'])}")
                if data_payload['template_snapshot']:
                    print(f"  - Snapshot has grid_data? {'grid_data' in data_payload['template_snapshot']}")

                snapshot_item = {
                    'issue_id': card.template.get('issue_id'),
                    'data': data_payload, # Contains everything needed to render
                    'origin': origin,
                    'source_proceeding_id': source_pid,
                    'added_by': 'User' 
                }
                current_snapshot.append(snapshot_item)
            
            # Save to DB
            success = self.db.save_scn_issue_snapshot(self.proceeding_id, current_snapshot)
            if success:
                print(f"SCN Persistence: Saved {len(current_snapshot)} issues with snapshot templates.")
            else:
                print("SCN Persistence: Failed to save to DB.")
                
        except Exception as e:
            print(f"Error persisting SCN issues: {e}")

    def is_stub_grid(self, grid_data):
        """Authoritative check: Is the grid data empty or just a placeholder stub?
        Supports both list-of-lists (legacy) and Dictionary Schema (Modern).
        """
        if not grid_data:
            return True
            
        # Case 1: Dictionary Schema {"columns": [], "rows": []}
        if isinstance(grid_data, dict):
            rows = grid_data.get('rows', [])
            if not rows: return True
            for row in rows:
                for col_id, cell in row.items():
                    if isinstance(cell, dict):
                        val = cell.get('value')
                        if val not in (None, "", "____"):
                            return False
                    elif cell not in (None, "", "____"):
                        return False
            return True

        # Case 2: List of Lists (Legacy)
        if isinstance(grid_data, list):
            if len(grid_data) <= 1: # Only header or nothing
                return True
            for row in grid_data[1:]:
                for cell in row:
                    if isinstance(cell, dict):
                        val = cell.get('value')
                        if val not in (None, "", "____"):
                            return False
                    elif cell not in (None, "", "____"):
                        return False
            return True
            
        return True

    def _normalize_issue_id(self, issue_id):
        """Strip 'Point X- ' prefixes for robust template lookup"""
        if not issue_id: return issue_id
        import re
        normalized = re.sub(r'^Point \d+- ', '', str(issue_id))
        return normalized

    def _normalize_summary_table(self, summary_table: dict) -> dict:
        """
        Convert Scrutiny summary_table (headers/rows) into a semantic NormalizedTable structure.
        Roles are identified heuristically (e.g., last row is Difference in a 3-row table).
        """
        headers = summary_table.get('headers')
        if not headers:
             # Fallback: Scrutiny summary might use 'columns' (Canonical Schema)
             raw_cols = summary_table.get('columns', [])
             headers = [c.get('label') if isinstance(c, dict) else str(c) for c in raw_cols]
             
        rows_data = summary_table.get('rows', [])
        
        # [ROBUSTNESS] Header Inference from First Row if missing
        if not headers and rows_data and isinstance(rows_data[0], dict):
             headers = list(rows_data[0].keys())
             print(f"[CONV DIAG] Infereed headers from row data: {headers}")

        # [DIAGNOSTIC] Log input structure
        print(f"[CONV DIAG] Headers Final: {headers}")
        print(f"[CONV DIAG] Rows Count: {len(rows_data)}")
        
        # 1. Map Columns to Tax Heads
        columns = []
        for i, h in enumerate(headers):
            h_upper = str(h).upper()
            col = {"id": f"col_{i}", "label": str(h)}
            if i == 0:
                col["id"] = "label"
                col["static"] = True
            elif "IGST" in h_upper: col["tax_head"] = "IGST"; col["id"] = "igst"
            elif "CGST" in h_upper: col["tax_head"] = "CGST"; col["id"] = "cgst"
            elif "SGST" in h_upper: col["tax_head"] = "SGST"; col["id"] = "sgst"
            elif "CESS" in h_upper: col["tax_head"] = "CESS"; col["id"] = "cess"
            columns.append(col)

        # 2. Determine Row Roles
        # Scrutiny summary tables usually have 3 rows: [Base1, Base2, Difference]
        normalized_rows = []
        num_rows = len(rows_data)
        
        num_value_cols = max(0, len(columns) - 1)
        
        for i, row in enumerate(rows_data):
            # 2.1 Calculate Role Deterministically
            role = "BASE"
            if num_rows >= 2 and i == num_rows - 1:
                role = "DIFFERENCE"

            try:
                # Row label handling: Summary table can have rows as lists or dicts (col0, col1...)
                if isinstance(row, dict):
                    # 1. Label handling (Semantic vs col0)
                    label = str(row.get("col0", ""))
                    if not label:
                        # Semantic Fallback: Try 'description', 'desc', 'label'
                        for k in ["description", "desc", "label", "particulars"]:
                            if k in row:
                                label = str(row[k])
                                break
                                
                    # 2. Value Mapping (Semantic vs colX)
                    values = []
                    for j in range(1, len(columns)):
                        col_def = columns[j]
                        header_label = col_def["label"].lower().strip()
                        
                        # A. Try Standard colX
                        val = row.get(f"col{j}")
                        
                        # B. Try Semantic Mapping (Deterministic Aliases)
                        if val is None:
                            # Map Header Label -> Potential Keys
                            aliases = []
                            
                            if "amount" in header_label or "value" in header_label:
                                aliases = ["amount", "value", "amt", "total_value"]
                            elif "tax" in header_label:
                                if "igst" in header_label: aliases = ["igst", "tax_igst", "igst_amt"]
                                elif "cgst" in header_label: aliases = ["cgst", "tax_cgst", "cgst_amt"]
                                elif "sgst" in header_label: aliases = ["sgst", "tax_sgst", "sgst_amt"]
                                elif "cess" in header_label: aliases = ["cess", "tax_cess", "cess_amt"]
                                else: aliases = ["tax", "tax_amt"]
                            elif "turnover" in header_label:
                                aliases = ["turnover", "total_turnover"]
                            elif "rate" in header_label:
                                aliases = ["rate", "tax_rate"]
                            
                            # Attempt alias lookup
                            for alias in aliases:
                                if alias in row:
                                    val = row[alias]
                                    break
                        
                        # Default to 0 if not found
                        if val is None:
                            val = 0
                            
                        values.append(val)
                else:
                    label = str(row[0]) if isinstance(row, list) and len(row) > 0 else f"Row {i+1}"
                    # Handle list rows explicitly
                    raw_values = row[1:] if isinstance(row, list) else []
                    values = []
                    for rv in raw_values:
                        values.append(rv)

                # 2.2 Enforce Rectangular Shape
                # 1. Truncate extra columns
                values = values[:num_value_cols]
                # 2. Pad missing columns with 0
                while len(values) < num_value_cols:
                    values.append(0)
                
                normalized_rows.append({
                    "role": role,
                    "label": label,
                    "values": values
                })

            except Exception as e:
                # [SAFEGUARD] Fallback to zero-row BUT maintain contract (Role)
                print(f"Row {i} normalization failed: {e}")
                normalized_rows.append({
                    "role": role, # CRITICAL: Maintain role (e.g. DIFFERENCE) so grid conversion binds variables
                    "label": "Error Row",
                    "values": [0] * num_value_cols
                })

        return {
            "columns": columns,
            "rows": normalized_rows
        }

    def _convert_normalized_to_grid(self, normalized_table: dict) -> dict:
        """
        Transform NormalizedTable into the SCN-compatible grid_data schema (Canonical Dict).
        Binds DIFFERENCE row cells to tax variables.
        Rules: Deterministic validation, explicit cell schema.
        """
        norm_columns = normalized_table.get("columns", [])
        rows = normalized_table.get("rows", [])
        
        # 1. Assert Invariants
        if not isinstance(norm_columns, list):
             raise ValueError(f"Normalized columns must be a list, got {type(norm_columns)}")
             
        num_cols = len(norm_columns)
        if num_cols <= 0:
             # [FIX] Explicit check to prevent KeyError: 0 downstream
             raise ValueError("MANDATORY: Table must have at least one column (label). Table is empty.")

        # 2. Prepare Columns for GridAdapter Schema
        grid_columns = []
        col_mappings = {} 
        
        for i, col in enumerate(norm_columns):
            grid_id = f"col{i}" 
            grid_columns.append({"id": grid_id, "label": col.get("label", f"Col {i}")})
            col_mappings[i] = grid_id

        # 3. Convert Rows to Canonical Schema
        grid_rows = []

        for r_idx, norm_row in enumerate(rows):
            # Assert row integrity
            assert "role" in norm_row, f"Row {r_idx} missing role"
            assert "label" in norm_row, f"Row {r_idx} missing label"
            assert "values" in norm_row, f"Row {r_idx} missing values"
            
            values = norm_row["values"]
            role = norm_row["role"]
            label = norm_row["label"]
            
            # Assert Rectangular Integrity: num_values == num_cols - 1 (label col excluded from values list)
            assert len(values) == num_cols - 1, f"Row {r_idx} value count ({len(values)}) mismatch with columns ({num_cols-1})"

            grid_row = {}

            # 3.1 Label Cell (col0) - Explicit Schema
            grid_id_0 = col_mappings[0]
            grid_row[grid_id_0] = {
                "value": label, 
                "type": "static"
            }

            # 3.2 Data Cells - Explicit Schema
            for i, val in enumerate(values):
                col_idx = i + 1
                grid_id = col_mappings[col_idx]
                col_meta = norm_columns[col_idx]
                tax_head = col_meta.get("tax_head")
                
                cell = {"value": val}
                
                if role == "DIFFERENCE" and tax_head:
                    # Bound to calculation engine
                    cell["type"] = "input"
                    cell["var"] = f"tax_{tax_head.lower()}"
                else:
                    cell["type"] = "static"
                    
                grid_row[grid_id] = cell
            
            grid_rows.append(grid_row)

        return {
            "columns": grid_columns,
            "rows": grid_rows
        }


    def build_scn_issue_from_asmt10(self, asmt_record: dict) -> dict:
        """
        Final Authoritative Adapter: Resolves SCN-specific templates while carrying forward
        only factual table data from ASMT-10 snapshots.
        """
        issue_id = asmt_record['issue_id']
        asmt_data = asmt_record['data']

        # 1. Identity & Template Resolution (Prefer SCN doc_type if exists)
        # Try exact ID, then normalized ID, then Name-based
        normalized_id = self._normalize_issue_id(issue_id)
        scn_template = self.db.get_issue(issue_id) or \
                       self.db.get_issue(normalized_id) or \
                       self.db.get_issue_by_name(normalized_id) or \
                       self.db.get_issue_by_name(issue_id)
        
        # 2. Strict Template Normalization for SCN
        if not scn_template:
             # Create a minimal scaffold if no master template exists
             scn_template = {
                 'issue_id': issue_id,
                 'issue_name': asmt_data.get('issue', asmt_data.get('category', 'Issue')),
                 'templates': {}
             }
        
        # 2.1 Ensure SCN-specific keys exist or fallback
        t = scn_template.get('templates', {})
        
        # Pull Narration from ASMT-10 if SCN template is new or empty
        asmt_narration = asmt_data.get('brief_facts') or asmt_data.get('description', '')
        
        if not t.get('brief_facts_scn') and not t.get('scn'):
             t['brief_facts_scn'] = asmt_narration
        if not t.get('grounds'):
             t['grounds'] = ""
        if not t.get('legal'):
             t['legal'] = ""
        if not t.get('conclusion'):
             t['conclusion'] = ""
        
        scn_template['templates'] = t

        # 3. Factual Table Carry-Forward (Direct Pass-Through)
        # [USER REQUEST] "The exact tables which were in the asmt-10 should appear"
        # We bypass complex normalization and trust the source structure.
        
        summary_table = asmt_data.get('summary_table')
        grid_data = asmt_data.get('grid_data')
        
        final_grid = None

        # [FIX] Prioritize Analysis Result (summary_table) over Static Template (grid_data)
        # The Master DB has 'grid_data' initialized with Zeros, which masked the real values.
        
        # Priority 1: Summary Table (Convert to Grid if needed)
        if summary_table:
            # Check if it's already in canonical format (rows + columns) OR just needs render-time inference
            # [DIRECT PASS-THROUGH] We now trust the updated renderer (ui_helpers) to handle List-rows
            if hasattr(summary_table, '__iter__') and not isinstance(summary_table, (str, bytes)):
                 # Accept Dict (canonical) AND List (raw rows)
                 if isinstance(summary_table, list):
                      if not summary_table: 
                           final_grid = None
                      else:
                           # [OPTION B] Strict Fidelity: Ensure List conforms to GridAdapter
                           print(f"Direct Pass-Through of List-Based Summary Table for {issue_id}")
                           # Check if first item is simple value (Flat List) -> Wrap as single col
                           if not isinstance(summary_table[0], (dict, list)):
                                # Convert ["A", "B"] -> [{"col0": {"value": "A"}}, ...]
                                wrapped_rows = []
                                for val in summary_table:
                                     wrapped_rows.append({"col0": {"value": val}})
                                final_grid = {"columns": [{"id": "col0", "label": "Value"}], "rows": wrapped_rows}
                           else:
                                # Safe List-of-Lists or List-of-Dicts
                                final_grid = {'rows': summary_table}

                 elif isinstance(summary_table, dict) and 'rows' in summary_table:
                      print(f"Direct Pass-Through of Summary Table for {issue_id}")
                      final_grid = summary_table
                      
                      # [FIX] Enforce Canonical Column Schema (Prevent Metadata Loss)
                      # If columns are strings, upgrade them immediately.
                      cols = final_grid.get('columns')
                      if isinstance(cols, list) and cols and not isinstance(cols[0], dict):
                          print(f"Detected Legacy String Columns for {issue_id} -> Upgrading to Canonical Schema")
                          new_cols = []
                          for i, col_val in enumerate(cols):
                              # Generate ID: col0, col1...
                              # Use value as Label
                              new_cols.append({"id": f"col{i}", "label": str(col_val)})
                          final_grid['columns'] = new_cols

                 else:
                      # [FIX] Trap for Legacy Scrutiny Dicts (without 'rows') -> Force Normalization
                      print(f"Legacy Scrutiny Table detected for {issue_id} -> Normalizing")
                      try:
                          normalized = self._normalize_summary_table(summary_table)
                          final_grid = self._convert_normalized_to_grid(normalized)
                      except Exception as e:
                          print(f"Legacy Table Conversion Failed: {e}")
                          final_grid = None
            else:
                 try:
                     normalized = self._normalize_summary_table(summary_table)
                     final_grid = self._convert_normalized_to_grid(normalized)
                 except: final_grid = None

        # Priority 2: Existing Grid Data (Canonical) - Fallback for Legacy/Static
        elif grid_data and isinstance(grid_data, dict) and 'rows' in grid_data:
            final_grid = grid_data
        
        # Inject Provenance Metadata (If we have a valid grid)
        if final_grid:
            try:
                import datetime
                source_meta = {
                    "origin": "ASMT10",
                    "asmt_id": self.proceeding_id, 
                    "converted_on": datetime.datetime.now().isoformat()
                }
                source_scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
                source_meta["asmt_id"] = source_scrutiny_id
                
                # Injection: Find first available cell in first row
                if final_grid.get('rows'):
                    first_row = final_grid['rows'][0]
                    # Robust injection for List or Dict rows
                    if isinstance(first_row, dict):
                         target_col = "col0"
                         if target_col not in first_row and first_row:
                             target_col = list(first_row.keys())[0]
                         if target_col in first_row:
                             first_row[target_col]["source"] = source_meta
                
                # Demand Calculation Contract
                # [FIX] REMOVED blind injection of tax_demand_mapping.
                # If the template doesn't specify a mapping, we should NOT assume standard variables exist.
                # This allows IssueCard to correctly fall back to heuristics (grid summation) for legacy/list-based issues.
                pass
            except Exception as e:
                print(f"Metadata Injection Failed: {e}")

        factual_tables = final_grid or asmt_data.get('tables') or []


        if factual_tables:
            # Force the table structure into the SCN template
            scn_template['grid_data'] = factual_tables
            print(f"[BRIDGE DIAG] build_scn: Attached grid_data to template for {issue_id}. Type: {type(factual_tables)}")
        else:
            print(f"[BRIDGE DIAG] build_scn: NO factual_tables for {issue_id}")
        
        # 4. Narration Initialization
        # We populate variables with factual data for placeholder resolution
        # Carry forward all variables from the ASMT-10 snapshot (findings)
        raw_snapshot = asmt_data.get('snapshot', {}).copy()
        variables = {}
        
        # CLAIM 2 FIX: Deterministic Variable Mapping
        # Bridge Scrutiny internal keys to clean SCN placeholder names
        SCRUTINY_TO_SCN_MAP = {
            "cgst_as_per_3b": "cgst_3b", "cgst_as_per_1": "cgst_1", "cgst_as_per_2b": "cgst_2b",
            "sgst_as_per_3b": "sgst_3b", "sgst_as_per_1": "sgst_1", "sgst_as_per_2b": "sgst_2b",
            "igst_as_per_3b": "igst_3b", "igst_as_per_1": "igst_1", "igst_as_per_2b": "igst_2b",
            "cess_as_per_3b": "cess_3b", "cess_as_per_1": "cess_1", "cess_as_per_2b": "cess_2b",
            "cgst_diff": "diff_cgst", "sgst_diff": "diff_sgst", "igst_diff": "diff_igst", "cess_diff": "diff_cess"
        }
        
        for k, v in raw_snapshot.items():
            variables[k] = v # Keep original
            if k in SCRUTINY_TO_SCN_MAP:
                variables[SCRUTINY_TO_SCN_MAP[k]] = v # Add mapped alias
        
        # Merge SCN-specific context
        variables.update({
            'brief_facts': asmt_data.get('brief_facts', ""),
            'total_shortfall': asmt_data.get('total_shortfall', 0),
            'issue_name': asmt_data.get('issue_name', asmt_data.get('issue', 'Issue'))
        })
        
        # Ensure converted grid variables are also in the variables dict
        if grid_data and isinstance(grid_data, dict) and 'rows' in grid_data:
             for row in grid_data['rows']:
                 # Canonical Row is {"col0": {val, type}, "col1": ...}
                 for cell_key, cell in row.items():
                     if isinstance(cell, dict):
                         var = cell.get('var')
                         if var and 'value' in cell:
                             variables[var] = cell['value']
        
        # 5. Output Payload (The Authoritative SCN Adoption JSON)
        return {
            'template': scn_template,
            'data': {
                'issue_id': issue_id,
                'origin': 'ASMT10',
                'table_data': grid_data or factual_tables, # Prefer conversion result
                'variables': variables,
                'status': 'ACTIVE',
                'source_issue_id': issue_id
            }
        }

    def is_scn_finalized(self):
        """Check if SCN is in finalized state (Read-Only Mode)"""
        status = self.proceeding_data.get('status', '')
        return "Final" in status or "Issued" in status

    def _hydrate_cards_from_records(self, records, is_initial_hydration=False):
        """Authoritative card factory. No fallbacks, heuristics, or shared help paths."""
        
        # Fetch case-level provenance for validation
        case_source_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
        
        for record in records:
            if is_initial_hydration:
                # Use Adapter for fresh ASMT-10 adoption
                adapted = self.build_scn_issue_from_asmt10(record)
                card = self.add_scn_issue_card(
                    template=adapted['template'],
                    data=adapted['data'],
                    origin="ASMT10",
                    source_id=record['issue_id']
                )
                if card: card.on_grid_data_adopted()
            else:
                # Restoration of existing SCN draft (SCN stage) - STRICT SNAPSHOT HYDRATION
                data_payload = record.get('data', {})
                issue_id = record['issue_id']
                
                # Rule: NEVER consult Issue Master for restored issues.
                # Use the template snapshot embedded in the data payload.
                template_snapshot = data_payload.get('template_snapshot')
                
                # [FIX] Hydration Data Flow: Authoritative Master Merge
                # Problem: Snapshot might be "hollow" (missing issue_name, brief_facts_scn).
                # Solution: Fetch Master (if available) and overlay snapshot data.
                
                master_template = self.db.get_issue(issue_id) or self.db.get_issue_by_name(issue_id)
                
                if master_template:
                     # 1. Base is Master (Identity + Static Text + Logic)
                     template = copy.deepcopy(master_template)
                     
                     # 2. Overlay Snapshot State (The "Values")
                     if template_snapshot:
                          # Preserve User Edits / Specific Tables (ASMT10)
                          if 'grid_data' in template_snapshot:
                               template['grid_data'] = template_snapshot['grid_data']
                          if 'variables' in template_snapshot:
                               template['variables'] = template_snapshot['variables']
                               
                     # Note: We purposely do NOT overlay 'issue_name' or 'templates' from snapshot
                     # to ensure we get the latest corrections from Master.
                else:
                     # Fallback: Trust Snapshot if Master gone (e.g. ad-hoc/custom issues)
                     template = template_snapshot
                     if not template:
                          print(f"WARNING: No template snapshot or master for {issue_id}.")

                if not template:
                     # Absolute fallback for corrupted IDs
                     template = {
                        'issue_id': issue_id, 
                        'issue_name': data_payload.get('issue', 'Issue'),
                        'variables': {}
                     }
                
                
                # Extract values from payload structure
                if 'values' in data_payload:
                     # New Structure
                     restore_data = {
                         'variables': data_payload.get('values'),
                         'table_data': data_payload.get('table_data')
                     }
                else:
                     # Legacy Structure (Direct props)
                     restore_data = data_payload
                
                # --- GLOBAL PROVENANCE LOGIC (System-Wide) ---
                current_origin = record.get('origin', 'SCRUTINY')
                
                source_id = record.get('source_issue_id') 
                source_proc_id = record.get('source_proceeding_id')
                source_type = record.get('source_proceeding_type', 'SCRUTINY') # Assume scrutiny if typeless legacy
                
                # GLOBAL RULE: Trust Verification Metadata only. 
                # If we have a valid source link (ID + ProcID), we honor it.
                if current_origin == "SCN" and source_id and source_proc_id and source_type in ("SCRUTINY", "ASMT10"):
                     # Double Check: Does source_proc_id match THIS case's lineage?
                     if source_proc_id == case_source_id:
                          print(f"Hydration Repair: Provenance-based Auto-Correction SCN -> {source_type} for {issue_id}")
                          current_origin = source_type
                
                
                # [HYDRATION REPAIR] Self-Healing for "Hollow" Templates
                # Scenario: Snapshot lacks grid_data (e.g., initial draft was saved before table render).
                # Fix: Re-fetch authoritative table from ASMT-10 source if available.
                
                is_hollow = (
                    current_origin in ["ASMT10", "SCRUTINY"] and 
                    not template.get('grid_data') and 
                    not template.get('tables') and
                    not restore_data.get('table_data')
                )
                
                if is_hollow and source_id and source_proc_id:
                     print(f"[HYDRATION REPAIR] Detected HOLLOW template for {issue_id}. Attempting repair from {source_proc_id}...")
                     
                     # 1. Fetch Source Context
                     try:
                         # Performance Note: This fetches case slice. Acceptable for repair scenario.
                         source_records = self.db.get_case_issues(source_proc_id, stage='DRC-01A')
                         source_record = next((r for r in source_records if r['issue_id'] == source_id), None)
                         
                         if source_record:
                             # 2. Regenerate Fresh Template/Data from Source
                             print(f"  - Source record found. Re-building...")
                             repair_package = self.build_scn_issue_from_asmt10(source_record)
                             
                             fresh_template = repair_package['template']
                             fresh_grid = fresh_template.get('grid_data')
                             
                             if fresh_grid:
                                  print(f"  - REPAIR SUCCESS: Injected {len(fresh_grid.get('rows', []))} rows.")
                                  
                                  # 3. Surgical Injection (Preserve User's Draft, Repair Structure)
                                  template['grid_data'] = fresh_grid
                                  
                                  # Also update restore_data to ensure load_data picks it up
                                  restore_data['table_data'] = fresh_grid
                             else:
                                  print("  - Repair Warning: Source also has no grid_data.")
                         else:
                             print("  - Repair Failed: Source record not found.")
                     except Exception as e:
                         print(f"  - Repair Error: {e}")

                print(f"[BRIDGE DIAG] hydrate_scn: Preparing card {issue_id}. restore_data[table_data] type: {type(restore_data.get('table_data'))}")
                
                # [FIX] JIT Repair for Legacy Snapshots (Failed Strictness Check)
                # Existing snapshots in DB may have string-columns. Upgrade them NOW.
                for target in [template, restore_data]:
                    tgt_grid = None
                    if target == template: tgt_grid = target.get('grid_data')
                    else: tgt_grid = target.get('table_data')
                    
                    if tgt_grid and isinstance(tgt_grid, dict):
                        cols = tgt_grid.get('columns')
                        if isinstance(cols, list) and cols and not isinstance(cols[0], dict):
                             print(f"  - JIT Repair: Upgrading string columns for {issue_id}")
                             new_cols = [{"id": f"col{i}", "label": str(c)} for i, c in enumerate(cols)]
                             tgt_grid['columns'] = new_cols

                if template:
                    print(f"  - Template has grid_data? {'grid_data' in template}")
                
                card = self.add_scn_issue_card(
                    template=template,
                    data=restore_data, 
                    origin=current_origin,
                    status=data_payload.get('status', 'ACTIVE'),
                    source_id=source_id
                )
                if card: card.on_grid_data_adopted()

    def reset_scn_adoption(self):
        """
        Reset Adoption Strategy (Redefined).
        Action: Remove ONLY issues with origin='SCRUTINY'.
        Constraint: NEVER delete origin='MANUAL_SOP'.
        Constraint: NEVER re-query ASMT-10. SCN Snapshot is authoritative.
        """
        if not self.proceeding_id: return

        # Guard: Phase-1 Finalization
        if self.is_scn_finalized():
             QMessageBox.warning(self, "Action Blocked", "Show Cause Notice is already finalized.")
             return

        # 1. Confirm Intent
        # We are purging adopted issues. Manual issues stay.
        msg = "This will remove all issues adopted from Scrutiny (Origin: SCRUTINY).\n\n"
        msg += "Manually added SOP issues will be PRESERVED.\n"
        msg += "To restore Scrutiny issues later, use the 'Adoption' dropdown.\n\n"
        msg += "Proceed with removal?"
        
        reply = QMessageBox.question(self, "Remove Scrutiny Issues", msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                   
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 2. Perform Selective Removal
        # Iterate backwards to safely remove from list
        removed_count = 0
        preserved_count = 0
        
        # Snapshot copy of list to avoid modification errors during iteration
        for card in list(self.scn_issue_cards):
            origin = getattr(card, 'origin', 'SCRUTINY')
            
            if origin == 'SCRUTINY' or origin == 'ASMT10':
                # Remove this card
                # Use existing removal logic but suppress heavy save per item if possible
                # For now, standard removal is safer to ensure UI sync
                self.remove_scn_issue_card(None, card)
                removed_count += 1
            else:
                preserved_count += 1
                
        # 3. Final Persistence & Feedback
        # remove_scn_issue_card triggers save, so DB is already updated.
        
        QMessageBox.information(self, "Action Complete", 
                              f"Removed {removed_count} Scrutiny issues.\nPreserved {preserved_count} Manual issues.")
        
        # 4. Refresh Dropdown immediately to make adopted issues available again
        self.load_scn_issue_templates()

    def _persist_scn_init_flag(self):
        """Authoritative, minimal persistence for SCN initialization flag only. UI-only side effect."""
        try:
            add_details = self.proceeding_data.get('additional_details', {})
            if isinstance(add_details, str): add_details = json.loads(add_details)
            add_details['scn_issues_initialized'] = True
            
            # Persist to DB directly
            # Fix: Pass dict directly to avoid double serialization (DB manager handles it)
            self.db.update_proceeding(self.proceeding_id, {
                'additional_details': add_details
            })
            print(f"ProceedingsWorkspace: SCN initialization flag persisted for {self.proceeding_id}")
        except Exception as e:
            print(f"Error persisting SCN init flag: {e}")

    def sync_demand_tiles(self):
        """Sync Demand Tiles with Issues"""
        try:
            # Clear existing tiles
            while self.demand_tiles_layout.count():
                item = self.demand_tiles_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.demand_tiles = []
            
            # Iterate through SCN issue cards
            tax_numerals = []
            
            for i, card in enumerate(self.scn_issue_cards, 1):
                data = card.get_data()
                template = card.template
                issue_id = template.get('issue_id', 'unknown')
                issue_name = template.get('issue_name', f'Issue {i}')
                
                # Generate Tax Text (Clause i/ii/iii)
                text = self.db.generate_single_issue_demand_text(data, i)
                # Extract numeral (naive but sufficient for now)
                roman = self.db.to_roman(i).lower()
                tax_numerals.append(f"({roman})")
                
                # Create Tile
                tile = ModernCard(f"And whereas - {issue_name} (Clause {roman})", collapsible=True)
                
                # Editor
                editor = RichTextEditor()
                formatted_text = text.replace('\n', '<br>')
                editor.setHtml(formatted_text)
                editor.setMinimumHeight(150)
                editor.textChanged.connect(lambda: self.trigger_preview() if not self.is_scn_phase1() else None)
                
                tile.addWidget(editor)
                self.demand_tiles_layout.addWidget(tile)
                
                self.demand_tiles.append({
                    'issue_id': issue_id,
                    'type': 'TAX',
                    'card': tile,
                    'editor': editor
                })
            
            # Create Consolidated Interest Tile
            if tax_numerals:
                refs = ", ".join(tax_numerals[:-1]) + " and " + tax_numerals[-1] if len(tax_numerals) > 1 else tax_numerals[0]
                interest_roman = self.db.to_roman(len(self.scn_issue_cards) + 1).lower()
                
                int_text = f"{interest_roman}. Interest at an appropriate rate under Section 50 of the CGST Act 2017 on the amount demanded at Para No. {refs} as mentioned above should not be demanded and recovered from them under Section 73(1) of the CGST Act 2017 and corresponding Section under Kerala SGST Act, 2017, read with Section 20 of the IGST Act, 2017;"
                
                int_tile = ModernCard(f"Interest Demand (Clause {interest_roman})", collapsible=True)
                int_editor = RichTextEditor()
                int_editor.setHtml(int_text)
                int_editor.setMinimumHeight(120)
                int_editor.textChanged.connect(lambda: self.trigger_preview() if not self.is_scn_phase1() else None)
                int_tile.addWidget(int_editor)
                self.demand_tiles_layout.addWidget(int_tile)
                self.demand_tiles.append({'issue_id': 'INTEREST_GLOBAL', 'type': 'INTEREST', 'card': int_tile, 'editor': int_editor})

                # Create Consolidated Penalty Tile
                pen_roman = self.db.to_roman(len(self.scn_issue_cards) + 2).lower()
                pen_text = f"{pen_roman}. Penalty should not be imposed on them under the provision of Section 73 (1) of CGST Act 2017 read with Section 122 (2) (a) of CGST Act, 2017 and corresponding section under the Kerala SGST Act, 2017 read with section 20 of the IGST Act, 2017, for the contraventions referred hereinabove."
                
                pen_tile = ModernCard(f"Penalty Demand (Clause {pen_roman})", collapsible=True)
                pen_editor = RichTextEditor()
                pen_editor.setHtml(pen_text)
                pen_editor.setMinimumHeight(120)
                pen_editor.textChanged.connect(lambda: self.trigger_preview() if not self.is_scn_phase1() else None)
                pen_tile.addWidget(pen_editor)
                self.demand_tiles_layout.addWidget(pen_tile)
                self.demand_tiles.append({'issue_id': 'PENALTY_GLOBAL', 'type': 'PENALTY', 'card': pen_tile, 'editor': pen_editor})
                
            self.trigger_preview()
            
        except Exception as e:
            print(f"Error syncing demand tiles: {e}")
            import traceback
            traceback.print_exc()
                

            QMessageBox.warning(self, "Error", f"Failed to generate demand text: {e}")

    def save_document(self, doc_type="SCN"):
        """Save SCN document with authoritative structural integrity"""
        # Phase-1 Isolation: Structurally block save during Step-2 (Adoption)
        if doc_type == "SCN" and self.is_scn_phase1():
             print("ProceedingsWorkspace: Autopersist blocked in Step-2 Adoption phase.")
             return

        if not self.proceeding_id:
            return
            
        print(f"ProceedingsWorkspace: Saving {doc_type} draft...")
        
        try:
            if doc_type == "SCN":
                # Aggregate issue data using the authoritative schema (New Persistence)
                self.persist_scn_issues()
                
                # Aggregate Demand Text from Tiles
                full_demand_text = ""
                demand_tiles_data = []
                
                if hasattr(self, 'demand_tiles') and self.demand_tiles:
                    for tile in self.demand_tiles:
                        editor = tile['editor']
                        issue_id = tile['issue_id']
                        content = editor.toHtml()
                        full_demand_text += content + "<br><br>"
                        demand_tiles_data.append({'issue_id': issue_id, 'content': content})
                else:
                    # Fallback if no tiles (shouldn't happen with new UI)
                     full_demand_text = "<p>No demand details generated.</p>"

                metadata = {
                    "scn_number": self.scn_no_input.text(),
                    "scn_oc_number": self.scn_oc_input.text(),
                    "scn_date": self.scn_date_input.date().toString("yyyy-MM-dd"),
                    "reliance_documents": self.reliance_editor.toHtml(),
                    "copy_submitted_to": self.copy_to_editor.toHtml(),
                    "demand_text": full_demand_text,
                    "demand_tiles_data": demand_tiles_data,
                    "scn_issues_initialized": self.scn_issues_initialized
                }
                
                # Update additional_details
                current_details = self.proceeding_data.get('additional_details', {})
                if isinstance(current_details, str):
                    try: current_details = json.loads(current_details)
                    except: current_details = {}
                    
                current_details.update(metadata)
                
                self.db.update_proceeding(self.proceeding_id, {
                    "status": "SCN Draft",
                    "additional_details": json.dumps(current_details)
                })
                
                # Update local data
                self.proceeding_data['additional_details'] = current_details
                
                QMessageBox.information(self, "Success", "Show Cause Notice draft saved successfully!")
                return True
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving SCN: {e}")
            print(f"Error saving SCN: {e}")
            return False

    def _find_template_for_scrutiny_item(self, item, template_map):
        """Heuristic to find a matching template for a scrutiny result item"""
        # 1. Try if template_id is directly in item (for future-proofing)
        if 'template_id' in item and item['template_id'] in template_map:
            return template_map[item['template_id']]
            
        # 2. Try matching by category
        cat = str(item.get('category', '')).lower()
        desc = str(item.get('description', '')).lower()
        
        for tid, t in template_map.items():
            name = str(t.get('issue_name', '')).lower()
            if name == cat or name == desc:
                return t
                
        # 3. Fallback to generic
        return {'issue_id': 'GENERIC_ISSUE', 'issue_name': item.get('description') or item.get('category'), 'variables': {}}

    def _show_blocking_msg(self, message):
        """Show a blocking message in Step 2 for empty states"""
        # Clear existing cards
        while self.scn_issues_layout.count():
            item = self.scn_issues_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
            
        lbl = QLabel(message)
        lbl.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 12pt; margin: 50px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scn_issues_layout.addWidget(lbl)

    def toggle_act_row(self, act_name, state):
        """Add or remove row for the selected act"""
        if state == Qt.CheckState.Checked.value:
            # Add Row before Total row
            total_row = self.tax_table.rowCount() - 1
            self.tax_table.insertRow(total_row)
            
            # Act Name (Read-only)
            item = QTableWidgetItem(act_name)
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.tax_table.setItem(total_row, 0, item)
            
            # Get months for the financial year
            fy = self.proceeding_data.get('financial_year', '')
            months = self.get_fy_months(fy)
            
            # Period From (Dropdown)
            from_combo = QComboBox()
            from_combo.addItems(months)
            from_combo.setStyleSheet("padding: 4px;")
            from_combo.currentTextChanged.connect(self.calculate_totals)
            self.tax_table.setCellWidget(total_row, 1, from_combo)
            
            # Period To (Dropdown)
            to_combo = QComboBox()
            to_combo.addItems(months)
            to_combo.setCurrentIndex(len(months) - 1)  # Default to last month
            to_combo.setStyleSheet("padding: 4px;")
            to_combo.currentTextChanged.connect(self.calculate_totals)
            self.tax_table.setCellWidget(total_row, 2, to_combo)
            
            # Editable cells for amounts
            for col in range(3, 7):
                self.tax_table.setItem(total_row, col, QTableWidgetItem("0"))
        else:
            # Remove Row
            for row in range(self.tax_table.rowCount() - 1):  # Exclude Total row
                item = self.tax_table.item(row, 0)
                if item and item.text() == act_name:
                    self.tax_table.removeRow(row)
                    break
        
        self.calculate_totals()
    
    def get_fy_months(self, fy_string):
        """Get list of months for a financial year (e.g., '2022-23' -> ['April 2022', 'May 2022', ...])"""
        if not fy_string or '-' not in fy_string:
            # Default to current FY
            import datetime
            year = datetime.date.today().year
            fy_string = f"{year}-{str(year+1)[-2:]}"
        
        try:
            start_year = int(fy_string.split('-')[0])
            end_year = int('20' + fy_string.split('-')[1])
        except:
            import datetime
            year = datetime.date.today().year
            start_year = year
            end_year = year + 1
        
        months = []
        month_names = ["April", "May", "June", "July", "August", "September", 
                      "October", "November", "December", "January", "February", "March"]
        
        for i, month in enumerate(month_names):
            if i < 9:  # April to December
                months.append(f"{month} {start_year}")
            else:  # January to March
                months.append(f"{month} {end_year}")
        
        return months

    def add_total_row(self):
        """Add Total row at the bottom"""
        row = self.tax_table.rowCount()
        self.tax_table.insertRow(row)
        
        # Total label
        item = QTableWidgetItem("Total")
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        item.setBackground(Qt.GlobalColor.lightGray)
        self.tax_table.setItem(row, 0, item)
        
        # Empty cells for periods
        for col in [1, 2]:
            item = QTableWidgetItem("-")
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(row, col, item)
        
        # Total amounts
        for col in range(3, 7):
            item = QTableWidgetItem("0")
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(row, col, item)

    def calculate_totals(self):
        """Calculate row totals and grand totals"""
        # Temporarily disconnect to avoid recursion
        try:
            self.tax_table.itemChanged.disconnect(self.calculate_totals)
        except:
            pass
        
        total_row = self.tax_table.rowCount() - 1
        if total_row < 0: return

        # Calculate each row's total (Tax + Interest + Penalty)
        for row in range(total_row):
            try:
                tax = float(self.tax_table.item(row, 3).text() or 0)
                interest = float(self.tax_table.item(row, 4).text() or 0)
                penalty = float(self.tax_table.item(row, 5).text() or 0)
                total = tax + interest + penalty
                self.tax_table.setItem(row, 6, QTableWidgetItem(str(total)))
            except (ValueError, AttributeError):
                pass
        
        # Calculate grand totals
        for col in range(3, 7):
            grand_total = 0
            for row in range(total_row):
                try:
                    value = float(self.tax_table.item(row, col).text() or 0)
                    grand_total += value
                except (ValueError, AttributeError):
                    pass
            
            item = QTableWidgetItem(str(grand_total))
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(total_row, col, item)
        
        # Reconnect signal
        self.tax_table.itemChanged.connect(self.calculate_totals)

    def open_asmt10_reference(self):
        """Open ASMT-10 in a modal overlay for reference"""
        source_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
        if not source_id:
            QMessageBox.information(self, "Reference", "No source ASMT-10 linked to this case.")
            return
            
        # Generate HTML (Simplified reuse of generator)
        scrutiny_data = self.db.get_scrutiny_case_data(source_id)
        if not scrutiny_data:
            QMessageBox.warning(self, "Reference", "Source scrutiny data could not be retrieved.")
            return
            
        case_info = {
            'case_id': scrutiny_data.get('case_id'),
            'financial_year': scrutiny_data.get('financial_year'),
            'section': scrutiny_data.get('section'),
            'notice_date': scrutiny_data.get('asmt10_finalised_on', '-'),
            'oc_number': scrutiny_data.get('oc_number', 'DRAFT'),
            'last_date_to_reply': scrutiny_data.get('last_date_to_reply', 'N/A')
        }
        taxpayer = scrutiny_data.get('taxpayer_details', {})
        issues = scrutiny_data.get('selected_issues', [])
        
        generator = ASMT10Generator()
        full_data = case_info.copy()
        full_data['taxpayer_details'] = taxpayer
        html = generator.generate_html(full_data, issues, for_preview=True)
        
        dlg = ASMT10ReferenceDialog(self, html)
        dlg.exec()

    def change_tab(self, index):
        self.content_stack.setCurrentIndex(index)
        if not self.is_scn_phase1():
            self.trigger_preview()

    def trigger_preview(self):
        self.preview_timer.start()


    def update_preview(self, context_key=None):
        """Standardized Preview Logic: Updates the global preview pane."""
        # Optimization: Don't render if preview is hidden
        if not self.preview_visible:
            return

        if not self.proceeding_id:
            return
            
        # 1. Resolve Context
        if not context_key:
            idx = self.content_stack.currentIndex()
            reverse_map = {0: "summary", 1: "drc01a", 2: "asmt10", 3: "scn", 4: "ph", 5: "order"}
            context_key = reverse_map.get(idx, "summary")

        # 2. Prevent preview for specific states if needed
        if context_key == "summary":
            self._clear_preview()
            return

        # 3. Generate HTML Content
        html = ""
        header_text = "Live Preview"
        
        if context_key == "drc01a":
            if bool(self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')):
                return
            html = self.generate_drc01a_html()
            header_text = "✏️ Draft – DRC-01A"
        elif context_key == "asmt10":
            scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
            if scrutiny_id:
                scrutiny_data = self.db.get_scrutiny_case_data(scrutiny_id)
                if scrutiny_data:
                    case_info = {
                        'case_id': scrutiny_data.get('case_id'),
                        'financial_year': scrutiny_data.get('financial_year'),
                        'section': scrutiny_data.get('section'),
                        'notice_date': scrutiny_data.get('asmt10_finalised_on', '-'),
                        'oc_number': scrutiny_data.get('oc_number', 'DRAFT'),
                        'last_date_to_reply': scrutiny_data.get('last_date_to_reply', 'N/A')
                    }
                    taxpayer = scrutiny_data.get('taxpayer_details', {})
                    issues = scrutiny_data.get('selected_issues', [])
                    generator = ASMT10Generator()
                    full_data = case_info.copy()
                    full_data['taxpayer_details'] = taxpayer
                    html = generator.generate_html(full_data, issues, for_preview=True)
                    header_text = "🔒 Finalised ASMT-10 — Reference"
                else:
                    html = "<h3>Source Data Missing</h3>"
            else:
                html = "<h3>No Source ASMT-10</h3>"
        elif context_key == "scn":
            html = self.render_scn()
            header_text = "✏️ Draft – Show Cause Notice"
        elif context_key == "ph":
            editor = getattr(self, "ph_editor", None)
            html = editor.toHtml() if editor else "<h3>PH Intimation Draft</h3>"
            header_text = "✏️ Draft – PH Intimation"
        elif context_key == "order":
            editor = getattr(self, "order_editor", None)
            html = editor.toHtml() if editor else "<h3>Order Draft</h3>"
            header_text = "✏️ Draft – Order in Original"
        
        if not html:
            self._clear_preview()
            return

        # 4. Render to UI
        # Target Header
        if hasattr(self, 'preview_label_widget'):
            self.preview_label_widget.setText(header_text)

        # [FIX] Direct HTML Rendering via QTextBrowser
        # Bypasses the fragile Image Generation pipeline (WeasyPrint PNG)
        if hasattr(self, 'preview_browser'):
            # Ensure base URL is set for any relative resource resolution (if needed)
            self.preview_browser.setHtml(html)
            
        # Legacy Fallback cleanup (if old widgets exist)
        if hasattr(self, 'preview_content_layout'):
            # If we accidentally have both, clear the old layout
            while self.preview_content_layout.count():
                item = self.preview_content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def _clear_preview(self):
        # [FIX] Clear Native Browser
        if hasattr(self, 'preview_browser'):
            self.preview_browser.setHtml("")
            
        # Legacy cleanup
        if hasattr(self, 'preview_content_layout'):
            while self.preview_content_layout.count():
                item = self.preview_content_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()

    def generate_drc01a_html(self):
        if not self.proceeding_data:
            return "<h3>No Case Data Loaded</h3>"
            
        # Load Template
        try:
            with open('templates/drc_01a.html', 'r', encoding='utf-8') as f:
                html = f.read()
        except:
            return "<h3>Template not found</h3>"
            
        # Taxpayer Details (Ensure flattened keys exist)
        tp = self.proceeding_data.get('taxpayer_details', {})
        if isinstance(tp, str):
            try: import json; tp = json.loads(tp)
            except: tp = {}
        elif tp is None:
            tp = {}
            
        gstin = self.proceeding_data.get('gstin', '') or tp.get('GSTIN', '')
        legal_name = self.proceeding_data.get('legal_name', '') or tp.get('Legal Name', '')
        trade_name = self.proceeding_data.get('trade_name', '') or tp.get('Trade Name', '')
        address = self.proceeding_data.get('address', '') or tp.get('Address', '')
        
        # Replace Placeholders with data from DB + Editors
        html = html.replace("{{GSTIN}}", str(gstin))
        html = html.replace("{{LegalName}}", str(legal_name))
        html = html.replace("{{TradeName}}", str(trade_name))
        html = html.replace("{{Address}}", str(address))
        html = html.replace("{{CaseID}}", self.proceeding_data.get('case_id', '') or '')
        html = html.replace("{{OCNumber}}", self.oc_number_input.text())
        html = html.replace("{{FinancialYear}}", self.proceeding_data.get('financial_year', '') or '')
        html = html.replace("{{SelectedSection}}", self.proceeding_data.get('initiating_section', '') or '')
        html = html.replace("{{FormType}}", self.proceeding_data.get('form_type', '') or '')
        
        # Issue Date (Use OC Date)
        issue_date_str = self.oc_date_input.date().toString("dd/MM/yyyy")
        html = html.replace("{{IssueDate}}", issue_date_str)
        html = html.replace("{{CurrentDate}}", issue_date_str) # Fallback if template still has it
        
        # Conditional Section Text
        section = self.proceeding_data.get('initiating_section', '')
        if "73" in section:
            section_title = "section 73(5)"
            section_body = "73(5)"
        elif "74" in section:
            section_title = "section 74(5)"
            section_body = "74(5)"
        else:
            section_title = "section 73(5)/section 74(5)"
            section_body = "73(5) / 74(5)"
            
        html = html.replace("{{SectionTitle}}", section_title)
        html = html.replace("{{SectionBody}}", section_body)

        # The user's HTML has {{IssueDescription}} and {{SectionsViolated}} but NO {{GroundsContent}}?
        # Wait, looking at the user's HTML:
        # <div class="section-title">Issue:</div>
        # <div>{{IssueDescription}}</div>
        # <div class="section-title">Sections Violated:</div>
        # <div>{{SectionsViolated}}</div>
        
        # So I should map the "Issues Involved" editor to {{IssueDescription}} 
        # and "Sections Violated" editor to {{SectionsViolated}}
        
        # Aggregate HTML from all Issue Cards
        issues_html = ""
        for card in self.issue_cards:
            issues_html += card.generate_html()
            issues_html += "<br><hr><br>" # Separator between issues
            
        html = html.replace("{{IssueDescription}}", issues_html)
        html = html.replace("{{SectionsViolated}}", self.sections_editor.toHtml())
        
        # Generate Tax Table HTML
        tax_table_html = self.generate_tax_table_html()
        html = html.replace("{{TaxTableRows}}", tax_table_html)
        
        # Calculate Tax Period Range from Table
        period_from_list = []
        period_to_list = []
        for row in range(self.tax_table.rowCount()):
            # Check if row is valid (not total row)
            if self.tax_table.item(row, 0) and self.tax_table.item(row, 0).text() != "Total":
                # Get period from QComboBox widgets or items
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                p_from = ""
                p_to = ""
                
                if isinstance(from_widget, QComboBox):
                    p_from = from_widget.currentText()
                elif self.tax_table.item(row, 1):
                    p_from = self.tax_table.item(row, 1).text()
                    
                if isinstance(to_widget, QComboBox):
                    p_to = to_widget.currentText()
                elif self.tax_table.item(row, 2):
                    p_to = self.tax_table.item(row, 2).text()
                
                if p_from: period_from_list.append(p_from)
                if p_to: period_to_list.append(p_to)
        
        # Simple logic: take first and last if available, otherwise empty
        tax_period_from = period_from_list[0] if period_from_list else ""
        tax_period_to = period_to_list[-1] if period_to_list else ""
        
        html = html.replace("{{TaxPeriodFrom}}", tax_period_from)
        html = html.replace("{{TaxPeriodTo}}", tax_period_to)
        
        # Get Last Date for Payment
        last_date_payment = self.payment_date.date().toString("dd/MM/yyyy")
        html = html.replace("{{LastDateForPayment}}", last_date_payment)
        
        # Get Last Date for Reply
        last_date_reply = self.reply_date.date().toString("dd/MM/yyyy")
        html = html.replace("{{LastDateForReply}}", last_date_reply)
        
        # Generate Conditional Advice Text based on Section
        # Use Adjudication Section if available (Adjudication Case), else Initiating Section (Scrutiny)
        section = self.proceeding_data.get('adjudication_section') or self.proceeding_data.get('initiating_section', '')
        print(f"DEBUG: Section value = '{section}'")  # Debug output
        
        if "73" in section:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
            print(f"DEBUG: Using Section 73 advice text")  # Debug output
        elif "74" in section:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
            print(f"DEBUG: Using Section 74 advice text")  # Debug output
        else:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."
            print(f"DEBUG: Using default advice text")  # Debug output
        
        print(f"DEBUG: Advice text = '{advice_text}'")  # Debug output
        html = html.replace("{{AdviceText}}", advice_text)
        
        # Inject letterhead if checkbox is checked
        if self.show_letterhead_cb.isChecked():
            try:
                from src.utils.config_manager import ConfigManager
                config = ConfigManager()
                letterhead_path = config.get_letterhead_path('pdf')
                with open(letterhead_path, 'r', encoding='utf-8') as f:
                    letterhead_html = f.read()
                html = html.replace('<div id="letterhead-placeholder"></div>', letterhead_html)
            except Exception as e:
                print(f"Error loading letterhead: {e}")
        
        # Clean up others
        for p in ["{{OCNumber}}", "{{SCNSection}}", "{{CurrentDate}}", "{{ComplianceDate}}", "{{TaxPeriodFrom}}", "{{TaxPeriodTo}}", "{{IssueDescription}}", "{{TaxAmount}}", "{{InterestAmount}}", "{{PenaltyAmount}}", "{{TotalAmount}}"]:
            html = html.replace(p, "_________________")
            
        return html

    def render_scn(self):
        """Render SCN HTML using Jinja2 template"""
        if not self.proceeding_data:
            return "<h3>No Case Data Loaded</h3>"
            
        try:
            # 1. Gather Data
            data = self.proceeding_data.copy()
            
            # Format Dates
            # Use SCN specific date if available, else fallback to issue_date (which is DRC-01A date usually)
            # Actually, we added scn_date_input
            scn_date = self.scn_date_input.date()
            data['issue_date'] = scn_date.toString("dd/MM/yyyy")
            data['year'] = scn_date.year()
            
            # Financial Year
            fy = data.get('financial_year', '') or ''
            data['current_financial_year'] = fy
            
            # OC No & SCN No (SCN Specific)
            data['oc_no'] = self.scn_oc_input.text() or "____"
            data['scn_no'] = self.scn_no_input.text() or "____"
            data['oc_no'] = self.scn_oc_input.text() or "____"
            data['scn_no'] = self.scn_no_input.text() or "____"
            # Prioritize adjudication_section
            data['initiating_section'] = data.get('adjudication_section') or data.get('initiating_section', '') or "____"
            
            # Taxpayer Details (Already in data, but ensure keys match template)
            tp = data.get('taxpayer_details', {})
            if tp is None: tp = {}
            if isinstance(tp, str): 
                try:
                    tp = json.loads(tp)
                except:
                    tp = {}
            
            data['legal_name'] = tp.get('Legal Name', '') or data.get('legal_name', '')
            data['trade_name'] = tp.get('Trade Name', '') or data.get('trade_name', '')
            data['address'] = tp.get('Address', '') or data.get('address', '')
            data['gstin'] = data.get('gstin', '')
            data['constitution_of_business'] = tp.get('Constitution of Business', 'Registered')
            
            # Officer Details (Mock for now, should come from Settings/Auth)
            data['officer_name'] = "VISHNU V"
            data['officer_designation'] = "Superintendent"
            data['designation'] = "Superintendent"
            data['jurisdiction'] = "Paravur Range"
            
            # Issues & Demands
            # 2. Issues Content
            issues_html = ""
            demand_html = ""
            
            total_tax = 0
            igst_total = 0
            cgst_total = 0
            sgst_total = 0

            # Start numbering from Para 3 (Para 1=Intro, Para 2=References)
            current_para_num = 3

            if hasattr(self, 'scn_issue_cards') and self.scn_issue_cards:
                # New Logic: Render from self.scn_issue_cards (Live Draft)
                current_para_num = 1
                
                # 1. Introduction Para (Para 1) - Handled in Template
                current_para_num += 1
                
                # 2. Jurisdiction/Definition Para (Para 2) - Handled in Template
                current_para_num += 1
                
                # 3. Dynamic Issues (Para 3 onwards)
                for card in self.scn_issue_cards:
                        if not card.get_data().get('is_enabled', True):
                            continue
                            
                        # Issue Title as Main Paragraph
                        title = card.display_title
                        i = card.issue_id
                        
                        # [FIX] Use Scoped Class Structure
                        issues_html += f"""
                        <table class="para-table">
                            <tr>
                                <td class="para-num">{current_para_num}.</td>
                                <td class="para-content"><strong>Issue No. {i}: {title}</strong></td>
                            </tr>
                        </table>
                        """
                        
                        # --- Sub Paragraphs (e.g., "3.1 Content...") ---
                        sub_para_count = 1
                        
                        # [FIX] Direct Separation of Content and Table
                        editor_part = card.editor.toHtml()
                        table_part = card.generate_table_html(card.template, card.variables)
                        
                        # Regex split for paragraphs
                        import re
                        editor_part = re.sub(r'<p>\s*&nbsp;\s*</p>', '', editor_part)
                        editor_part = re.sub(r'<p>\s*</p>', '', editor_part)
                        paras = re.findall(r'<p.*?>(.*?)</p>', editor_part, re.DOTALL)
                        
                        # Fallback for raw text
                        if not paras and editor_part.strip():
                            paras = [editor_part]
                            
                        for p_content in paras:
                            if p_content.strip():
                                # [FIX] Flatten text and Remove Wrapper
                                # 1. Replace all whitespace/newlines with single space
                                clean_content = re.sub(r'\s+', ' ', p_content).strip()
                                
                                # 2. Inject into P.legal-para (Qt Justification Contract)
                                num_str = f"{current_para_num}.{sub_para_count}"
                                issues_html += f"""
                                <table class="para-table">
                                    <tr>
                                        <td class="para-num">{num_str}</td>
                                        <td class="para-content">
                                            <p class="legal-para">{clean_content}</p>
                                        </td>
                                    </tr>
                                </table>
                                """
                                sub_para_count += 1
                        
                        # Table as Sub-Para
                        if table_part and table_part.strip():
                            num_str = f"{current_para_num}.{sub_para_count}"
                            issues_html += f"""
                            <table class="para-table">
                                <tr>
                                    <td class="para-num">{num_str}</td>
                                    <td class="para-content">{table_part}</td>
                                </tr>
                            </table>
                            """
                            sub_para_count += 1
                            
                        current_para_num += 1
                    
                        # Demand Summary Calculations
                        # demand_html += f"<li>Demand for {title}...</li>"
                        
                        # Totals
                        card_data = card.get_data()
                        breakdown = card_data.get('tax_breakdown', {})
                        for act, vals in breakdown.items():
                            tax = vals.get('tax', 0)
                            total_tax += tax
                            if act == 'IGST': igst_total += tax
                            elif act == 'CGST': cgst_total += tax
                            elif act == 'SGST': sgst_total += tax
            else:
                issues_html = "<p>No issues selected.</p>"

            # Pass the next available para number to the template for subsequent sections
            data['next_para_num'] = current_para_num
            
            # Explicitly calculate subsequent paragraph numbers
            data['para_demand'] = current_para_num
            data['para_payment'] = current_para_num + 1
            data['para_evidence'] = current_para_num + 2  # Was "As per Section 29..." merged? No, separate.
            # Wait, "As per Section 29" was Para 6 in template, "With regard to..." was Para 5.
            # Let's map them exactly to the template structure:
            # Para N: Demand
            # Para N+1: "With regard to..." (Payment/Penalty waiver)
            # Para N+2: "As per Section 29..." (Cancellation liability)
            # Para N+3: Hearing / Evidence
            # Para N+4: Ex-parte warning
            
            data['para_waiver'] = current_para_num + 1
            data['para_cancellation'] = current_para_num + 2
            data['para_hearing'] = current_para_num + 3
            data['para_exparte'] = current_para_num + 4
            
            # Additional clauses usually present in SCN
            data['para_prejudice'] = current_para_num + 5
            data['para_amendment'] = current_para_num + 6
            data['para_reliance'] = current_para_num + 7
            
            data['issues_content'] = issues_html
            data['issues_templates'] = issues_html
            
            # Demand Text (Loaded from Editor)
            # Demand Text (Loaded from Editor or Tiles)
            if hasattr(self, 'demand_tiles') and self.demand_tiles:
                 full_text = ""
                 for tile in self.demand_tiles:
                     full_text += tile['editor'].toHtml() + "<br><br>"
                 data['demand_text'] = full_text
            else:
                 # Fallback (though editor removed)
                 data['demand_text'] = "<p>No demand details generated.</p>"
            
            # Generate Tax Table HTML (Reuse DRC-01A table logic)
            data['tax_table'] = self.generate_tax_table_html()
            
            data['total_amount'] = f"{total_tax:,.2f}"
            data['igst_total'] = f"{igst_total:,.2f}"
            data['cgst_total'] = f"{cgst_total:,.2f}"
            data['sgst_total'] = f"{sgst_total:,.2f}"
            
            # Reliance Documents
            rel_text = self.reliance_editor.toPlainText()
            data['reliance_documents'] = [line for line in rel_text.split('\\n') if line.strip()]
            data['reliance_documents_placeholder'] = "No documents listed"
            
            # Copy Submitted To
            copy_text = self.copy_to_editor.toPlainText()
            data['copy_submitted_to'] = [line for line in copy_text.split('\\n') if line.strip()]
            data['copy_submitted_to_placeholder'] = "No copies listed"
            
            data['show_letterhead'] = self.show_letterhead_cb.isChecked()
            
            # Letterhead Content
            if data['show_letterhead']:
                try:
                    from src.utils.config_manager import ConfigManager
                    config = ConfigManager()
                    letterhead_path = config.get_letterhead_path('pdf')
                    with open(letterhead_path, 'r', encoding='utf-8') as f:
                        data['letter_head'] = f.read()
                except Exception as e:
                    print(f"Error loading letterhead: {e}")
                    data['letter_head'] = ""
            else:
                data['letter_head'] = ""

            # Section Logic
            section = data.get('initiating_section', '')
            data['section'] = section
            
            # 2. Load Template and CSS
            template_dir = os.path.join(os.getcwd(), 'templates')
            css_dir = os.path.join(template_dir, 'css')
            
            # Helper to read CSS safely
            def read_css(filename):
                path = os.path.join(css_dir, filename)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                return ""

            # Load CSS Content
            data['base_css'] = read_css('scn_base.css')
            
            # Determine Renderer CSS
            # Default to Qt (Preview) unless overridden
            renderer_mode = data.get('render_mode', 'qt') 
            if renderer_mode == 'pdf':
                data['renderer_css'] = read_css('scn_pdf.css')
            else:
                data['renderer_css'] = read_css('scn_qt.css')

            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template('scn.html')
            
            # 3. Render
            return template.render(**data)
            
        except Exception as e:
            print(f"Error rendering SCN: {e}")
            import traceback
            traceback.print_exc()
    def save_drc01a_metadata(self):
        """Save DRC-01A Metadata (OC No, Dates, etc.) to DB"""
        metadata = {
            "oc_number": self.oc_number_input.text(),
            "oc_date": self.oc_date_input.date().toString("yyyy-MM-dd"),
            "reply_date": self.reply_date.date().toString("yyyy-MM-dd"),
            "payment_date": self.payment_date.date().toString("yyyy-MM-dd"),
            "financial_year": self.proceeding_data.get('financial_year', ''),
            "initiating_section": self.proceeding_data.get('initiating_section', '')
        }
        
        # Tax Period Logic
        period_from_list = []
        period_to_list = []
        for row in range(self.tax_table.rowCount()):
            if self.tax_table.item(row, 0) and self.tax_table.item(row, 0).text() != "Total":
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                p_from = ""
                p_to = ""
                
                if isinstance(from_widget, QComboBox): p_from = from_widget.currentText()
                elif self.tax_table.item(row, 1): p_from = self.tax_table.item(row, 1).text()
                    
                if isinstance(to_widget, QComboBox): p_to = to_widget.currentText()
                elif self.tax_table.item(row, 2): p_to = self.tax_table.item(row, 2).text()
                
                if p_from: period_from_list.append(p_from)
                if p_to: period_to_list.append(p_to)
                
        metadata['tax_period_from'] = period_from_list[0] if period_from_list else ""
        metadata['tax_period_to'] = period_to_list[-1] if period_to_list else ""
        
        # Update DB
        current_details = self.proceeding_data.get('additional_details', {})
        if isinstance(current_details, str):
            try: current_details = json.loads(current_details)
            except: current_details = {}
            
        current_details.update(metadata)
        
        self.db.update_proceeding(self.proceeding_id, {
            "initiating_section": metadata['initiating_section'],
            "last_date_to_reply": metadata['reply_date'],
            "additional_details": json.dumps(current_details)
        })
        
        # Update local data
        self.proceeding_data.update(metadata)
        self.proceeding_data['additional_details'] = current_details

    def save_drc01a(self):
        """Save DRC-01A Draft"""
        # 1. Aggregate HTML for Document
        issues_html = ""
        issues_list = []
        
        for card in self.issue_cards:
            issues_html += card.generate_html()
            issues_html += "<br><hr><br>"
            
            # Collect structured data for restoration
            issues_list.append({
                'issue_id': card.template.get('issue_id', 'UNKNOWN'),
                'data': card.get_data()
            })
            
        # 2. Save Document HTML (for View Mode)
        doc_data = {
            "proceeding_id": self.proceeding_id,
            "doc_type": "DRC-01A",
            "content_html": issues_html,
            "is_final": 0
        }
        self.db.save_document(doc_data)
        
        # 3. Save Structured Draft Data to case_issues table
        self.db.save_case_issues(self.proceeding_id, issues_list, stage='DRC-01A')
        
        # 4. Save Metadata
        self.save_drc01a_metadata()
        
        self.db.update_proceeding(self.proceeding_id, {
            "status": "DRC-01A Draft"
        })

        QMessageBox.information(self, "Success", "DRC-01A draft saved successfully!")

    def generate_tax_table_html(self):
        """Generate HTML table rows from tax_table widget"""
        rows_html = ""
        try:
            for row in range(self.tax_table.rowCount()):
                item_act = self.tax_table.item(row, 0)
                act = item_act.text() if item_act else ""
                
                # Get period from QComboBox widgets
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                if isinstance(from_widget, QComboBox):
                    period_from = from_widget.currentText()
                else:
                    item_from = self.tax_table.item(row, 1)
                    period_from = item_from.text() if item_from else ""
                    
                if isinstance(to_widget, QComboBox):
                    period_to = to_widget.currentText()
                else:
                    item_to = self.tax_table.item(row, 2)
                    period_to = item_to.text() if item_to else ""
                
                item_tax = self.tax_table.item(row, 3)
                tax = item_tax.text() if item_tax else "0"
                
                item_int = self.tax_table.item(row, 4)
                interest = item_int.text() if item_int else "0"
                
                item_pen = self.tax_table.item(row, 5)
                penalty = item_pen.text() if item_pen else "0"
                
                item_tot = self.tax_table.item(row, 6)
                total = item_tot.text() if item_tot else "0"
                
                rows_html += f"""
                <tr>
                    <td style="border: 1px solid black; padding: 8px;">{act}</td>
                    <td style="border: 1px solid black; padding: 8px;">{period_from}</td>
                    <td style="border: 1px solid black; padding: 8px;">{period_to}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{tax}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{interest}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{penalty}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{total}</td>
                </tr>
                """
        except Exception as e:
            print(f"Error generating tax table HTML: {e}")
            return "<tr><td colspan='7'>Error loading tax details</td></tr>"
    
        return rows_html

    def generate_pdf(self):
        """Generate PDF for current tab"""
        try:
            current_index = self.content_stack.currentIndex()
            
            # Determine content based on tab
            html_content = ""
            filename_prefix = "Document"
            doc_type = "Document"
            
            if current_index == 1: # DRC-01A
                # AUTO-SAVE: Ensure DB is up to date before generation
                self.save_drc01a_metadata()
                
                html_content = self.generate_drc01a_html()
                oc_no = self.oc_number_input.text() or "DRAFT"
                # Sanitize OC No for filename
                safe_oc = "".join([c for c in oc_no if c.isalnum() or c in ('-','_')])
                default_filename = f"DRC-01A_{safe_oc}.pdf"
                doc_type = "DRC 01A"
            elif current_index == 2: # ASMT-10
                # Reuse the ASMT-10 HTML generation logic
                scrutiny_id = self.proceeding_data.get('source_scrutiny_id') or self.proceeding_data.get('scrutiny_id')
                if scrutiny_id:
                    scrutiny_data = self.db.get_scrutiny_case_data(scrutiny_id)
                    if scrutiny_data:
                        case_info = {
                            'case_id': scrutiny_data.get('case_id'),
                            'financial_year': scrutiny_data.get('financial_year'),
                            'section': scrutiny_data.get('section'),
                            'notice_date': scrutiny_data.get('asmt10_finalised_on', '-'),
                            'oc_number': scrutiny_data.get('oc_number', 'DRAFT')
                        }
                        taxpayer = scrutiny_data.get('taxpayer_details', {})
                        issues = scrutiny_data.get('selected_issues', [])
                        generator = ASMT10Generator()
                        full_data = case_info.copy()
                        full_data['taxpayer_details'] = taxpayer
                        html_content = generator.generate_html(full_data, issues)
                        filename_prefix = f"ASMT-10_{case_id}"
                        default_filename = f"{filename_prefix}.pdf"
                        doc_type = "ASMT-10"
                    else:
                        QMessageBox.warning(self, "Error", "Source scrutiny data could not be retrieved.")
                        return
                else:
                    QMessageBox.warning(self, "Error", "No source ASMT-10 linked to this case.")
                    return
            elif current_index == 3: # SCN
                if self.is_scn_phase1():
                    QMessageBox.warning(self, "Locked", "SCN PDF generation is locked during Phase-1.")
                    return
                html_content = self.render_scn()
                case_id = self.proceeding_data.get('case_issue_id', 'DRAFT').replace('/', '_')
                default_filename = f"SCN_{case_id}.pdf"
                doc_type = "Show Cause Notice"
            else:
                QMessageBox.warning(self, "Error", f"PDF generation not supported for tab index {current_index} yet.")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save PDF As",
                default_filename,
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Generate PDF using the correct method
                import shutil
                from src.utils.document_generator import DocumentGenerator
                
                # Extract just the filename without extension
                filename_only = os.path.splitext(os.path.basename(file_path))[0]
                
                doc_gen = DocumentGenerator()
                generated_path = doc_gen.generate_pdf_from_html(html_content, filename_only)
                
                if generated_path and os.path.exists(generated_path):
                    # Move the file to user-selected location
                    try:
                        shutil.move(generated_path, file_path)
                        
                        # 2. Auto-Register in OC Register -> REMOVED to prevent phantom entries on preview/draft
                        # oc_data = {
                        #     'OC_Number': oc_no if current_index == 1 else self.scn_oc_input.text(),
                        #     'OC_Content': doc_type,
                        #     'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"), # DB format
                        #     'OC_To': self.proceeding_data.get('legal_name', '')
                        # }
                        # self.db.add_oc_entry(self.proceeding_data.get('case_id'), oc_data)
                        pass # No implicit register write
                        
                        # 3. Save Document Record to DB (for View Mode)
                        doc_data = {
                            'proceeding_id': self.proceeding_data.get('id'),
                            'doc_type': doc_type,
                            'content_html': html_content,
                            'template_id': None, # Could link to template if needed
                            'template_version': 1,
                            'version_no': 1,
                            'is_final': 1,
                            'snapshot_path': file_path # Using PDF path as snapshot for now
                        }
                        self.db.save_document(doc_data)
                        
                        QMessageBox.information(self, "Success", f"PDF generated and OC Registered successfully!\n\nSaved to: {file_path}")
                        
                        # Open the file
                        try:
                            os.startfile(file_path)
                        except Exception as e:
                            print(f"Could not open file: {e}")
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"PDF was generated but could not be moved to selected location.\n\nGenerated at: {generated_path}\nError: {str(e)}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to generate PDF. Check console for errors.")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating PDF: {str(e)}")
            print(f"PDF Generation Error: {e}")
            import traceback
            traceback.print_exc()

    def generate_docx(self):
        """Generate DOCX document for DRC-01A"""
        try:
            # Check Tab
            current_index = self.content_stack.currentIndex()
            if current_index == 1: # DRC-01A
                pass
            elif current_index == 3: # SCN
                if self.is_scn_phase1():
                    QMessageBox.warning(self, "Locked", "SCN DOCX generation is locked during Phase-1.")
                    return
            else:
                QMessageBox.information(self, "Info", "DOCX generation is only available for DRC-01A and SCN.")
                return

            # Check if proceeding is loaded
            if not self.proceeding_data or not isinstance(self.proceeding_data, dict):
                QMessageBox.warning(self, "Error", "No proceeding loaded. Please open a case first.")
                return

            # Save Metadata first!
            self.save_drc01a_metadata()

            # 1. Validate OC No (Mandatory)
            oc_no = self.oc_number_input.text().strip()
            if not oc_no:
                QMessageBox.warning(self, "Validation Error", "OC Number is mandatory. Please enter it in the Reference Details section.")
                return
                
            from PyQt6.QtWidgets import QFileDialog
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from bs4 import BeautifulSoup
            import os
            
            # Ask user for save location
            case_id = self.proceeding_data.get('case_id', 'DRAFT')
            if case_id and isinstance(case_id, str):
                case_id = case_id.replace('/', '_')
            else:
                case_id = 'DRAFT'
            default_filename = f"DRC-01A_{case_id}.docx"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save DOCX As",
                default_filename,
                "Word Documents (*.docx)"
            )
            
            if file_path:
                # Create DOCX document
                doc = Document()
                
                # Set margins
                sections = doc.sections
                for section in sections:
                    section.top_margin = Inches(1)
                    section.bottom_margin = Inches(1)
                    section.left_margin = Inches(1)
                    section.right_margin = Inches(1)
                
                # Add title
                title = doc.add_paragraph()
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = title.add_run("FORM DRC-01A")
                run.bold = True
                run.font.size = Pt(16)
                
                # Add case details
                doc.add_paragraph(f"Case ID: {self.proceeding_data.get('case_id', 'N/A')}")
                doc.add_paragraph(f"GSTIN: {self.proceeding_data.get('gstin', 'N/A')}")
                doc.add_paragraph(f"Legal Name: {self.proceeding_data.get('legal_name', 'N/A')}")
                doc.add_paragraph(f"Address: {self.proceeding_data.get('address', 'N/A')}")
                doc.add_paragraph()
                
                # Add Tax Demand Table
                if self.tax_table.rowCount() > 0:
                    heading = doc.add_paragraph()
                    run = heading.add_run("Tax Demand Details:")
                    run.bold = True
                    run.font.size = Pt(14)
                    
                    # Create table
                    table = doc.add_table(rows=self.tax_table.rowCount(), cols=7)
                    table.style = 'Light Grid Accent 1'
                    
                    # Add headers
                    headers = ["Act", "Tax Period From", "Tax Period To", "Tax (₹)", "Interest (₹)", "Penalty (₹)", "Total (₹)"]
                    for col, header in enumerate(headers):
                        cell = table.rows[0].cells[col]
                        cell.text = header
                        cell.paragraphs[0].runs[0].bold = True
                    
                    # Add data
                    for row in range(self.tax_table.rowCount()):
                        # Handle QComboBox widgets for periods in DOCX
                        from_widget = self.tax_table.cellWidget(row, 1)
                        to_widget = self.tax_table.cellWidget(row, 2)
                        
                        p_from = ""
                        p_to = ""
                        
                        if isinstance(from_widget, QComboBox):
                            p_from = from_widget.currentText()
                        elif self.tax_table.item(row, 1):
                            p_from = self.tax_table.item(row, 1).text()
                            
                        if isinstance(to_widget, QComboBox):
                            p_to = to_widget.currentText()
                        elif self.tax_table.item(row, 2):
                            p_to = self.tax_table.item(row, 2).text()

                        # Act
                        if self.tax_table.item(row, 0):
                            table.rows[row].cells[0].text = self.tax_table.item(row, 0).text()
                        
                        # Periods
                        table.rows[row].cells[1].text = p_from
                        table.rows[row].cells[2].text = p_to
                        
                        # Amounts
                        for col in range(3, 7):
                            item = self.tax_table.item(row, col)
                            if item:
                                table.rows[row].cells[col].text = item.text()
                    
                    doc.add_paragraph()
                
                # Add Issue (Mapped from Issues Editor)
                heading = doc.add_paragraph()
                run = heading.add_run("Issue:")
                run.bold = True
                run.font.size = Pt(14)
                doc.add_paragraph(self.issues_editor.toPlainText())
                doc.add_paragraph()

                # Add Sections Violated
                heading = doc.add_paragraph()
                run = heading.add_run("Sections Violated:")
                run.bold = True
                run.font.size = Pt(14)
                doc.add_paragraph(self.sections_editor.toPlainText())
                
                # Add Conditional Advice Text
                last_date_payment = self.payment_date.date().toString("dd/MM/yyyy")
                section = self.proceeding_data.get('initiating_section', '')
                
                if "73" in section:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
                elif "74" in section:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
                else:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."
                
                p = doc.add_paragraph()
                p.add_run(advice_text)

                # Add Submission Instructions
                last_date_reply = self.reply_date.date().toString("dd/MM/yyyy")
                p = doc.add_paragraph()
                p.add_run(f"In case you wish to file any submissions against the above ascertainment, the same may be furnished by {last_date_reply} in Part B of this Form.")
                
                # Add Signature Block
                doc.add_paragraph()
                doc.add_paragraph()
                
                sig = doc.add_paragraph()
                sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = sig.add_run("Proper Officer")
                run.bold = True
                
                doc.save(file_path)
                
                # 2. Auto-Register in OC Register -> REMOVED
                # oc_data = {
                #     'OC_Number': oc_no,
                #     'OC_Content': 'DRC 01A',
                #     'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"), # DB format
                #     'OC_To': self.proceeding_data.get('legal_name', '')
                # }
                # self.db.add_oc_entry(self.proceeding_data.get('case_id'), oc_data)
                
                QMessageBox.information(self, "Success", f"DOCX generated successfully!\n\nSaved to: {file_path}\n\nNote: This did NOT register to OC Log. Use 'Finalize' to issue.")
                
                # Open the file
                try:
                    os.startfile(file_path)
                except Exception as e:
                    print(f"Could not open file: {e}")
                sig = doc.add_paragraph()
                sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = sig.add_run("Proper Officer\n(Signature)\nName: ____________________\nDesignation: ____________________\nJurisdiction: ____________________")
                run.bold = True
                
                # Save document
                doc.save(file_path)
                
                QMessageBox.information(self, "Success", f"DOCX generated successfully!\n\nSaved to: {file_path}")
                
                # Open the file
                os.startfile(file_path)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating DOCX: {str(e)}")

    def check_existing_documents(self):
        """Check if documents exist and toggle view mode"""
        drc01a_exists = False
        scn_exists = False
        
        for doc in self.documents:
            if doc['doc_type'] == 'DRC 01A':
                drc01a_exists = True
                # Update preview image if available (Removed as per user request)
                # if doc.get('snapshot_path') and os.path.exists(doc['snapshot_path']):
                #     pixmap = QPixmap(doc['snapshot_path'])
                #     self.drc01a_view_preview.setPixmap(pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation))
                # else:
                #     self.drc01a_view_preview.setText("Preview not available")
                    
        self.toggle_view_mode("drc01a", drc01a_exists)
        self.toggle_view_mode("scn", scn_exists)

    def toggle_view_mode(self, doc_type, show_view):
        """Toggle between Draft and View containers"""
        if doc_type == "drc01a":
            if show_view:
                self.drc01a_draft_container.hide()
                self.drc01a_view_container.show()
            else:
                self.drc01a_view_container.hide()
                self.drc01a_draft_container.show()
                
        elif doc_type == "scn":
            if show_view:
                self.scn_draft_container.hide()
                self.scn_view_container.show()
            else:
                self.scn_view_container.hide()
                self.scn_draft_container.show()

    def _on_auto_generate_oc(self):
        """Helper for SCN Auto-Generate utility"""
        self._auto_generating_oc = True
        self.suggest_next_oc(self.scn_oc_input)
        if self.scn_oc_input.text():
            self.oc_provenance_lbl.setText("✔ Generated from O.C. Register")
            self.oc_provenance_lbl.show()
            # Tooltip safeguard
            self.scn_oc_input.setToolTip("Auto-generated value. You can still edit manually.")
        self._auto_generating_oc = False

    def _on_scn_oc_changed(self):
        """Handle OC text changes for SCN"""
        if not getattr(self, '_auto_generating_oc', False):
            # Manually edited
            if hasattr(self, 'oc_provenance_lbl'):
                self.oc_provenance_lbl.hide()
        
        self.trigger_preview()
        self.evaluate_scn_workflow_phase()

    def restore_draft_state(self):
        """Restore UI state from proceeding data with robust error isolation."""
        self.issue_restore_failed = False
        
        # --- BLOCK 1: Issue Restoration (Complex, High Risk) ---
        try:
            # Check for structured data in proceedings table
            add_details = self.proceeding_data.get('additional_details', {})
            # 1. Restore Issues from case_issues table
            saved_issues = self.db.get_case_issues(self.proceeding_id, stage='DRC-01A')
        
            # Clear existing cards first
            for card in self.issue_cards:
                card.setParent(None)
                self.issues_layout.removeWidget(card)
                card.deleteLater()
            self.issue_cards = []
            
            if saved_issues:
                # Load templates to reconstruct cards
                all_templates = self.db.get_issue_templates()
                    
                template_map = {t['issue_id']: t for t in all_templates}
                
                for issue_record in saved_issues:
                    issue_id = issue_record['issue_id']
                    data = issue_record['data']
                    issue_row_id = issue_record.get('id') # Ensure get_case_issues returns row ID too

                    # --- AUTO-REPAIR: Legacy Data Migration ---
                    # Constraint: Only if origin is 'SCN' AND source_issue_id exists
                    current_origin = issue_record.get('origin', 'SCN')
                    source_id_in_data = data.get('source_issue_id')
                    
                    if current_origin == 'SCN' and source_id_in_data and issue_row_id:
                         print(f"Auto-corrected legacy issue origin from SCN -> SCRUTINY (issue_id={issue_id})")
                         # 1. Update In-Memory
                         issue_record['origin'] = 'SCRUTINY'
                         data['origin'] = 'SCRUTINY'
                         
                         # 2. Persist Correction Immediately
                         self.db.update_case_issue_origin(issue_row_id, 'SCRUTINY')
                         try:
                             # Also update internal JSON blob to prevent regressive sync
                             import json
                             updated_json = json.dumps(data)
                             self.db.update_case_issue(issue_row_id, {'data_json': updated_json})
                         except: pass

                    # Pass corrected origin to card
                    if 'origin' not in data: data['origin'] = issue_record.get('origin', 'SCN')
                    
                    template = template_map.get(issue_id)
                    if not template:
                        print(f"WARNING: Template not found for issue_id: {issue_id}. Using fallback.")
                        # Fallback for unknown template
                        template = {'issue_id': issue_id, 'issue_name': 'Unknown Issue', 'variables': {}}
                    else:
                        print(f"SUCCESS: Restoring issue {issue_id} with template.")
                        
                    from src.ui.issue_card import IssueCard
                    card = IssueCard(template, parent=self)
                    
                    # Restore state using robust load_data method
                    card.load_data(data)
                    
                    # Add to layout
                    self.issues_layout.addWidget(card)
                    self.issue_cards.append(card)
                    
                    # Connect signals
                    card.removeClicked.connect(lambda c=card: self.remove_issue_card(c))
                    card.valuesChanged.connect(self.calculate_grand_totals)
                    card.valuesChanged.connect(lambda _: self.trigger_preview() if not self.is_scn_phase1() else None)
                    
                    # Trigger calculation to update totals based on restored variables
                    card.calculate_values()
                    
        except Exception as e:
            print(f"SCN Issue restore failed: {e}")
            import traceback
            traceback.print_exc()
            self.issue_restore_failed = True

        # --- BLOCK 2: Metadata Restoration (Foundational, Low Risk) ---
        try:
            add_details = self.proceeding_data.get('additional_details', {})
            if add_details:
                if 'oc_number' in add_details: 
                    self.oc_number_input.setText(add_details['oc_number'])
                if 'oc_date' in add_details: 
                    self.oc_date_input.setDate(QDate.fromString(add_details['oc_date'], "yyyy-MM-dd"))
                if 'reply_date' in add_details: 
                    self.reply_date.setDate(QDate.fromString(add_details['reply_date'], "yyyy-MM-dd"))
                
                # SCN Metadata (Step 1 ONLY in Phase-1)
                # Safeguard: Block signals during restoration to prevent unintended autosaves
                self.scn_no_input.blockSignals(True)
                self.scn_oc_input.blockSignals(True)
                self.scn_date_input.blockSignals(True)
                
                if 'scn_number' in add_details: self.scn_no_input.setText(add_details['scn_number'])
                if 'scn_oc_number' in add_details: self.scn_oc_input.setText(add_details['scn_oc_number'])
                if 'scn_date' in add_details: self.scn_date_input.setDate(QDate.fromString(add_details['scn_date'], "yyyy-MM-dd"))
                
                self.scn_no_input.blockSignals(False)
                self.scn_oc_input.blockSignals(False)
                self.scn_date_input.blockSignals(False)
                
                # Phase-2/3 Restoration: BLOCKED during Phase-1
                if not self.is_scn_phase1():
                    if 'reliance_documents' in add_details: self.reliance_editor.setHtml(add_details['reliance_documents'])
                    if 'copy_submitted_to' in add_details: self.copy_to_editor.setHtml(add_details['copy_submitted_to'])
                else:
                    print("ProceedingsWorkspace: Phase-1 Active. Skipping Phase-2/3 Restoration (Reliance/Copy-To).")

        except Exception as e:
             print(f"SCN Metadata restore failed: {e}")
             import traceback
             traceback.print_exc()
            
        # --- BLOCK 3: Finalization & UI Unlocking ---
        try:
            # 4. Final Validation
            self.evaluate_scn_workflow_phase()
            
            # Non-blocking warning for partial failures
            if self.issue_restore_failed:
                 print("Warning: Some issues failed to restore.")
                 # Optional: Show a subtle message or toast. 
                 # For now, we avoid popup spam on load, but logging is key.

        except Exception as e:
            print(f"Error in restoration finalization: {e}")

    def confirm_ph_finalization(self):
        """Finalize PH and Register OC"""
        if not self.ph_oc_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "OC Number is mandatory for registration.")
            return
            
        try:
            oc_data = {
                'OC_Number': self.ph_oc_input.text(),
                'OC_Date': self.ph_oc_date.date().toString("yyyy-MM-dd"),
                'OC_Content': f"Personal Hearing Intimation issued for GSTIN {self.proceeding_data.get('gstin','')}.",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            self.db.add_oc_entry(self.proceeding_id, oc_data)
            
            # Update status
            self.db.update_proceeding(self.proceeding_id, {"status": "PH Intimated"})
            
            QMessageBox.information(self, "Success", "PH Intimation Finalized and OC Registered.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to finalize PH: {e}")

    def confirm_order_finalization(self):
        """Finalize Order and Register OC"""
        if not self.order_oc_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "OC Number is mandatory for registration.")
            return
            
        try:
            oc_data = {
                'OC_Number': self.order_oc_input.text(),
                'OC_Date': self.order_oc_date.date().toString("yyyy-MM-dd"),
                'OC_Content': f"Final Order (DRC-07) issued for GSTIN {self.proceeding_data.get('gstin','')}.",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            self.db.add_oc_entry(self.proceeding_id, oc_data)
            
            # Update status
            self.db.update_proceeding(self.proceeding_id, {"status": "Order Issued"})
            
            QMessageBox.information(self, "Success", "Order Finalized and OC Registered.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to finalize Order: {e}")

    def suggest_next_oc(self, input_field: QLineEdit):
        """Fetch next available OC number and set it to input"""
        try:
            import datetime
            current_year = datetime.date.today().year
            
            # Fetch next number from DB
            # We assume format XXX/YEAR
            next_num = self.db.get_next_oc_number(str(current_year))
            
            formatted_oc = f"{next_num}/{current_year}"
            input_field.setText(formatted_oc)
            
        except Exception as e:
            print(f"Error suggesting OC: {e}")
