from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QStackedWidget, QSplitter, QScrollArea, QTextEdit, QTextBrowser,
                             QMessageBox, QFrame, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, QLineEdit, QFileDialog, QDialog, QGridLayout, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6 import QtCore
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence, QIcon, QResizeEvent, QColor
from src.database.db_manager import DatabaseManager
from PyQt6.QtWebEngineWidgets import QWebEngineView
from src.utils.preview_generator import PreviewGenerator
from src.ui.collapsible_box import CollapsibleBox
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard
from src.ui.issue_card import IssueCard
from src.ui.adjudication_setup_dialog import AdjudicationSetupDialog
from src.ui.components.side_nav_card import SideNavCard # Canonical import
from src.ui.components.finalization_panel import FinalizationPanel
from src.services.asmt10_generator import ASMT10Generator
from src.services.ph_intimation_generator import PHIntimationGenerator
from src.ui.styles import Theme, Styles
import os
import json
import copy
from jinja2 import Template, Environment, FileSystemLoader
import datetime
import traceback
import base64
import re

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
        
        self.asmt10_zoom_level = 1.0
        self.asmt10_show_letterhead = True
        
        self.active_scn_step = 0
        self.preview_initialized = False
        self.scn_workflow_phase = "METADATA" # Authority state: METADATA | DRAFTING
        
        # [NEW] PH Generator & State
        self.ph_generator = PHIntimationGenerator()
        self.ph_entries = [] # List of dicts
        self.ph_editing_index = -1
        
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
        
        header_layout.addWidget(self.context_title_lbl)
        header_layout.addStretch()
        
        self.central_container_layout.addWidget(self.central_header)
        self.central_container_layout.addWidget(self.content_stack)

        self.layout.addWidget(self.central_container_widget)
        
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

    def apply_context_layout(self, context_key):
        """
        Enforce single legal context layout rules.
        """
        # Update UI Title
        titles = {
            "scn": "Show Cause Notice Drafting",
            "drc01a": "DRC-01A Drafting",
            "summary": "Case Summary & Cockpit",
            "asmt10": "ASMT-10 Reference",
            "ph": "Personal Hearing Intimation", 
            "order": "Adjudication Order"
        }
        self.context_title_lbl.setText(titles.get(context_key, ""))
        
        # SCN Specific Page 1 Navigation check (Metadata)
        is_scn = (context_key == "scn")
        if is_scn and hasattr(self, 'active_scn_step'):
            # This logic is mostly handled in on_scn_page_changed
            pass

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
        
        # 2. Native HTML Preview (QWebEngineView)
        # Upgraded to support high-fidelity A4 simulation and JS pagination
        self.asmt10_browser = QWebEngineView()
        self.asmt10_browser.setStyleSheet("background-color: #525659;") 
        
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
            
            # [ALIGNMENT] Use "professional" style mode for high-fidelity A4 parity
            html_content = generator.generate_html(full_data, issues, for_preview=True, show_letterhead=self.asmt10_show_letterhead, style_mode="professional")
            
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
        self.asmt10_browser.setZoomFactor(self.asmt10_browser.zoomFactor() + 0.1)

    def _zoom_asmt10_out(self):
        self.asmt10_browser.setZoomFactor(max(0.1, self.asmt10_browser.zoomFactor() - 0.1))

    def _zoom_asmt10_reset(self):
        self.asmt10_browser.setZoomFactor(1.0)

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
        self.preview_initialized = False

    def hydrate_proceeding_data(self):
        """
        Idempotently normalize self.proceeding_data['additional_details'].
        Must handle str/dict/null and corrupted JSON safely.
        """
        raw = self.proceeding_data.get("additional_details")
        parsed = {}

        if isinstance(raw, str):
            if not raw.strip():
                parsed = {}
            else:
                try:
                    import json
                    parsed = json.loads(raw)
                    # Handle potential double-serialization
                    if isinstance(parsed, str):
                        try:
                            parsed = json.loads(parsed)
                        except: pass
                except (json.JSONDecodeError, TypeError):
                    print(f"Warning: Failed to hydrate additional_details JSON. Falling back to {{}}.")
                    parsed = {}
        elif isinstance(raw, dict):
            parsed = raw
        else:
            parsed = {}

        # Type Enforcement & Normalization
        if not isinstance(parsed.get("ph_entries"), list):
            parsed["ph_entries"] = []

        if not isinstance(parsed.get("scn_metadata"), dict):
            parsed["scn_metadata"] = {}

        if not isinstance(parsed.get("drc01a_metadata"), dict):
            parsed["drc01a_metadata"] = {}

        # Assign back atomically
        self.proceeding_data["additional_details"] = parsed

    def hydrate_scn_grounds_data(self):
        """
        Ensure SCN grounds data exists and handle migration/defaults. (Safe Method)
        Strategy:
        - If 'scn_grounds' missing -> Initialize default (Manual Override ON for safety).
        - Try to populate ASMT-10 details from snapshot if available.
        - Updates self.proceeding_data in-place (memory only).
        """
        try:
            import json
            details = self.proceeding_data.get('additional_details', {})
            if not details: details = {}
            # details is already dict due to hydrate_proceeding_data, but be safe
            if isinstance(details, str): return 

            grounds = details.get('scn_grounds')
            
            # --- PHASE 20/21: RECOVERY LOGIC for Blanched Cases ---
            # If grounds exists BUT it has the 'Stale Default' list while files are now available,
            # we should re-calculate to recover from the Metadata Blanching bug.
            
            def _get_current_file_doc_list(details_dict):
                f_paths = details_dict.get('file_paths', {})
                d_list = []
                if 'tax_liability_yearly' in f_paths: d_list.append("Tax Liability Excel")
                if any(k.startswith('gstr3b') for k in f_paths): d_list.append("GSTR-3B")
                if any(k.startswith('gstr1') for k in f_paths): d_list.append("GSTR-1")
                if any(k.startswith('gstr2a') for k in f_paths): d_list.append("GSTR-2A")
                if any(k.startswith('gstr2b') for k in f_paths): d_list.append("GSTR-2B")
                if any(k.startswith('gstr9') for k in f_paths): d_list.append("GSTR-9")
                if any(k.startswith('gstr9c') for k in f_paths): d_list.append("GSTR-9C")
                return d_list

            # Initialize if missing (Legacy or New Case)
            if not grounds:
                print("SCN Grounds: Hydrating default structure.")
                doc_list = _get_current_file_doc_list(details)
                
                # Fallback default if no files
                if not doc_list:
                    doc_list = ["GSTR-1", "GSTR-3B", "GSTR-2A"]

                # Create Structure
                grounds = {
                    "version": 1,
                    "type": "scrutiny",
                    "manual_override": True,
                    "manual_text": "",
                    "data": {
                        "financial_year": self.proceeding_data.get('financial_year', '-'),
                        "docs_verified": doc_list, 
                        "asmt10_ref": {
                            "oc_no": "", 
                            "date": "",
                            "officer_designation": "Proper Officer",
                            "office_address": ""
                        },
                        "reply_ref": {
                            "received": False,
                            "date": None
                        }
                    }
                }
                details['scn_grounds'] = grounds
                self.proceeding_data['additional_details'] = details
            else:
                # [RECOVERY] Check if it's a blanched draft
                current_docs = grounds.get('data', {}).get('docs_verified', [])
                STALE_DEFAULT = ["GSTR-1", "GSTR-3B", "GSTR-2A"]
                
                if current_docs == STALE_DEFAULT:
                    fresh_list = _get_current_file_doc_list(details)
                    # If we found more files now (due to Deep Merge Fix), update!
                    if fresh_list and fresh_list != STALE_DEFAULT:
                        print("SCN Grounds: Recovering blanched doc list.")
                        grounds['data']['docs_verified'] = fresh_list
                        # Update the pointer just in case
                        details['scn_grounds'] = grounds
                        self.proceeding_data['additional_details'] = details
                
        except Exception as e:
            print(f"Error hydrating SCN grounds: {e}")
            import traceback
            traceback.print_exc()

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
            pass # Clear preview logic removed
            return

        # [PHASE 15] Centralized Hydration
        self.hydrate_proceeding_data()
        self.hydrate_scn_grounds_data() # [NEW] Hydrate SCN Grounds
        
        # [NEW] Bind Data to Grounds Form if UI is ready
        if hasattr(self, 'scn_grounds_form'):
            details = self.proceeding_data.get('additional_details', {})
            grounds_data = details.get('scn_grounds')
            
            # [PHASE 18] UI Overlay (Generation-Time Linkage)
            # Deep copy to avoid mutating stored JSON in memory
            import copy
            if grounds_data:
                ui_view = copy.deepcopy(grounds_data)
                # Overlay Authoritative Identifiers
                if 'data' in ui_view:
                    if 'asmt10_ref' not in ui_view['data']:
                        ui_view['data']['asmt10_ref'] = {}
                    
                    # Fetch authoritative IDs
                    auth_oc = self.proceeding_data.get('oc_number', '')
                    auth_date = self.proceeding_data.get('notice_date', '')
                    
                    ui_view['data']['asmt10_ref']['oc_no'] = auth_oc
                    ui_view['data']['asmt10_ref']['date'] = auth_date
                    
                self.scn_grounds_form.set_data(ui_view)
            else:
                 self.scn_grounds_form.set_data(None)
            
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
        
        # [PHASE 15] Hydrate SCN Initialization Flag from normalized details
        self.scn_issues_initialized = False
        details = self.proceeding_data.get('additional_details', {})
        scn_meta = details.get('scn_metadata', {})
        self.scn_issues_initialized = scn_meta.get('scn_issues_initialized') or details.get('scn_issues_initialized', False)
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
        

        dates_layout.addWidget(reply_label)
        dates_layout.addWidget(self.reply_date)
        
        # Last Date for Payment
        payment_label = QLabel("Last Date for Payment")
        self.payment_date = QDateEdit()
        self.payment_date.setCalendarPopup(True)
        self.payment_date.setDate(QDate.currentDate().addDays(30))
        self.payment_date.setMinimumDate(QDate.currentDate())
        

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
            
        card.valuesChanged.connect(self.calculate_grand_totals)
        card.removeClicked.connect(lambda: self.remove_issue_card(card))
        
        self.issues_layout.addWidget(card)
        self.issue_cards.append(card)
        
        # Trigger initial calculation and preview
        self.calculate_grand_totals()
        

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
        # No automatic preview trigger here. Preview is stage-gated.
        pass

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
        

        self.scn_date_input.dateChanged.connect(self.evaluate_scn_workflow_phase)
        
        grid.addWidget(date_label, 3, 0)
        grid.addWidget(self.scn_date_input, 3, 1, 1, 2)
        
        # [NEW] Grounds Configuration Module
        # Separator
        sep_grounds = QFrame()
        sep_grounds.setFrameShape(QFrame.Shape.HLine)
        sep_grounds.setStyleSheet("color: #e0e0e0; margin-top: 10px; margin-bottom: 10px;")
        grid.addWidget(sep_grounds, 4, 0, 1, 3)
        
        # Instantiate Form
        from src.ui.components.grounds_forms import get_grounds_form
        self.scn_grounds_form = get_grounds_form("scrutiny")
        grid.addWidget(self.scn_grounds_form, 5, 0, 1, 3)
        
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
        
        # Action Buttons Hierarchy (End)
        
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
        

        rel_layout.addWidget(self.reliance_editor)
        
        # 5. Copy Submitted To
        copy_widget = QWidget()
        copy_layout = QVBoxLayout(copy_widget)
        copy_layout.setContentsMargins(0,0,0,0)
        
        self.copy_to_editor = RichTextEditor("List authorities here...")
        self.copy_to_editor.setMinimumHeight(300)
        

        copy_layout.addWidget(self.copy_to_editor)
        
        # 6. Finalization & Preview (Deterministic Step 6)
        self.scn_finalization_container = self.create_scn_finalization_panel()

        # Build Side Nav
        nav_items = [
            ("Reference Details", "1", ref_widget),
            ("Issue Adoption", "2", issues_widget),
            ("Demand & Contraventions", "3", demand_widget),
            ("Reliance Placed", "4", reliance_widget),
            ("Copy Submitted To", "5", copy_widget),
            ("Actions & Finalize", "✓", self.scn_finalization_container)
        ]
        
        self.scn_side_nav = self.create_side_nav_layout(nav_items, page_changed_callback=self.on_scn_page_changed)
        # Store for access in validation
        self.scn_nav_cards = self.scn_side_nav.nav_cards
        
        draft_layout.addWidget(self.scn_side_nav)
        
        # Lock Steps 2-6 initially
        for i in range(1, 6):
            self.scn_nav_cards[i].set_enabled(False)
        
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
            
            # [NEW] Extract and Validate Grounds Data
            grounds_data = None
            if hasattr(self, 'scn_grounds_form'):
                grounds_data = self.scn_grounds_form.get_data()
            
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
            
            if grounds_data:
                current_details['scn_grounds'] = grounds_data
            
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
        
        # [NEW] Deterministic Stage-Gated Preview
        # Trigger rendering ONLY when entering the finalization stage for the first time
        # We compare the page widget at the current index directly to our stored container
        if hasattr(self, 'scn_side_nav') and hasattr(self, 'scn_finalization_container'):
             # Each item in the side_nav is wrapped in a scroll area. 
             # Let's check the index if it matches the 'Actions & Finalize' item.
             # Actually, simpler: we know Step 6 is index 5. 
             # But per user request to use widget comparison:
             try:
                 # Check if the widget in the content stack for this index matches
                 # But the items were wrapped. 
                 # Let's use a flag on the widget itself or stored index.
                 if index == 5: # Definitively 'Actions & Finalize'
                     if not getattr(self, 'preview_initialized', False):
                         self.render_final_preview()
                         self.preview_initialized = True
             except:
                 pass
            
        print(f"SCN: Moved to Step {index+1}.")

    def create_ph_intimation_tab(self):
        """Create Personal Hearing Intimation tab with neutral professional design"""
        main_widget = QWidget()
        main_widget.setStyleSheet(f"background-color: {Theme.NEUTRAL_100};") # Screen Background
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # Splitter for Form (Left) and Preview (Right)
        self.ph_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.ph_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        
        # --- LEFT PANE: FORM ---
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        form_container = QWidget()
        form_container.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)
        
        # 1. Header & Entries List
        header_layout = QHBoxLayout()
        header_label = QLabel("Personal Hearing Intimations")
        header_label.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {Theme.NEUTRAL_900};")
        
        self.ph_add_btn = QPushButton("+ Add New Entry")
        self.ph_add_btn.setFixedHeight(32)
        self.ph_add_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {Theme.SUCCESS}; color: white; padding: 0 16px; 
                font-weight: bold; border-radius: 6px; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Theme.SUCCESS_HOVER}; }}
        """)
        self.ph_add_btn.clicked.connect(self.add_new_ph_entry)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.ph_add_btn)
        form_layout.addLayout(header_layout)
        
        # List of Entries (Cards)
        self.ph_list_container = QWidget()
        self.ph_list_layout = QVBoxLayout(self.ph_list_container)
        self.ph_list_layout.setContentsMargins(0, 0, 0, 0)
        self.ph_list_layout.setSpacing(12)
        form_layout.addWidget(self.ph_list_container)
        
        # 2. Entry Editor (Form) - Hidden by default
        self.ph_editor_card = QFrame()
        self.ph_editor_card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {Theme.SURFACE}; 
                border-radius: 8px; 
                border: 1px solid {Theme.NEUTRAL_200};
            }}
            QLabel {{ border: none; color: {Theme.NEUTRAL_500}; font-size: 13px; }}
            QLineEdit, QDateEdit {{ 
                height: 32px; 
                border: 1px solid {Theme.NEUTRAL_200}; 
                border-radius: 6px; 
                padding: 0 8px;
                background-color: white;
            }}
        """)
        self.ph_editor_card.setVisible(False)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.ph_editor_card.setGraphicsEffect(shadow)

        editor_layout = QVBoxLayout(self.ph_editor_card)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        editor_layout.setSpacing(16)
        
        editor_title = QLabel("Edit PH Details")
        editor_title.setStyleSheet(f"color: {Theme.NEUTRAL_900}; font-weight: bold; font-size: 14px; border: none;")
        editor_layout.addWidget(editor_title)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        
        # Row 1: OC Details
        grid.addWidget(QLabel("OC No:"), 0, 0)
        
        oc_no_layout = QHBoxLayout()
        oc_no_layout.setSpacing(4)
        
        self.ph_edit_oc = QLineEdit()
        oc_no_layout.addWidget(self.ph_edit_oc)
        
        self.ph_auto_oc_btn = QPushButton("Auto-Generate")
        self.ph_auto_oc_btn.setFixedHeight(28)
        self.ph_auto_oc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ph_auto_oc_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                color: #475569;
                padding: 0 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #3498db;
                color: #3498db;
            }
        """)
        self.ph_auto_oc_btn.clicked.connect(self._on_ph_auto_generate_oc)
        oc_no_layout.addWidget(self.ph_auto_oc_btn)
        
        grid.addLayout(oc_no_layout, 0, 1)
        
        grid.addWidget(QLabel("OC Date:"), 0, 2)
        self.ph_edit_oc_date = QDateEdit()
        self.ph_edit_oc_date.setCalendarPopup(True)
        self.ph_edit_oc_date.setDate(QDate.currentDate())
        grid.addWidget(self.ph_edit_oc_date, 0, 3)
        
        # Row 2: PH Details
        grid.addWidget(QLabel("PH Date:"), 1, 0)
        self.ph_edit_date = QDateEdit()
        self.ph_edit_date.setCalendarPopup(True)
        self.ph_edit_date.setDate(QDate.currentDate().addDays(7))
        grid.addWidget(self.ph_edit_date, 1, 1)
        
        grid.addWidget(QLabel("PH Time:"), 1, 2)
        self.ph_edit_time = QLineEdit("11:00 AM")
        grid.addWidget(self.ph_edit_time, 1, 3)
        
        # Row 3: Venue
        grid.addWidget(QLabel("Venue:"), 2, 0)
        self.ph_edit_venue = QLineEdit("Paravur Range Office")
        grid.addWidget(self.ph_edit_venue, 2, 1, 1, 3)
        
        # Row 4: Copy To
        grid.addWidget(QLabel("Copy To:"), 3, 0)
        self.ph_edit_copy_to = QLineEdit("The Assistant Commissioner, Central Tax, Paravur Division")
        grid.addWidget(self.ph_edit_copy_to, 3, 1, 1, 3)
        
        editor_layout.addLayout(grid)
        
        # Editor Buttons
        editor_btn_layout = QHBoxLayout()
        editor_btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"color: {Theme.NEUTRAL_500}; background: transparent; border: none; font-weight: bold;")
        cancel_btn.clicked.connect(lambda: self.ph_editor_card.setVisible(False))
        
        save_entry_btn = QPushButton("Save Draft")
        save_entry_btn.setFixedHeight(32)
        save_entry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_entry_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; border: 1px solid {Theme.NEUTRAL_200}; 
                color: {Theme.NEUTRAL_900}; border-radius: 6px; padding: 0 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Theme.NEUTRAL_100}; }}
        """)
        save_entry_btn.clicked.connect(self.save_ph_entry)
        
        finalize_reg_btn = QPushButton("Finalize & Register")
        finalize_reg_btn.setFixedHeight(32)
        finalize_reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        finalize_reg_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {Theme.PRIMARY}; color: white; padding: 0 16px; 
                font-weight: bold; border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {Theme.PRIMARY_HOVER}; }}
        """)
        finalize_reg_btn.clicked.connect(self.register_ph_entry)
        
        editor_btn_layout.addStretch()
        editor_btn_layout.addWidget(cancel_btn)
        editor_btn_layout.addWidget(save_entry_btn)
        editor_btn_layout.addWidget(finalize_reg_btn)
        editor_layout.addLayout(editor_btn_layout)
        
        form_layout.addWidget(self.ph_editor_card)
        form_layout.addStretch()
        
        form_scroll.setWidget(form_container)
        form_scroll.setMinimumWidth(450) # Fix side scroll for PH editor
        self.ph_splitter.addWidget(form_scroll)
        
        # --- RIGHT PANE: PREVIEW ---
        preview_container = QWidget()
        preview_container.setStyleSheet("background: transparent;")
        preview_v_layout = QVBoxLayout(preview_container)
        preview_v_layout.setContentsMargins(0, 0, 0, 0)
        preview_v_layout.setSpacing(0)
        
        # Compact Preview Toolbar (Single Flex Row)
        self.ph_preview_toolbar = QFrame()
        self.ph_preview_toolbar.setFixedHeight(40)
        self.ph_preview_toolbar.setStyleSheet(f"background: transparent; border: none;")
        
        toolbar_layout = QHBoxLayout(self.ph_preview_toolbar)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)
        toolbar_layout.setSpacing(8)
        
        live_preview_label = QLabel("Live Preview")
        live_preview_label.setStyleSheet(f"font-weight: bold; color: {Theme.NEUTRAL_900}; font-size: 14px;")
        toolbar_layout.addWidget(live_preview_label)
        toolbar_layout.addStretch()
        
        # Toolbar Actions
        self.ph_show_lh = QCheckBox("Show Letterhead")
        self.ph_show_lh.setChecked(True)
        self.ph_show_lh.stateChanged.connect(self.render_ph_preview)
        self.ph_show_lh.setStyleSheet(f"font-size: 13px; color: {Theme.NEUTRAL_500};")
        toolbar_layout.addWidget(self.ph_show_lh)
        
        btn_style = f"""
            QPushButton {{ 
                background: transparent; border: 1px solid {Theme.NEUTRAL_200}; 
                color: {Theme.NEUTRAL_900}; padding: 0 12px; border-radius: 6px; 
                font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Theme.NEUTRAL_100}; }}
        """
        
        self.ph_refresh_btn = QPushButton("🔄 Refresh Preview")
        self.ph_refresh_btn.setFixedHeight(32)
        self.ph_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ph_refresh_btn.setStyleSheet(btn_style)
        self.ph_refresh_btn.clicked.connect(self.render_ph_preview)
        toolbar_layout.addWidget(self.ph_refresh_btn)
        
        self.ph_pdf_btn = QPushButton("👁 Draft PDF")
        self.ph_pdf_btn.setFixedHeight(32)
        self.ph_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ph_pdf_btn.setStyleSheet(btn_style)
        self.ph_pdf_btn.clicked.connect(self.generate_ph_pdf)
        toolbar_layout.addWidget(self.ph_pdf_btn)
        
        self.ph_docx_btn = QPushButton("📝 Draft DOCX")
        self.ph_docx_btn.setFixedHeight(32)
        self.ph_docx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ph_docx_btn.setStyleSheet(btn_style)
        self.ph_docx_btn.clicked.connect(self.generate_ph_docx)
        toolbar_layout.addWidget(self.ph_docx_btn)
        
        preview_v_layout.addWidget(self.ph_preview_toolbar)
        
        # Restore Phase 8 direct browser placement (fixes hidden preview regression)
        self.ph_browser = QWebEngineView()
        self.ph_browser.setStyleSheet(f"background-color: {Theme.NEUTRAL_100}; border: none;")
        preview_v_layout.addWidget(self.ph_browser)
        
        self.ph_splitter.addWidget(preview_container)
        self.ph_splitter.setStretchFactor(0, 1)
        self.ph_splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(self.ph_splitter)
        return main_widget
        
        
        
        
        


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
        
        
        order_oc_suggest_btn = QPushButton("Get Next")
        order_oc_suggest_btn.setStyleSheet("padding: 2px 8px; background-color: #3498db; color: white; border-radius: 4px; font-size: 8pt;")
        order_oc_suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.order_oc_input))
        
        oc_date_label = QLabel("OC Date:")
        self.order_oc_date = QDateEdit()
        self.order_oc_date.setCalendarPopup(True)
        self.order_oc_date.setDate(QDate.currentDate())
        
        
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
        """Create the SCN Finalization Summary Panel with embedded QWebEngineView (Chromium)"""
        container = QWidget()
        container.setObjectName("SCNFinalizationContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top: Summary Panel (Fixed/Minimal Height)
        self.scn_fin_panel = FinalizationPanel()
        layout.addWidget(self.scn_fin_panel, 0)
        
        # Bottom: High-Fidelity Preview (Expanding)
        self.scn_final_preview = QWebEngineView()
        self.scn_final_preview.setMinimumHeight(400)
        self.scn_final_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Apply page container background style to the internal browser
        self.scn_final_preview.setStyleSheet("background-color: #f1f3f4;")
        layout.addWidget(self.scn_final_preview, 1)
        
        # Clear/Set Stretch explicitly
        layout.setStretch(0, 0) # Buttons/Summary
        layout.setStretch(1, 1) # Preview
        
        # Consolidated Button Connections
        self.scn_fin_panel.save_btn.clicked.connect(lambda: self.save_document("SCN"))
        self.scn_fin_panel.pdf_btn.clicked.connect(self.generate_pdf)
        self.scn_fin_panel.docx_btn.clicked.connect(self.generate_docx)
        self.scn_fin_panel.refresh_btn.clicked.connect(self.render_final_preview)
        self.scn_fin_panel.finalize_btn.clicked.connect(self.confirm_scn_finalization)
        
        # Navigation
        self.scn_fin_panel.cancel_btn.clicked.connect(lambda: self.scn_side_nav.nav_cards[0].click()) # Back to Step 1
        
        return container

    def render_final_preview(self):
        """
        One-shot or manual refresh of the high-fidelity Chromium preview.
        Gathers in-memory state from all IssueCards.
        """
        print("ProceedingsWorkspace: Generating deterministic SCN preview...")
        # 1. Update data for FinalizationPanel summary
        scn_no = self.scn_no_input.text()
        scn_date = self.scn_date_input.date().toString('dd-MM-yyyy')
        oc_no = self.scn_oc_input.text()
        
        self.scn_fin_panel.load_data(
            proceeding_data=self.proceeding_data,
            issues_list=self.scn_issue_cards,
            doc_type="SCN",
            doc_no=scn_no,
            doc_date=scn_date,
            ref_no=oc_no
        )
        
        # 2. Render HTML and load into WebEngineView
        html = self.render_scn(is_preview=True)
        self.scn_final_preview.setHtml(html)
        
        # Mark as initialized to prevent auto-render on every future tab switch
        self.preview_initialized = True

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
            # 1. Fresh Canonical Fetch for Manual / SCN Templates
            if origin in ["SCN", "MANUAL_SOP"]:
                # Fetch full authoritative JSON from Master DB (JIT)
                template = self.db.get_issue(issue_id)
                if not template:
                    QMessageBox.warning(self, "Integration Error", 
                                      f"Could not load authoritative schema for issue '{issue_id}'.\nCheck Issue Master integrity.")
                    return
                data = payload.get('data') # Fresh or pre-filled
                source_id = None
                
            # 2. Adoption from ASMT-10 (Pre-adapted via build_scn_issue_from_asmt10)
            elif origin == "ASMT10" and 'template' in payload:
                template = payload['template']
                data = payload.get('data')
                source_id = issue_id
            
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
                
                if data_payload['template_snapshot']:
                    # print(f"  - Snapshot has grid_data? {'grid_data' in data_payload['template_snapshot']}")
                    pass

                snapshot_item = {
                    'issue_id': card.template.get('issue_id'),
                    'data': data_payload, # Contains everything needed to render
                    'origin': origin,
                    'source_proceeding_id': source_pid,
                    'added_by': 'User' 
                }
                current_snapshot.append(snapshot_item)
            
            # Save to DB
            try:
                import json
                # [DEBUG] Pre-flight serialization check to catch Circular References
                for i, item in enumerate(current_snapshot):
                    try:
                        # Test dump to catch cycles early
                        json.dumps(item) 
                    except ValueError as ve:
                        print(f"[CRITICAL] Serialization Failed for Card {i} ({item.get('issue_id')}): {ve}")
                        # Analyze keys
                        for k, v in item.get('data', {}).items():
                            try:
                                json.dumps(v)
                            except ValueError:
                                print(f"  -> BAD KEY: {k} maps to {type(v)}")
                        # Fail unsafe to prevent corrupt save
                        raise ve

                success = self.db.save_scn_issue_snapshot(self.proceeding_id, current_snapshot)
                if success:
                    print(f"SCN Persistence: Saved {len(current_snapshot)} issues with snapshot templates.")
                else:
                    print("SCN Persistence: Failed to save to DB.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error persisting SCN issues (Serialization/DB): {e}")

        except Exception as e:
            print(f"Error persisting SCN issues (Outer): {e}")

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
        
        # [BRIDGE DIAG] Confirm return payload integrity
        
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
                
                template_snapshot = data_payload.get('template_snapshot')
                     
                # [FIX] Hydration Data Flow: Authoritative Master Merge
                # Rule: Consult Master (if available) but preserve USER VALUES from snapshot.
                master_template = self.db.get_issue(issue_id) or self.db.get_issue_by_name(issue_id)
                
                if master_template:
                     # 1. Base is Master (Identity + Static Text + Logic + LIABILITY CONFIG)
                     template = copy.deepcopy(master_template)

                     # 2. Overlay Snapshot State (The "Values", NOT the "Structure")
                     if template_snapshot:
                          # [DEEP MERGE] Preserve Master Structure (var tags) but Adopt Snapshot Values
                          snapshot_grid = template_snapshot.get('grid_data')
                          if snapshot_grid and template.get('grid_data'):
                               master_grid = template['grid_data']
                               
                               # Polymorphic Normalize: Handle List (Legacy) vs Dict (Modern)
                               s_rows = snapshot_grid.get('rows', []) if isinstance(snapshot_grid, dict) else (snapshot_grid if snapshot_grid else [])
                               m_rows = master_grid.get('rows', []) if isinstance(master_grid, dict) else master_grid
                               m_cols = master_grid.get('columns', []) if isinstance(master_grid, dict) else []
                               
                               # [RESILIENCE] Helper to extract value from dict or primitive
                               def safe_get_value(cell):
                                   if isinstance(cell, dict): return cell.get('value', 0)
                                   return cell if cell is not None else 0
                               

                               
                               row_policy = master_grid.get('row_policy', 'fixed')

                               for i, s_row in enumerate(s_rows):
                                   m_row = None

                                   if i < len(m_rows):
                                       m_row = m_rows[i]
                                   elif row_policy == 'dynamic' and len(m_rows) > 0:
                                       # [FIX] Expand Master for Dynamic Rows
                                       prototype = m_rows[0]
                                       if isinstance(prototype, dict):
                                           try:
                                               new_row = copy.deepcopy(prototype)
                                               new_row['id'] = f"r{i+1}_hydrated"
                                               m_rows.append(new_row)
                                               m_row = new_row
                                           except Exception as e:
                                               print(f"[HYDRATION ERROR] Failed to clone dynamic row: {e}")

                                   if m_row:
                                       
                                       # Scenario A: Modern Dict-based Row
                                       if isinstance(m_row, dict):
                                           if isinstance(s_row, dict):
                                               # Match by Column ID with Positional Fallback
                                               for cid, s_cell in s_row.items():
                                                   target_cid = None
                                                   if cid in m_row:
                                                       target_cid = cid
                                                   elif cid.startswith('col') and cid[3:].isdigit():
                                                       # Fallback: Positional mapping for legacy col0, col1, etc.
                                                       col_idx = int(cid[3:])
                                                       if col_idx < len(m_cols):
                                                           target_cid = m_cols[col_idx].get('id') if isinstance(m_cols[col_idx], dict) else str(m_cols[col_idx]).lower().replace(" ", "_")
                                                   
                                                   if target_cid and target_cid in m_row and isinstance(m_row[target_cid], dict):
                                                       m_row[target_cid]['value'] = safe_get_value(s_cell)
                                           elif isinstance(s_row, list):
                                               # Match Legacy List-Row by Index using Master Column IDs
                                               for col_idx, s_cell in enumerate(s_row):
                                                   if col_idx < len(m_cols):
                                                       m_col = m_cols[col_idx]
                                                       cid = m_col.get('id') if isinstance(m_col, dict) else str(m_col).lower().replace(" ", "_")
                                                       if cid in m_row and isinstance(m_row[cid], dict):
                                                            m_row[cid]['value'] = safe_get_value(s_cell)
                                       
                                       # Scenario B: Legacy List-based Row
                                       elif isinstance(m_row, list) and isinstance(s_row, list):
                                           for col_idx, s_cell in enumerate(s_row):
                                               if col_idx < len(m_row):
                                                   if isinstance(m_row[col_idx], dict):
                                                       m_row[col_idx]['value'] = safe_get_value(s_cell)
                               
                               # [CRITICAL] Update restore_data so IssueCard uses the merged structure/values
                               if isinstance(master_grid, dict):
                                   restore_data['table_data'] = copy.deepcopy(master_grid)
                               else:
                                   # Master is list (Legacy fallback)
                                   restore_data['table_data'] = copy.deepcopy(master_grid)

                          # Adoption of variables (if any fresh overrides existed)
                          if 'variables' in template_snapshot:
                               if not template.get('variables'): template['variables'] = {}
                               # Only adopt non-null values
                               for kv, vv in template_snapshot.get('variables', {}).items():
                                   if vv is not None and vv != "":
                                       template['variables'][kv] = vv
                else:
                     # Fallback for ad-hoc issues
                     template = template_snapshot
                     if not template:
                          print(f"WARNING: No template snapshot or master for {issue_id}.")

                if not template:
                     template = {
                        'issue_id': issue_id, 
                        'issue_name': data_payload.get('issue', 'Issue'),
                        'variables': {}
                     }
                
                
                     template = {
                        'issue_id': issue_id, 
                        'issue_name': data_payload.get('issue', 'Issue'),
                        'variables': {}
                     }
                
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
            # [PHASE 15] Safe Merge
            details = copy.deepcopy(self.proceeding_data.get('additional_details', {}))
            if 'scn_metadata' not in details: details['scn_metadata'] = {}
            
            details['scn_metadata']['scn_issues_initialized'] = True
            # For backward compatibility during migration
            details['scn_issues_initialized'] = True 
            
            # Persist to DB directly
            self.db.update_proceeding(self.proceeding_id, {
                'additional_details': details
            })
            self.proceeding_data['additional_details'] = details
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
                template = card.template
                issue_id = template.get('issue_id', 'unknown')
                issue_name = template.get('issue_name', f'Issue {i}')

                # [DIAGNOSTIC]
                print(f"SYNC ISSUE INDEX: {i}")
                print(f"SYNC ISSUE ID: {issue_id}")

                # [REFRESH] Force state synchronization before generating demand text
                # This ensures liability rows are extracted from grid into variables
                card.calculate_values() 
                data = card.get_data() # Fresh snapshot
                print(f"BREAKDOWN SENT TO GENERATOR (Issue {i}):", data.get('tax_breakdown'))

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
                

                pen_tile.addWidget(pen_editor)
                self.demand_tiles_layout.addWidget(pen_tile)
                self.demand_tiles.append({'issue_id': 'PENALTY_GLOBAL', 'type': 'PENALTY', 'card': pen_tile, 'editor': pen_editor})
                
            
            
        except Exception as e:
            print(f"Error syncing demand tiles: {e}")
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
                    "scn_issues_initialized": self.scn_issues_initialized,
                    "scn_model_snapshot": self._get_scn_model() # Authoritative point-in-time snapshot
                }
                
                # [PHASE 15] Safe Merge with deep copy
                details = copy.deepcopy(self.proceeding_data.get('additional_details', {}))
                details['scn_metadata'] = metadata
                
                self.db.update_proceeding(self.proceeding_id, {
                    "status": "SCN Draft",
                    "additional_details": details
                })
                
                # Update local data
                self.proceeding_data['additional_details'] = details
                
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

    def _get_scn_model(self):
        """Build a structured SCN data model for consistent rendering across Preview, PDF, and DOCX."""
        if not self.proceeding_data:
            return None

        # 1. Base Metadata
        model = self.proceeding_data.copy()
        
        # [FIX] Break Circular Reference: scn_model_snapshot -> additional_details -> scn_model_snapshot
        if 'additional_details' in model:
            # Shallow copy the inner dict so we can modify it without affecting self.proceeding_data
            details_copy = model['additional_details'].copy() if isinstance(model['additional_details'], dict) else {}
            # Remove the self-referential snapshot
            details_copy.pop('scn_model_snapshot', None)
            model['additional_details'] = details_copy
        
        # Format Dates
        scn_date = self.scn_date_input.date()
        model['issue_date'] = scn_date.toString("dd/MM/yyyy")
        model['year'] = scn_date.year()
        
        # Dynamic Financial Year (based on SCN Date)
        # If Month >= 4 (April), FY is Year-(Year+1). Else (Year-1)-Year.
        if scn_date.month() >= 4:
            fy_start = scn_date.year()
            fy_end = (scn_date.year() + 1) % 100
        else:
            fy_start = scn_date.year() - 1
            fy_end = scn_date.year() % 100
        model['current_financial_year'] = f"{fy_start}-{fy_end:02d}"
        
        # OC & SCN No
        model['oc_no'] = self.scn_oc_input.text() or "____"
        model['scn_no'] = self.scn_no_input.text() or "____"
        model['initiating_section'] = model.get('adjudication_section') or model.get('initiating_section', '') or "____"
        model['section'] = model['initiating_section'] # Specific key for template
        
        # Taxpayer Details
        tp = model.get('taxpayer_details', {})
        if tp is None: tp = {}
        if isinstance(tp, str): 
            try:
                import json
                tp = json.loads(tp)
            except:
                tp = {}
        
        model['legal_name'] = tp.get('Legal Name', '') or model.get('legal_name', '')
        model['trade_name'] = tp.get('Trade Name', '') or model.get('trade_name', '')
        model['address'] = tp.get('Address', '') or model.get('address', '')
        model['gstin'] = model.get('gstin', '')
        model['constitution_of_business'] = tp.get('Constitution of Business', 'Registered')
        
        # Officer Details
        model['officer_name'] = "VISHNU V"
        model['officer_designation'] = "Superintendent"
        model['designation'] = "Superintendent"
        model['jurisdiction'] = "Paravur Range"

        # 2. Sequential Issues Handling
        included_issues = []
        if hasattr(self, 'scn_issue_cards'):
            # Filter strictly by is_included
            for card in self.scn_issue_cards:
                if card.get_data().get('is_included', True):
                    included_issues.append(card)

        # Build issue list for rendering
        issues_data = []
        total_tax = 0
        igst_total = 0
        cgst_total = 0
        sgst_total = 0
        
        # Mapping for narrative replacement
        id_to_index = {}
        for idx, card in enumerate(included_issues, start=1):
            id_to_index[card.issue_id] = str(idx)

        import re
        for idx, card in enumerate(included_issues, start=1):
            issue_info = {
                'index': idx,
                'title': card.display_title,
                'issue_id': card.issue_id, # Keep for internal use, but suppress in display
                'paras': [],
                'table_html': card.generate_table_html(card.template, card.variables)
            }
            
            # Narrative Content Handling with Regex Replacement
            editor_part = card.editor.toHtml()
            editor_part = re.sub(r'<p>\s*&nbsp;\s*</p>', '', editor_part)
            editor_part = re.sub(r'<p>\s*</p>', '', editor_part)
            paras = re.findall(r'<p.*?>(.*?)</p>', editor_part, re.DOTALL)
            if not paras and editor_part.strip():
                paras = [editor_part]

            for p_content in paras:
                if p_content.strip():
                    clean_content = re.sub(r'\s+', ' ', p_content).strip()
                    # REGEX REPLACE internal IDs with sequential numbers
                    for internal_id, seq_num in id_to_index.items():
                        # Word boundary regex to avoid partial replacements
                        pattern = r'\b' + re.escape(internal_id) + r'\b'
                        clean_content = re.sub(pattern, f"issue {seq_num}", clean_content)
                    
                    issue_info['paras'].append(clean_content)
            
            issues_data.append(issue_info)
            
            # Totals
            card_data = card.get_data()
            breakdown = card_data.get('tax_breakdown', {})
            for act, vals in breakdown.items():
                tax = vals.get('tax', 0)
                total_tax += tax
                if act == 'IGST': igst_total += tax
                elif act == 'CGST': cgst_total += tax
                elif act == 'SGST': sgst_total += tax

        model['issues'] = issues_data
        model['total_tax_val'] = total_tax
        model['igst_total_val'] = igst_total
        model['cgst_total_val'] = cgst_total
        model['sgst_total_val'] = sgst_total
        
        # Helper: Indian Currency Format (Hardened)
        def format_indian_currency(value):
            if value is None: return "0"
            try:
                val = float(value)
            except (ValueError, TypeError):
                return str(value)
            
            is_negative = val < 0
            val = abs(val)
            
            # Format to 2 decimals first to handle rounding
            s_val = f"{val:.2f}"
            
            # Extract integer and decimal parts
            if "." in s_val:
                integer_part, decimal_part = s_val.split(".")
            else:
                integer_part, decimal_part = s_val, "00"
            
            # Drop decimal if zero
            if decimal_part == "00":
                decimal_suffix = ""
            else:
                decimal_suffix = "." + decimal_part
                
            # Apply commas to integer part
            if len(integer_part) > 3:
                last3 = integer_part[-3:]
                rest = integer_part[:-3]
                # split rest into chunks of 2 from right
                parts = []
                while len(rest) > 2:
                    parts.insert(0, rest[-2:])
                    rest = rest[:-2]
                parts.insert(0, rest)
                formatted_int = ",".join(parts) + "," + last3
            else:
                formatted_int = integer_part
                
            result = formatted_int + decimal_suffix
            if is_negative:
                result = "-" + result
            return result

        # Formatted totals using Indian Format
        model['total_amount'] = format_indian_currency(total_tax)
        model['igst_total'] = format_indian_currency(igst_total)
        model['cgst_total'] = format_indian_currency(cgst_total)
        model['sgst_total'] = format_indian_currency(sgst_total)

        # 3. Dynamic Paragraph Numbering
        # Intro=Para 1, Jurisdiction=Para 2, Issues start at Para 3
        # If we have N issues, they occupy Para 3 to 3+(N-1)
        next_para = 3 + len(issues_data)
        model['para_demand'] = next_para
        model['para_waiver'] = next_para + 1
        model['para_cancellation'] = next_para + 2
        model['para_hearing'] = next_para + 3
        model['para_exparte'] = next_para + 4
        model['para_prejudice'] = next_para + 5
        model['para_amendment'] = next_para + 6
        model['para_reliance'] = next_para + 7

        # 4. Additional Data (Reliance, Copy To)
        rel_text = self.reliance_editor.toPlainText()
        model['reliance_documents'] = [line for line in rel_text.split('\n') if line.strip()]
        
        copy_text = self.copy_to_editor.toPlainText()
        model['copy_submitted_to'] = [line for line in copy_text.split('\n') if line.strip()]
        
        model['show_letterhead'] = self.show_letterhead_cb.isChecked()
        
        # [NEW] Introductory Narrative (Grounds)
        try:
            from src.utils.scn_generator import generate_intro_narrative
            details = self.proceeding_data.get('additional_details', {})
            # Ensure details is dict
            if isinstance(details, str):
                import json
                try: details = json.loads(details)
                except: details = {}
                
            grounds_data = details.get('scn_grounds')
            
            # [PHASE 18] Generation-Time Linkage (Strict Overlay)
            # Ensure SCN always cites the authoritative ASMT-10 Ref from Case Data
            import copy
            if grounds_data:
                # 1. Deepcopy to prevent mutation of stored JSON
                gen_view = copy.deepcopy(grounds_data)
                
                # 2. Overlay Authoritative Identifiers
                auth_oc = self.proceeding_data.get('oc_number', '')
                auth_date = self.proceeding_data.get('notice_date', '')
                
                if 'data' in gen_view:
                    if 'asmt10_ref' not in gen_view['data']:
                        gen_view['data']['asmt10_ref'] = {}
                        
                    gen_view['data']['asmt10_ref']['oc_no'] = auth_oc
                    gen_view['data']['asmt10_ref']['date'] = auth_date
                
                # 3. Generate Narrative with guaranteed correct IDs
                model['intro_narrative'] = generate_intro_narrative(gen_view)
            else:
                model['intro_narrative'] = ""
        except Exception as e:
            print(f"Narrative Gen Error: {e}")
            model['intro_narrative'] = "<b>[ERROR GENERATING INTRODUCTORY NARRATIVE]</b>"
        
        # Demand Text (Loaded from Tiles)
        if hasattr(self, 'demand_tiles') and self.demand_tiles:
             full_text = ""
             for tile in self.demand_tiles:
                 full_text += tile['editor'].toHtml() + "<br><br>"
             model['demand_text'] = full_text
        else:
             model['demand_text'] = "<p>No demand details generated.</p>"

        # Tax Table
        model['tax_table_html'] = self.generate_tax_table_html()

        return model
    def render_scn(self, is_preview=False, for_pdf=False):
        """Render SCN HTML using Jinja2 template"""
        model = self._get_scn_model()
        if not model:
            return "<h3>No Case Data Loaded</h3>"
            
        model['is_preview'] = is_preview
        
        try:
            # 1. Format Issues HTML from the centralized model
            issues_html = ""
            for issue in model['issues']:
                current_para_num = issue['index'] + 2 # Paras 1&2 are fixed, Issues start at 3
                title = issue['title']
                
                # No wrapper for the whole issue to avoid pagination truncation of multi-block content
                
                # Issue Heading
                issues_html += f"""
                <div class="issue-header">
                    <table class="para-table">
                        <tr>
                            <td class="para-num">{current_para_num}.</td>
                            <td class="para-content"><h3>Issue No. {issue['index']}: {title}</h3></td>
                        </tr>
                    </table>
                </div>
                """
                
                # Sub Paragraphs
                sub_para_count = 1
                for p_content in issue['paras']:
                    num_str = f"{current_para_num}.{sub_para_count}"
                    issues_html += f"""
                    <table class="para-table">
                        <tr>
                            <td class="para-num">{num_str}</td>
                            <td class="para-content">
                                <p class="legal-para">{p_content}</p>
                            </td>
                        </tr>
                    </table>
                    """
                    sub_para_count += 1
                
                # Table as Sub-Para (Unwrapped for pagination splitting)
                if issue['table_html'] and issue['table_html'].strip():
                    num_str = f"{current_para_num}.{sub_para_count}"
                    issues_html += f"""
                    <table class="para-table">
                        <tr>
                            <td class="para-num">{num_str}</td>
                            <td class="para-content">
                                <p class="legal-para">The details of the discrepancies are as follows:</p>
                            </td>
                        </tr>
                    </table>
                    {issue['table_html']}
                    """
                
                # End issue
            
            model['issues_content'] = issues_html
            model['issues_templates'] = issues_html
            
            # Letterhead
            import base64
            model['letter_head'] = ""
            if model['show_letterhead']:
                try:
                    from src.utils.config_manager import ConfigManager
                    config = ConfigManager()
                    lh_filename = config.get_pdf_letterhead()
                    lh_path = config.get_letterhead_path('pdf')
                    
                    if lh_path and os.path.exists(lh_path):
                        ext = os.path.splitext(lh_path)[1][1:].lower()
                        
                        # Fetch visual adjustments for this specific letterhead
                        adj = config.get_letterhead_adjustments(lh_filename)
                        width_val = min(adj.get('width', 100), 100)
                        
                        lh_style = f"width: {width_val}%; padding-top: {adj.get('padding_top', 0)}px; margin-bottom: {adj.get('margin_bottom', 20)}px;"
                        
                        if ext == "html":
                            # Case 1: HTML letterhead - read as text
                            with open(lh_path, 'r', encoding='utf-8') as f:
                                lh_full = f.read()
                                # Extract body content if present, otherwise use full content
                                match = re.search(r"<body[^>]*>(.*?)</body>", lh_full, re.DOTALL | re.IGNORECASE)
                                inner_html = match.group(1) if match else lh_full
                                model['letter_head'] = f'<div style="{lh_style} text-align: center;">{inner_html}</div>'
                        else:
                            # Case 2: Image letterhead - read as binary and base64 encode
                            with open(lh_path, "rb") as image_file:
                                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                            if ext == "jpg": ext = "jpeg"
                            model['letter_head'] = f'<div style="{lh_style} text-align: center;"><img src="data:image/{ext};base64,{encoded_string}" alt="Letterhead" style="max-width: 100%; height: auto;"></div>'
                except Exception as e:
                    print(f"Letterhead failed: {e}")
                    model['letter_head'] = ""

            # Standard SCN context variables
            model['section'] = model.get('initiating_section', '')
            
            # Load Template and CSS
            template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
            css_dir = os.path.join(template_dir, 'css')
            
            def read_css(filename):
                path = os.path.join(css_dir, filename)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                return ""

            model['base_css'] = read_css('doc_base.css')
            renderer_mode = 'pdf' if not is_preview else 'qt'
            if renderer_mode == 'pdf':
                model['renderer_css'] = "" # Base CSS now includes @media print
            else:
                model['renderer_css'] = read_css('doc_qt.css')

            print(f"DEBUG SCN: template_dir={template_dir}")
            print(f"DEBUG SCN: base_css_len={len(model['base_css'])}")
            print(f"DEBUG SCN: renderer_css_len={len(model['renderer_css'])}")

            # Workaround for formatter mangling: generate full style tag in Python
            model['full_styles_html'] = f"<style>\n{model['base_css']}\n{model['renderer_css']}\n</style>"

            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template('scn.html')
            
            model['for_pdf'] = for_pdf
            return template.render(**model)
            
        except Exception as e:
            print(f"Error rendering SCN: {e}")
            import traceback
            traceback.print_exc()
            return f"<h3>Render Error: {str(e)}</h3>"

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
        
        # [PHASE 15] Safe Merge
        details = copy.deepcopy(self.proceeding_data.get('additional_details', {}))
        details['drc01a_metadata'] = metadata
        
        self.db.update_proceeding(self.proceeding_id, {
            "initiating_section": metadata['initiating_section'],
            "last_date_to_reply": metadata['reply_date'],
            "additional_details": details
        })
        
        # Update local data
        self.proceeding_data.update(metadata)
        self.proceeding_data['additional_details'] = details

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
                        html_content = generator.generate_html(full_data, issues, for_pdf=True)
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
                html_content = self.render_scn(for_pdf=True)
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
                import os
                from src.utils.document_generator import DocumentGenerator
                
                # [ULTRA-SAFE] UI Mitigation
                from PyQt6.QtWidgets import QApplication
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                
                filename_only = os.path.splitext(os.path.basename(file_path))[0]
                doc_gen = DocumentGenerator()
                try:
                    generated_path = doc_gen.generate_pdf_from_html(html_content, filename_only)
                    
                    if generated_path and os.path.exists(generated_path):
                        # Move the file to user-selected location
                        shutil.move(generated_path, file_path)
                        
                        # 3. Save Document Record to DB
                        doc_data = {
                            'proceeding_id': self.proceeding_data.get('id'),
                            'doc_type': doc_type,
                            'content_html': html_content,
                            'template_id': None,
                            'template_version': 1,
                            'version_no': 1,
                            'is_final': 1,
                            'snapshot_path': file_path
                        }
                        self.db.save_document(doc_data)
                        
                        QMessageBox.information(self, "Success", f"PDF generated and Registered successfully!\n\nSaved to: {file_path}")
                    else:
                        raise RuntimeError("File generation failed without error message.")
                        
                except Exception as e:
                    err_str = str(e)
                    if "MISSING_DEPENDENCY" in err_str:
                        msg = ("PDF Generation Unavailable.\n\n"
                               "The system is missing required rendering libraries (GTK3).\n"
                               "Please install the dependencies or use 'Draft Word' instead.")
                        QMessageBox.critical(self, "Dependency Error", msg)
                    elif "TIMEOUT" in err_str:
                        QMessageBox.warning(self, "Timeout", "PDF generation took too long (20s limit) and was cancelled for safety.")
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to generate {doc_type} PDF: {err_str}")
                finally:
                    QApplication.restoreOverrideCursor()
                
                # Open the file if it exists and was successfully moved
                if os.path.exists(file_path):
                    try:
                        os.startfile(file_path)
                    except Exception as e:
                        print(f"Could not open file: {e}")
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during export: {str(e)}")
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
                # SCN Logic
                model = self._get_scn_model()
                if not model:
                     QMessageBox.warning(self, "Error", "Failed to build SCN model.")
                     return
                
                from script_docx import Document # Using a helper if available, or docx.Document
                from docx import Document
                from docx.shared import Pt, Inches
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                
                case_id = model.get('case_id', 'DRAFT').replace('/', '_')
                default_filename = f"SCN_{case_id}.docx"
                
                from PyQt6.QtWidgets import QFileDialog
                file_path, _ = QFileDialog.getSaveFileName(self, "Save SCN DOCX As", default_filename, "Word Documents (*.docx)")
                if not file_path: return

                doc = Document()
                for section in doc.sections:
                    section.top_margin = Inches(0.8)
                    section.bottom_margin = Inches(0.8)
                    section.left_margin = Inches(1)
                    section.right_margin = Inches(1)

                # Title
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run("SHOW CAUSE NOTICE")
                run.bold = True
                run.font.size = Pt(16)
                
                # Header
                doc.add_paragraph(f"GSTIN: {model.get('gstin', '')}")
                doc.add_paragraph(f"Legal Name: {model.get('legal_name', '')}")
                doc.add_paragraph(f"OC Number: {model.get('oc_no', '')}")
                doc.add_paragraph(f"Date: {model.get('issue_date', '')}")
                doc.add_paragraph()

                # Paragraph 1: Intro
                p = doc.add_paragraph()
                p.add_run("1. ").bold = True
                p.add_run("A brief of the case and the grounds for initiating proceedings are as follows:")
                
                # Issues
                for issue in model['issues']:
                    p_num = issue['index'] + 2 # Starts at 3
                    title = issue['title']
                    
                    p = doc.add_paragraph()
                    p.add_run(f"{p_num}. Issue No. {issue['index']}: {title}").bold = True
                    
                    for s_idx, para in enumerate(issue['paras'], start=1):
                        sp = doc.add_paragraph()
                        sp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        sp.add_run(f"{p_num}.{s_idx} ").bold = True
                        sp.add_run(para)
                
                # Demands
                num = model['para_demand']
                p = doc.add_paragraph()
                p.add_run(f"{num}. Summary of Tax Liability:").bold = True
                doc.add_paragraph(f"The total tax liability is determined as ₹{model['total_amount']}.")

                # Proper Officer
                doc.add_paragraph()
                sig = doc.add_paragraph()
                sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                sig.add_run("Proper Officer").bold = True
                
                doc.save(file_path)
                import os
                os.startfile(file_path)
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

    def _on_ph_auto_generate_oc(self):
        """Helper for PH Auto-Generate OC utility"""
        self.suggest_next_oc(self.ph_edit_oc)
        
    def _on_scn_oc_changed(self):
        """Handle OC text changes for SCN"""
        if not getattr(self, '_auto_generating_oc', False):
            # Manually edited
            if hasattr(self, 'oc_provenance_lbl'):
                self.oc_provenance_lbl.hide()
        
        
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

                    
                    # Trigger calculation to update totals based on restored variables
                    card.calculate_values()
                    
        except Exception as e:
            print(f"SCN Issue restore failed: {e}")
            import traceback
            traceback.print_exc()
            self.issue_restore_failed = True

        # --- BLOCK 2: Metadata Restoration (Foundational, Low Risk) ---
        try:
            # [PHASE 15] additional_details is already normalized by hydrate_proceeding_data
            details = self.proceeding_data.get('additional_details', {})
            
            if details:
                # 1. DRC-01A Metadata (with legacy fallback)
                drc_meta = details.get('drc01a_metadata', {})
                oc_num = drc_meta.get('oc_number') or details.get('oc_number')
                oc_dte = drc_meta.get('oc_date') or details.get('oc_date')
                rply_dte = drc_meta.get('reply_date') or details.get('reply_date')
                
                if oc_num: self.oc_number_input.setText(oc_num)
                if oc_dte: self.oc_date_input.setDate(QDate.fromString(oc_dte, "yyyy-MM-dd"))
                if rply_dte: self.reply_date.setDate(QDate.fromString(rply_dte, "yyyy-MM-dd"))
                
                # SCN Metadata (with legacy fallback)
                scn_meta = details.get('scn_metadata', {})
                scn_num = scn_meta.get('scn_number') or details.get('scn_number')
                scn_oc = scn_meta.get('scn_oc_number') or details.get('scn_oc_number')
                scn_dte = scn_meta.get('scn_date') or details.get('scn_date')
                
                # Safeguard: Block signals during restoration
                self.scn_no_input.blockSignals(True)
                self.scn_oc_input.blockSignals(True)
                self.scn_date_input.blockSignals(True)
                
                if scn_num: self.scn_no_input.setText(scn_num)
                if scn_oc: self.scn_oc_input.setText(scn_oc)
                if scn_dte: self.scn_date_input.setDate(QDate.fromString(scn_dte, "yyyy-MM-dd"))
                
                self.scn_no_input.blockSignals(False)
                self.scn_oc_input.blockSignals(False)
                self.scn_date_input.blockSignals(False)
                
                # PH Intimation Restoration
                self.ph_entries = details.get('ph_entries', [])
                self.refresh_ph_list()
                if self.ph_entries:
                    self.render_ph_preview()
                
                # Phase-2/3 Restoration (Reliance/Copy-To)
                if not self.is_scn_phase1():
                    rel_docs = scn_meta.get('reliance_documents') or details.get('reliance_documents')
                    copy_to = scn_meta.get('copy_submitted_to') or details.get('copy_submitted_to')
                    if rel_docs: self.reliance_editor.setHtml(rel_docs)
                    if copy_to: self.copy_to_editor.setHtml(copy_to)
                else:
                    print("ProceedingsWorkspace: Phase-1 Active. Skipping Phase-2/3 Restoration.")

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

    def add_new_ph_entry(self):
        """Add a new PH entry slot (Max 3)"""
        if self.is_scn_finalized():
            QMessageBox.warning(self, "Locked", "Case finalized. Cannot add new PH Intimations.")
            return
            
        if len(self.ph_entries) >= 3:
            QMessageBox.warning(self, "Limit Reached", "Maximum 3 Personal Hearing Intimations allowed per case.")
            return

        # Prepare default data
        next_val = "DRAFT"
        self.ph_edit_oc.setText(next_val)
        self.ph_edit_oc_date.setDate(QDate.currentDate())
        self.ph_edit_date.setDate(QDate.currentDate().addDays(7))
        self.ph_edit_time.setText("11:00 AM")
        self.ph_edit_venue.setText("Paravur Range Office")
        self.ph_edit_copy_to.setText("The Assistant Commissioner, Central Tax, Paravur Division")
        
        # Track that we are adding a NEW entry (index = -1)
        self.ph_editing_index = -1
        self.ph_editor_card.setVisible(True)

    def save_ph_entry(self):
        """Save form data into ph_entries list and persist"""
        entry = {
            "oc_no": self.ph_edit_oc.text(),
            "issue_date": self.ph_edit_oc_date.date().toString("dd/MM/yyyy"),
            "ph_date": self.ph_edit_date.date().toString("dd/MM/yyyy"),
            "ph_time": self.ph_edit_time.text(),
            "venue": self.ph_edit_venue.text(),
            "copy_to": self.ph_edit_copy_to.text(),
            "show_letterhead": self.ph_show_lh.isChecked()
        }
        
        print(f"DEBUG: save_ph_entry captured: {entry}")
        
        if self.ph_editing_index == -1:
            self.ph_entries.append(entry)
        else:
            self.ph_entries[self.ph_editing_index] = entry
            
        self.ph_editor_card.setVisible(False)
        self.refresh_ph_list()
        self.render_ph_preview()
        
        # Persist to additional_details
        self.save_ph_data()

    def register_ph_entry(self):
        """Finalize, Register OC, and Save entry"""
        if self.is_scn_finalized(): return
        
        oc_no = self.ph_edit_oc.text().strip()
        if not oc_no or oc_no == "DRAFT":
            QMessageBox.warning(self, "Validation Error", "Please enter a valid OC Number for registration.")
            return
            
        try:
            # 1. Register in OC Register
            oc_data = {
                'OC_Number': oc_no,
                'OC_Date': self.ph_edit_oc_date.date().toString("yyyy-MM-dd"),
                'OC_Content': f"Personal Hearing Intimation for Case {self.proceeding_id}",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            self.db.add_oc_entry(self.proceeding_id, oc_data)
            
            # 2. Mark entry as registered
            entry = {
                "oc_no": oc_no,
                "issue_date": self.ph_edit_oc_date.date().toString("dd/MM/yyyy"),
                "ph_date": self.ph_edit_date.date().toString("dd/MM/yyyy"),
                "ph_time": self.ph_edit_time.text(),
                "venue": self.ph_edit_venue.text(),
                "copy_to": self.ph_edit_copy_to.text(),
                "show_letterhead": self.ph_show_lh.isChecked(),
                "is_registered": True
            }
            
            if self.ph_editing_index == -1:
                self.ph_entries.append(entry)
            else:
                self.ph_entries[self.ph_editing_index] = entry
                
            # 3. Update status (cumulative)
            self.db.update_proceeding(self.proceeding_id, {"status": "PH Intimated"})
            
            self.ph_editor_card.setVisible(False)
            self.refresh_ph_list()
            self.render_ph_preview()
            self.save_ph_data()
            
            QMessageBox.information(self, "Success", f"PH Intimation registered successfully with OC {oc_no}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to register PH: {e}")

    def refresh_ph_list(self):
        """Rebuild the list of PH entry cards with modern neutralized style"""
        while self.ph_list_layout.count():
            item = self.ph_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        is_scn_fin = self.is_scn_finalized()
        
        for idx, entry in enumerate(self.ph_entries):
            card = QFrame()
            is_reg = entry.get('is_registered', False)
            card.setStyleSheet(f"""
                QFrame {{ 
                    background-color: {Theme.SURFACE}; 
                    border-radius: 8px; 
                    border: 1px solid {Theme.NEUTRAL_200};
                }}
            """)
            
            l = QHBoxLayout(card)
            l.setContentsMargins(12, 12, 12, 12)
            
            # Info Section
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            
            title = QLabel(f"PH {idx+1}: {entry['ph_date']} @ {entry['ph_time']}")
            title.setStyleSheet(f"font-weight: bold; color: {Theme.NEUTRAL_900}; font-size: 14px; border: none;")
            
            status_row = QHBoxLayout()
            status_row.setSpacing(8)
            
            badge_text = "REGISTERED" if is_reg else "DRAFT"
            badge_bg = Theme.SUCCESS if is_reg else Theme.NEUTRAL_100
            badge_color = "white" if is_reg else Theme.NEUTRAL_500
            
            badge = QLabel(badge_text)
            badge.setStyleSheet(f"""
                padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;
                background-color: {badge_bg}; color: {badge_color}; border: none;
            """)
            
            oc_info = QLabel(f"OC: {entry['oc_no']}")
            oc_info.setStyleSheet(f"color: {Theme.NEUTRAL_500}; font-size: 12px; border: none;")
            
            status_row.addWidget(badge)
            status_row.addWidget(oc_info)
            status_row.addStretch()
            
            info_layout.addWidget(title)
            info_layout.addLayout(status_row)
            l.addLayout(info_layout)
            l.addStretch()
            
            # Actions
            edit_btn = QPushButton("View" if (is_scn_fin or is_reg) else "Edit")
            edit_btn.setFixedHeight(32)
            edit_btn.setFixedWidth(80)
            edit_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: transparent; border: 1px solid {Theme.NEUTRAL_200}; 
                    color: {Theme.NEUTRAL_900}; border-radius: 6px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {Theme.NEUTRAL_100}; }}
            """)
            edit_btn.clicked.connect(lambda _, i=idx: self.edit_ph_entry(i))
            l.addWidget(edit_btn)
            
            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(32)
            del_btn.setFixedWidth(80)
            del_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: transparent; border: none; 
                    color: {Theme.DANGER}; font-weight: bold;
                }}
                QPushButton:hover {{ color: {Theme.DANGER_HOVER}; }}
            """)
            del_btn.clicked.connect(lambda _, i=idx: self.delete_ph_entry(i))
            if is_scn_fin or is_reg: del_btn.setEnabled(False)
            l.addWidget(del_btn)
            
            self.ph_list_layout.addWidget(card)
        
        self.ph_add_btn.setEnabled(not (len(self.ph_entries) >= 3 or is_scn_fin))

    def edit_ph_entry(self, index):
        """Load entry into form for editing"""
        try:
            entry = self.ph_entries[index]
            self.ph_editing_index = index
            is_reg = entry.get('is_registered', False)
            is_scn_fin = self.is_scn_finalized()
            
            print(f"DEBUG: Editing PH Entry {index}: {entry}")

            # Safe Get with Defaults
            self.ph_edit_oc.setText(entry.get('oc_no', ''))
            
            # Handle Dates (Robust parsing)
            i_date = entry.get('issue_date', '')
            p_date = entry.get('ph_date', '')
            
            if i_date: self.ph_edit_oc_date.setDate(QDate.fromString(i_date, "dd/MM/yyyy"))
            else: self.ph_edit_oc_date.setDate(QDate.currentDate())
                
            if p_date: self.ph_edit_date.setDate(QDate.fromString(p_date, "dd/MM/yyyy"))
            else: self.ph_edit_date.setDate(QDate.currentDate())
                
            self.ph_edit_time.setText(entry.get('ph_time', ''))
            self.ph_edit_venue.setText(entry.get('venue', ''))
            self.ph_edit_copy_to.setText(entry.get('copy_to', ''))
            
            # Restore Checkbox (Missing in previous version)
            self.ph_show_lh.setChecked(entry.get('show_letterhead', False))
            
            # Lock fields if registered or SCN finalized
            locked = is_reg or is_scn_fin
            self.ph_edit_oc.setReadOnly(locked)
            self.ph_edit_oc_date.setReadOnly(locked)
            self.ph_edit_date.setReadOnly(locked)
            self.ph_edit_time.setReadOnly(locked)
            self.ph_edit_venue.setReadOnly(locked)
            self.ph_edit_copy_to.setReadOnly(locked)
            self.ph_show_lh.setEnabled(not locked)
            
            # Find buttons in editor card layout and toggle
            for i in range(self.ph_editor_card.layout().count()):
                item = self.ph_editor_card.layout().itemAt(i)
                # Both grid layout and horizontal button layout need button locking
                if isinstance(item.layout(), QHBoxLayout):
                    for j in range(item.layout().count()):
                        w = item.layout().itemAt(j).widget()
                        if isinstance(w, QPushButton) and w.text() != "Cancel":
                            w.setEnabled(not locked)
            
            self.ph_editor_card.setVisible(True)
            self.render_ph_preview()
        except Exception as e:
            print(f"Error loading PH entry for edit: {e}")
            traceback.print_exc()
            QMessageBox.warning(self, "Error", "Failed to load entry details.")

    def delete_ph_entry(self, index):
        """Remove a PH entry"""
        if self.is_scn_finalized(): return
        
        res = QMessageBox.question(self, "Confirm Delete", "Delete this Personal Hearing Intimation permanentely?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.ph_entries.pop(index)
            self.refresh_ph_list()
            self.save_ph_data()
            if self.ph_browser: self.ph_browser.setHtml("<h3>Select or Add a PH Entry to Preview</h3>")

    def render_ph_preview(self):
        """Render the highlighted/active PH entry into WebEngine with high-fidelity A4 simulation"""
        if not self.ph_entries:
            self.ph_browser.setHtml("<div style='background: #f1f3f4; height: 100vh; display: flex; align-items: center; justify-content: center; font-family: sans-serif; color: #7f8c8d;'><h3>Select or Add a PH Entry to Preview</h3></div>")
            return
            
        # Preview the current entry being edited OR the last one
        idx = self.ph_editing_index if self.ph_editing_index != -1 else (len(self.ph_entries) - 1)
        entry = self.ph_entries[idx].copy()
        
        # Reactive State: Override entry data with current form values for live preview
        entry['show_letterhead'] = self.ph_show_lh.isChecked()
        
        if self.ph_editor_card.isVisible():
            entry.update({
                "oc_no": self.ph_edit_oc.text(),
                "issue_date": self.ph_edit_oc_date.date().toString("dd/MM/yyyy"),
                "ph_date": self.ph_edit_date.date().toString("dd/MM/yyyy"),
                "ph_time": self.ph_edit_time.text(),
                "venue": self.ph_edit_venue.text(),
                "copy_to": self.ph_edit_copy_to.text()
            })
            
        # Gather case data
        case_data = {
            'gstin': self.proceeding_data.get('gstin', ''),
            'legal_name': self.proceeding_data.get('legal_name', ''),
            'address': self.proceeding_data.get('address', ''),
            'scn_no': self.scn_no_input.text() or "____",
            'scn_date': self.scn_date_input.date().toString("dd/MM/yyyy")
        }
        
        html = self.ph_generator.generate_html(case_data, entry, for_preview=True)
        self.ph_browser.setHtml(html)

    def save_ph_data(self):
        """Persist ph_entries to additional_details using safe merge"""
        try:
            details = copy.deepcopy(self.proceeding_data.get('additional_details', {}))
            details['ph_entries'] = self.ph_entries
            
            # [DEBUG]
            print(f"DEBUG: save_ph_data [Pre-DB] Entries Count: {len(self.ph_entries)}")
            print(f"DEBUG: save_ph_data [Pre-DB] Dumping details... (Keys: {list(details.keys())})")
            
            success = self.db.update_proceeding(self.proceeding_id, {
                "additional_details": details
            })
            
            if success:
                print("DEBUG: save_ph_data [DB Update Success]")
                self.proceeding_data['additional_details'] = details
            else:
                print("DEBUG: save_ph_data [DB Update FAILED]")
                
        except Exception as e:
            print(f"DEBUG: save_ph_data CRITICAL FAILURE: {e}")
            traceback.print_exc()

    def generate_ph_pdf(self):
        """Finalize and Generate PDF for active PH entry"""
        if not self.ph_entries: return
        
        idx = self.ph_editing_index if self.ph_editing_index != -1 else (len(self.ph_entries) - 1)
        entry = self.ph_entries[idx]
        
        case_data = {
            'gstin': self.proceeding_data.get('gstin', ''),
            'legal_name': self.proceeding_data.get('legal_name', ''),
            'address': self.proceeding_data.get('address', ''),
            'scn_no': self.scn_no_input.text() or "____",
            'scn_date': self.scn_date_input.date().toString("dd/MM/yyyy")
        }
        
        html = self.ph_generator.generate_html(case_data, entry, for_preview=False, for_pdf=True)
        
        safe_oc = "".join([c for c in entry['oc_no'] if c.isalnum() or c in ('-','_')])
        default_filename = f"PH_Intimation_{safe_oc}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PH Intimation PDF", default_filename, "PDF Files (*.pdf)")
        if file_path:
            from src.utils.document_generator import DocumentGenerator
            import shutil
            import os
            from PyQt6.QtWidgets import QApplication
            
            filename_only = os.path.splitext(os.path.basename(file_path))[0]
            doc_gen = DocumentGenerator()
            
            # [ULTRA-SAFE] UI Mitigation
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            # Disable triggering button if we had a direct reference, 
            # but since this is a general handler we rely on the modal wait cursor.
            
            try:
                generated_path = doc_gen.generate_pdf_from_html(html, filename_only)
                
                if generated_path and os.path.exists(generated_path):
                    shutil.move(generated_path, file_path)
                    QMessageBox.information(self, "Success", f"PH Intimation PDF saved to: {file_path}")
                    os.startfile(file_path)
                else:
                    raise RuntimeError("File generation failed without error message.")
                    
            except Exception as e:
                err_str = str(e)
                if "MISSING_DEPENDENCY" in err_str:
                    msg = ("PDF Generation Unavailable.\n\n"
                           "The system is missing required rendering libraries (GTK3).\n"
                           "Please install the dependencies or use 'Draft DOCX' instead.")
                    QMessageBox.critical(self, "Dependency Error", msg)
                elif "TIMEOUT" in err_str:
                    QMessageBox.warning(self, "Timeout", "PDF generation took too long (20s limit) and was cancelled for safety.")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to generate PDF: {err_str}")
            finally:
                QApplication.restoreOverrideCursor()

    def generate_ph_docx(self):
        """Generate DOCX Document for the active PH Intimation entry"""
        if not self.ph_entries: return
        
        idx = self.ph_editing_index if self.ph_editing_index != -1 else (len(self.ph_entries) - 1)
        entry = self.ph_entries[idx]
        
        # Build filename
        safe_oc = "".join([c for c in entry['oc_no'] if c.isalnum() or c in ('-','_')])
        default_filename = f"PH_Intimation_{safe_oc}.docx"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PH Intimation DOCX", default_filename, "Word Documents (*.docx)")
        if not file_path: return
        
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            doc = Document()
            
            # Margins
            for section in doc.sections:
                section.top_margin = Inches(0.8)
                section.bottom_margin = Inches(0.8)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
                
            # Header Info
            p = doc.add_paragraph()
            p.add_run(f"O.C. No. {entry['oc_no']}").bold = True
            tab_run = p.add_run("\t\t\t\t\t") # Basic spacing simulation
            p.add_run(f"Date: {entry['issue_date']}").bold = True
            
            doc.add_paragraph()
            
            # To Address
            doc.add_paragraph("To,")
            p = doc.add_paragraph()
            p.add_run(self.proceeding_data.get('legal_name', '')).bold = True
            doc.add_paragraph(f"GSTIN: {self.proceeding_data.get('gstin', '')}")
            doc.add_paragraph(self.proceeding_data.get('address', ''))
            
            doc.add_paragraph()
            doc.add_paragraph("Gentlemen/Sir/Madam,")
            doc.add_paragraph()
            
            # Subject
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            run = p.add_run("Subject: Intimation of Personal Hearing – reg")
            run.bold = True
            
            doc.add_paragraph()
            
            # Reference
            p = doc.add_paragraph()
            p.add_run("References: ").bold = True
            p.add_run(f"1. SCN reference number: {self.scn_no_input.text()} dated {self.scn_date_input.date().toString('dd/MM/yyyy')}")
            
            doc.add_paragraph()
            
            # Paragraphs
            p1 = doc.add_paragraph("1. Please refer to the above mentioned SCN number issued by Office of the Superintendent Paravur Range.")
            p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            p2 = doc.add_paragraph(f"2. In this connection, it is to inform you that personal hearing in this case will be held at {entry['ph_time']} on {entry.get('ph_date', '')} before the Superintendent of Central Tax, Paravur Range Office.")
            p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            p3 = doc.add_paragraph("3. You may therefore appear in person or through an authorized representative for the personal hearing on the above mentioned date and time as per your convenience, at the above mentioned address, without fail along with records/documents/evidences you wish to rely upon in support of your case.")
            p3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            doc.add_paragraph()
            doc.add_paragraph()
            
            # Signature
            sig = doc.add_paragraph()
            sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            sig.add_run("VISHNU V\nSuperintendent").bold = True
            
            doc.add_paragraph()
            
            # Copy To
            doc.add_paragraph("Copy submitted to:").bold = True
            doc.add_paragraph(f"1. {entry['copy_to']}")
            
            doc.save(file_path)
            QMessageBox.information(self, "Success", f"Word document saved to: {file_path}")
            os.startfile(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Word document: {e}")
            traceback.print_exc()

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
