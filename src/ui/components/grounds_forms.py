from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QDateEdit, 
    QCheckBox, QLabel, QGroupBox, QTextEdit, QPushButton, 
    QHBoxLayout, QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manual_override_active = False
        self._setup_ui()
        
        # Internal state for manual text to preserve it across toggles
        self._cached_manual_text = ""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # --- 1. Automated Configuration Section ---
        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # A. Financial Year (Read-Only Context)
        fy_layout = QHBoxLayout()
        self.lbl_fy_key = QLabel("Financial Year:")
        self.lbl_fy_key.setStyleSheet("color: #5f6368; font-weight: 500;")
        self.lbl_fy_val = QLabel("-")
        self.lbl_fy_val.setStyleSheet("font-weight: bold; color: #2c3e50;")
        fy_layout.addWidget(self.lbl_fy_key)
        fy_layout.addWidget(self.lbl_fy_val)
        fy_layout.addStretch()
        config_layout.addLayout(fy_layout)
        
        # B. Documents Verified
        self.input_docs = QLineEdit()
        self.input_docs.setPlaceholderText("e.g. GSTR-1, GSTR-3B, GSTR-2A")
        self.input_docs.setText("GSTR-1, GSTR-3B, GSTR-2A") # Default
        config_layout.addWidget(QLabel("Documents Verified:"))
        config_layout.addWidget(self.input_docs)
        
        # C. ASMT-10 Details Group
        self.grp_asmt10 = QGroupBox("ASMT-10 Details (Previous Communication)")
        asmt_layout = QFormLayout(self.grp_asmt10)
        asmt_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.input_asmt_oc = QLineEdit()
        self.input_asmt_oc.setPlaceholderText("OC No.")
        self.input_asmt_date = QDateEdit()
        self.input_asmt_date.setCalendarPopup(True)
        self.input_asmt_date.setDate(QDate.currentDate())
        
        self.input_officer_desg = QLineEdit()
        self.input_officer_desg.setPlaceholderText("e.g. State Tax Officer")
        self.input_office_addr = QLineEdit() # Using LineEdit for compactness
        self.input_office_addr.setPlaceholderText("e.g. Circle I, Kochi")
        
        asmt_layout.addRow("OC No:", self.input_asmt_oc)
        asmt_layout.addRow("Date:", self.input_asmt_date)
        asmt_layout.addRow("Designation:", self.input_officer_desg)
        asmt_layout.addRow("Address:", self.input_office_addr)
        
        config_layout.addWidget(self.grp_asmt10)
        
        # D. Reply Details Group
        self.grp_reply = QGroupBox("Taxpayer Reply")
        self.grp_reply.setCheckable(True)
        self.grp_reply.setChecked(False) # Default to No Reply
        reply_layout = QFormLayout(self.grp_reply)
        
        self.input_reply_date = QDateEdit()
        self.input_reply_date.setCalendarPopup(True)
        self.input_reply_date.setDate(QDate.currentDate())
        
        reply_layout.addRow("Reply Date:", self.input_reply_date)
        config_layout.addWidget(self.grp_reply)
        
        layout.addWidget(self.config_container)
        
        # --- 2. Manual Override Section ---
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Toggle Header
        toggle_layout = QHBoxLayout()
        self.chk_manual_override = QCheckBox("Manual Override")
        self.chk_manual_override.setStyleSheet("font-weight: bold; color: #d35400;")
        self.chk_manual_override.setToolTip("Enable to manually edit the introductory text. Disables auto-generation.")
        self.chk_manual_override.toggled.connect(self._on_override_toggled)
        
        toggle_layout.addWidget(self.chk_manual_override)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)
        
        # Manual Editor (Hidden by default)
        self.manual_editor = QTextEdit()
        self.manual_editor.setPlaceholderText("Enter the introductory paragraph here...")
        self.manual_editor.setStyleSheet("background-color: #fff3e0; border: 1px solid #e67e22;")
        self.manual_editor.setVisible(False)
        self.manual_editor.textChanged.connect(self._sync_manual_text_cache)
        layout.addWidget(self.manual_editor)
        
        layout.addStretch()

    def get_data(self) -> dict:
        """
        Return state in strict schema:
        {
            "version": 1,
            "type": "scrutiny",
            "manual_override": bool,
            "manual_text": str|None,
            "data": { ... }
        }
        """
        return {
            "version": 1,
            "type": "scrutiny",
            "manual_override": self.chk_manual_override.isChecked(),
            "manual_text": self._cached_manual_text,
            "data": {
                "financial_year": self.lbl_fy_val.text(),
                "docs_verified": [d.strip() for d in self.input_docs.text().split(",") if d.strip()],
                "asmt10_ref": {
                    "oc_no": self.input_asmt_oc.text().strip(),
                    "date": self.input_asmt_date.date().toString("yyyy-MM-dd"),
                    "officer_designation": self.input_officer_desg.text().strip(),
                    "office_address": self.input_office_addr.text().strip()
                },
                "reply_ref": {
                    "received": self.grp_reply.isChecked(),
                    "date": self.input_reply_date.date().toString("yyyy-MM-dd") if self.grp_reply.isChecked() else None
                }
            }
        }

    def set_data(self, payload: dict):
        """
        Populate form from payload.
        Handles version migration and missing keys gracefully.
        """
        if not payload: return
        
        # 1. Top Level Flags
        manual_override = payload.get("manual_override", False)
        self.chk_manual_override.setChecked(manual_override)
        
        # Restore manual text cache
        self._cached_manual_text = payload.get("manual_text", "")
        if self._cached_manual_text:
            self.manual_editor.setPlainText(self._cached_manual_text)
            
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
        self.input_office_addr.setText(asmt.get("office_address", ""))
        
        # Reply
        reply = data.get("reply_ref", {})
        self.grp_reply.setChecked(reply.get("received", False))
        if reply.get("date"):
            self.input_reply_date.setDate(QDate.fromString(reply["date"], "yyyy-MM-dd"))
            
        # Update UI Stae
        self._update_visibility()

    def validate(self) -> list:
        """
        Check for missing mandatory fields if Automated Mode is active.
        """
        if self.chk_manual_override.isChecked():
            # In manual mode, only require that text is not empty? 
            # Or allow empty? Let's say manual mode assumes user knows what they are doing.
            return []
            
        errors = []
        
        # Mandatory: ASMT-10 OC
        if not self.input_asmt_oc.text().strip():
            errors.append("ASMT-10 OC No. is required.")
            
        # Mandatory: Officer Details (Soft validation? No, explicit as per plan)
        if not self.input_officer_desg.text().strip():
             errors.append("Officer Designation is required.")
             
        return errors

    def _on_override_toggled(self, checked):
        """
        Handle transition between Auto and Manual modes.
        """
        if not checked:
            # ON -> OFF: Confirm before discarding (hiding) manual view
            # In a real app, we might ask for confirmation here if needed
            # For now, per spec: "Discard manual changes? ... manual text is ignored (but preserved)"
            pass
            
        self._update_visibility()

    def _update_visibility(self):
        is_manual = self.chk_manual_override.isChecked()
        self.config_container.setEnabled(not is_manual)
        self.manual_editor.setVisible(is_manual)
        
        # Visual cues
        if is_manual:
             self.config_container.setStyleSheet("opacity: 0.5;")
        else:
             self.config_container.setStyleSheet("")


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
