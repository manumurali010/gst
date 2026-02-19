from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QDateEdit, 
    QCheckBox, QLabel, QGroupBox, QTextEdit, QPushButton, 
    QHBoxLayout, QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from datetime import datetime

class GroundsConfigurator(QWidget):
    """
    Abstract Interface for SCN Grounds Configuration Widgets.
    Must be implemented by all origin-specific forms.
    """
    def get_data(self) -> dict:
        """Return the structured configuration data."""
        raise NotImplementedError
        
    def set_data(self, data: dict):
        """Populate the form with existing data."""
        raise NotImplementedError
        
    def validate(self) -> list:
        """
        Validate the form data.
        Returns a list of error messages (empty if valid).
        """
        raise NotImplementedError

class ScrutinyGroundsForm(GroundsConfigurator):
    """
    Configuration form for Scrutiny-origin SCNs (Section 61).
    Handles ASMT-10 reference, Docs Verified, and Reply details.
    """
    regenerationRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_intro_modified_by_user = False
        self._is_programmatic_update = False
        self._setup_ui()
        
        # Internal Connection for Auto-Regeneration
        self.regenerationRequested.connect(self.auto_regenerate)
        
        # Validation Listeners
        self.check_reply_received.toggled.connect(self._run_dynamic_validation)
        self.input_reply_date.dateChanged.connect(self._run_dynamic_validation)
        self.input_asmt_date.dateChanged.connect(self._run_dynamic_validation)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0) # We'll use manual spacing for visual rhythm

        # Style Tokens
        header_style = "font-size: 11pt; font-weight: bold; color: #2c3e50;"
        subtitle_style = "font-size: 8pt; font-style: italic; color: #7f8c8d;"
        label_style = "color: #5f6368; font-weight: 500;"

        # --- 1. Automated Configuration Section ---
        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(10)
        config_layout.addSpacing(24) # Spacing from Notice Identification
        
        # Section 2 – Scrutiny Conducted
        sec2_header = QLabel("Scrutiny Conducted")
        sec2_header.setStyleSheet(header_style)
        config_layout.addWidget(sec2_header)
        
        sec2_subtitle = QLabel("Details of return scrutiny under Section 61")
        sec2_subtitle.setStyleSheet(subtitle_style)
        sec2_subtitle.setContentsMargins(0, -5, 0, 5)
        config_layout.addWidget(sec2_subtitle)

        # Financial Year
        fy_layout = QHBoxLayout()
        lbl_fy_key = QLabel("Financial Year:")
        lbl_fy_key.setStyleSheet(label_style)
        self.lbl_fy_val = QLabel("-")
        self.lbl_fy_val.setStyleSheet("font-weight: bold; color: #2c3e50;")
        fy_layout.addWidget(lbl_fy_key)
        fy_layout.addWidget(self.lbl_fy_val)
        fy_layout.addStretch()
        config_layout.addLayout(fy_layout)
        
        # Documents Verified
        self.input_docs = QLineEdit()
        self.input_docs.setPlaceholderText("e.g. GSTR-1, GSTR-3B, GSTR-2A")
        self.input_docs.setToolTip("Auto-filled from case uploads. Edit manually if required.")
        self.input_docs.textChanged.connect(self._on_field_changed)
        
        lbl_docs = QLabel("Documents Verified:")
        lbl_docs.setStyleSheet(label_style)
        config_layout.addWidget(lbl_docs)
        config_layout.addWidget(self.input_docs)
        
        # Section 3 – Prior Communication – ASMT-10
        config_layout.addSpacing(24)
        sec3_header = QLabel("Prior Communication – ASMT-10")
        sec3_header.setStyleSheet(header_style)
        config_layout.addWidget(sec3_header)
        
        self.grp_asmt10 = QWidget() # Changed from QGroupBox for borderless look
        asmt_layout = QFormLayout(self.grp_asmt10)
        asmt_layout.setContentsMargins(0, 5, 0, 0)
        asmt_layout.setSpacing(10)
        asmt_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.input_asmt_oc = QLineEdit()
        self.input_asmt_oc.setPlaceholderText("OC No.")
        self.input_asmt_oc.setReadOnly(True) 
        self.input_asmt_oc.setStyleSheet("background-color: #f8f9fa; color: #495057; border: 1px solid #ced4da;")
        
        self.input_asmt_date = QDateEdit()
        self.input_asmt_date.setCalendarPopup(True)
        self.input_asmt_date.setReadOnly(True)
        self.input_asmt_date.setStyleSheet("background-color: #f8f9fa; color: #495057; border: 1px solid #ced4da;")
        self.input_asmt_date.setDate(QDate.currentDate())
        
        self.input_officer_desg = QLineEdit()
        self.input_officer_desg.setPlaceholderText("e.g. State Tax Officer")
        self.input_officer_desg.textChanged.connect(self._on_field_changed)
        
        self.input_office_addr = QLineEdit()
        self.input_office_addr.setPlaceholderText("e.g. Circle I, Kochi")
        self.input_office_addr.textChanged.connect(self._on_field_changed)
        
        def _add_form_row(layout, label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(label_style)
            layout.addRow(lbl, widget)

        _add_form_row(asmt_layout, "OC No:", self.input_asmt_oc)
        _add_form_row(asmt_layout, "Date:", self.input_asmt_date)
        _add_form_row(asmt_layout, "Designation:", self.input_officer_desg)
        _add_form_row(asmt_layout, "Address:", self.input_office_addr)
        
        config_layout.addWidget(self.grp_asmt10)
        
        # Section 4 – Taxpayer Response
        config_layout.addSpacing(24)
        sec4_header = QLabel("Taxpayer Response")
        sec4_header.setStyleSheet(header_style)
        config_layout.addWidget(sec4_header)
        
        self.grp_reply = QWidget() # Changed from QGroupBox
        reply_layout = QFormLayout(self.grp_reply)
        reply_layout.setContentsMargins(0, 5, 0, 0)
        reply_layout.setSpacing(10)
        
        self.check_reply_received = QCheckBox("Reply received from taxpayer")
        self.check_reply_received.setStyleSheet(label_style)
        self.check_reply_received.toggled.connect(self._on_field_changed)
        self.check_reply_received.toggled.connect(lambda checked: self.input_reply_date.setEnabled(checked))
        
        self.input_reply_date = QDateEdit()
        self.input_reply_date.setCalendarPopup(True)
        self.input_reply_date.setDate(QDate.currentDate())
        self.input_reply_date.setEnabled(False)
        self.input_reply_date.dateChanged.connect(self._on_field_changed)
        
        lbl_reply_date = QLabel("Reply Date:")
        lbl_reply_date.setStyleSheet(label_style)
        
        self.lbl_reply_error = QLabel("")
        self.lbl_reply_error.setStyleSheet("color: #d32f2f; font-size: 10px; font-weight: bold;")
        self.lbl_reply_error.hide()
        
        reply_layout.addRow(self.check_reply_received)
        reply_layout.addRow(lbl_reply_date, self.input_reply_date)
        reply_layout.addRow("", self.lbl_reply_error)
        
        config_layout.addWidget(self.grp_reply)
        layout.addWidget(self.config_container)
        
        # --- 2. Introductory Paragraph Section ---
        # Section 5 – Introductory Paragraph
        layout.addSpacing(32) # Primary drafting area separator
        
        sec5_header_layout = QHBoxLayout()
        sec5_header = QLabel("Introductory Paragraph")
        sec5_header.setStyleSheet(header_style)
        
        self.lbl_status = QLabel("System-generated (auto-updates)")
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 11px;")
        
        self.btn_regenerate = QPushButton("Regenerate")
        self.btn_regenerate.setFixedWidth(100)
        self.btn_regenerate.setStyleSheet("""
            QPushButton { 
                background-color: #f8f9fa; border: 1px solid #dee2e6; 
                border-radius: 4px; color: #495057; font-size: 11px; padding: 2px 8px;
            }
            QPushButton:hover { background-color: #e9ecef; }
        """)
        self.btn_regenerate.clicked.connect(self._on_regenerate_clicked)
        
        sec5_header_layout.addWidget(sec5_header)
        sec5_header_layout.addSpacing(10)
        sec5_header_layout.addWidget(self.lbl_status)
        sec5_header_layout.addStretch()
        sec5_header_layout.addWidget(self.btn_regenerate)
        layout.addLayout(sec5_header_layout)
        
        # Editor (Always visible, Primary Focus)
        self.manual_editor = QTextEdit()
        self.manual_editor.setPlaceholderText("Enter the introductory paragraph here...")
        self.manual_editor.setMinimumHeight(220) # Generous height for drafting focus
        self.manual_editor.setStyleSheet("background-color: white; border: 1px solid #dadce0; border-radius: 4px; padding: 8px;")
        self.manual_editor.textChanged.connect(self._on_text_changed)
        layout.addSpacing(8)
        layout.addWidget(self.manual_editor)
        
        # UI Hint for formatting
        self.lbl_hint = QLabel("Basic formatting supported: Ctrl+B (Bold)")
        self.lbl_hint.setStyleSheet("color: #95a5a6; font-size: 10px; font-style: italic;")
        layout.addWidget(self.lbl_hint)
        
        layout.addStretch()

    def get_data(self) -> dict:
        """
        Return state in strict schema.
        Added: is_intro_modified_by_user
        """
        return {
            "version": 1,
            "type": "scrutiny",
            "is_intro_modified_by_user": self.is_intro_modified_by_user,
            "manual_text": self._extract_clean_html(),
            "data": {
                "financial_year": self.lbl_fy_val.text(),
                "docs_verified": [d.strip() for d in self.input_docs.text().split(",") if d.strip()],
                "asmt10_ref": {
                    "oc_no": self.input_asmt_oc.text().strip(),
                    "date": self.input_asmt_date.date().toString("yyyy-MM-dd"),
                    "officer_designation": self.input_officer_desg.text().strip(),
                    "office_address": self.input_office_addr.text().strip()
                },
                "asmt_10_address": self.input_office_addr.text(),
                "reply_received": self.check_reply_received.isChecked(),
                "reply_date": self.input_reply_date.date().toString("dd/MM/yyyy") if self.check_reply_received.isChecked() else ""
            }
        }

    def set_data(self, payload: dict):
        """
        Populate form from payload.
        Handles loading logic: If modified manually, load stored text.
        """
        if not payload: return
        
        # 1. Load Flag and Text
        self.is_intro_modified_by_user = payload.get("is_intro_modified_by_user", False)
        
        # For legacy compatibility, also check manual_override
        if not self.is_intro_modified_by_user:
            self.is_intro_modified_by_user = payload.get("manual_override", False)

        manual_text = payload.get("manual_text", "")
        
        # 2. Standardized Rendering (Always HTML)
        self._is_programmatic_update = True
        
        # Legacy Detection & Wrap
        if manual_text and not ("<p>" in manual_text.lower() or "<body>" in manual_text.lower() or "<div>" in manual_text.lower()):
            # Treat as legacy plain text
            manual_text = f"<p>{manual_text}</p>"
            
        self.manual_editor.setHtml(manual_text)
        self._is_programmatic_update = False
        
        self._update_status_label()
            
        # 2. Structured Data
        data = payload.get("data", {})
        
        # FY
        if "financial_year" in data:
            self.lbl_fy_val.setText(data["financial_year"])
            
        # Docs
        docs = data.get("docs_verified", [])
        if isinstance(docs, list):
            self.input_docs.setText(", ".join(docs))
        elif isinstance(docs, str):
            self.input_docs.setText(docs)
            
        # ASMT-10
        asmt = data.get("asmt10_ref", {})
        self.input_asmt_oc.setText(asmt.get("oc_no", ""))
        
        if asmt.get("date"):
            self.input_asmt_date.setDate(QDate.fromString(asmt["date"], "yyyy-MM-dd"))
            
        self.input_officer_desg.setText(asmt.get("officer_designation", ""))
        self.input_office_addr.setText(data.get("asmt_10_address", ""))
        
        # Reply
        reply_received = data.get("reply_received", False)
        self.check_reply_received.setChecked(reply_received)
        self.input_reply_date.setEnabled(reply_received)
        
        reply_date_str = data.get("reply_date", "")
        if reply_date_str:
            # Try parsing with the new format first, then fallback to old
            date_obj = QDate.fromString(reply_date_str, "dd/MM/yyyy")
            if not date_obj.isValid():
                date_obj = QDate.fromString(reply_date_str, "yyyy-MM-dd")
            if date_obj.isValid():
                self.input_reply_date.setDate(date_obj)
        self.config_container.setEnabled(True)
        self.config_container.setStyleSheet("")

    def _run_dynamic_validation(self):
        """Perform non-blocking inline validation."""
        self.validate(show_ui=True)

    def validate(self, show_ui=False) -> list:
        """
        Check for missing mandatory fields and legal contradictions.
        - Reply Received => Reply Date mandatory
        - ASMT Date <= Reply Date
        - ASMT Date <= SCN Date (Checked if scn_date provided)
        """
        errors = []
        
        # Reset styles
        self.input_asmt_oc.setStyleSheet("background-color: #f8f9fa;")
        self.input_officer_desg.setStyleSheet("")
        self.input_reply_date.setStyleSheet("")
        self.lbl_reply_error.hide()

        # 1. Mandatory Metadata
        if not self.input_asmt_oc.text().strip():
            errors.append("ASMT-10 OC No. is required.")
            if show_ui: self.input_asmt_oc.setStyleSheet("border: 1px solid #d32f2f; background-color: #fdf2f2;")
            
        if not self.input_officer_desg.text().strip():
            errors.append("Officer Designation is required.")
            if show_ui: self.input_officer_desg.setStyleSheet("border: 1px solid #d32f2f;")

        # 2. Reply Logic
        if self.check_reply_received.isChecked():
            # In GST context, the date cannot be in the future (usually)
            # and MUST be >= ASMT-10 date
            asmt_date = self.input_asmt_date.date()
            reply_date = self.input_reply_date.date()
            
            if reply_date < asmt_date:
                err = "Reply date cannot be earlier than ASMT-10 date."
                errors.append(err)
                if show_ui:
                    self.lbl_reply_error.setText(err)
                    self.lbl_reply_error.show()
                    self.input_reply_date.setStyleSheet("border: 1px solid #d32f2f;")

        return errors

    def _on_field_changed(self):
        """Triggered when any field used for auto-generation changes."""
        self.regenerationRequested.emit()

    def auto_regenerate(self):
        """Perform regeneration only if not manually modified."""
        if self.is_intro_modified_by_user:
            return
        self._on_regenerate_clicked()

    def _on_regenerate_clicked(self):
        """Force regeneration from UI values."""
        from src.utils.scn_generator import generate_intro_narrative
        data = self.get_data()
        # Force flag to False so generator doesn't return existing manual text
        data['is_intro_modified_by_user'] = False 
        new_text = generate_intro_narrative(data)
        self.update_intro_text(new_text, force=True)

    def _on_text_changed(self):
        """Track user modifications."""
        if self._is_programmatic_update:
            return
            
        if not self.is_intro_modified_by_user:
            self.is_intro_modified_by_user = True
            self._update_status_label()

    def update_intro_text(self, text: str, force: bool = False):
        """
        Programmatically update the intro text using HTML.
        """
        if self.is_intro_modified_by_user and not force:
            return
            
        self._is_programmatic_update = True
        self.manual_editor.setHtml(text)
        if force:
            self.is_intro_modified_by_user = False
        self._is_programmatic_update = False
        self._update_status_label()

    def _extract_clean_html(self) -> str:
        """
        Safely extract content between <body> and </body> case-insensitively.
        Handles attributes in <body> tag.
        """
        raw_html = self.manual_editor.toHtml()
        lower_html = raw_html.lower()
        
        # Search for <body...
        body_start_search = lower_html.find("<body")
        if body_start_search == -1:
            return raw_html # Fallback
            
        # Find the closing > of the opening body tag
        body_start_tag_end = lower_html.find(">", body_start_search)
        if body_start_tag_end == -1:
            return raw_html
            
        body_end_search = lower_html.find("</body>")
        if body_end_search == -1:
            body_end_search = len(raw_html)
            
        body_content = raw_html[body_start_tag_end + 1:body_end_search].strip()

        # Ghost Paragraph Safeguard
        # If content is just empty tags like <p></p> or whitespace, return empty
        clean_text = self.manual_editor.toPlainText().strip()
        if not clean_text:
            return ""
            
        return body_content

    def _update_status_label(self):
        if self.is_intro_modified_by_user:
            self.lbl_status.setText("Modified manually")
            self.lbl_status.setStyleSheet("color: #d35400; font-style: italic; font-size: 11px;")
        else:
            self.lbl_status.setText("System-generated (auto-updates)")
            self.lbl_status.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 11px;")


def get_grounds_form(origin_type: str, parent=None) -> GroundsConfigurator:
    """
    Factory to get the correct configuration form based on case origin.
    Currently supports: 'scrutiny'.
    Defaults to ScrutinyGroundsForm for now.
    """
    # Normalize origin
    origin = origin_type.lower() if origin_type else ""
    
    if "scrutiny" in origin:
        return ScrutinyGroundsForm(parent)
    elif "inspection" in origin:
        # Placeholder for Phase 2
        # return InspectionGroundsForm(parent)
        return ScrutinyGroundsForm(parent) 
    else:
        # Default fallback
        return ScrutinyGroundsForm(parent)
