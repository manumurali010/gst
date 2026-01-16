from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton, 
                             QPushButton, QButtonGroup, QHBoxLayout, QFrame, QWidget)
from PyQt6.QtCore import Qt

class HeaderSelectionDialog(QDialog):
    """
    Modal dialog to resolve GSTR-2A header ambiguity.
    Forces user to select one of the detected headers or Cancel (Fallback).
    """
    def __init__(self, sop_id, canonical_key, options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GSTR-2A Header Ambiguity Resolution")
        self.setFixedWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.selected_header = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Issue Map
        self.issue_map = {
            3: "ISD Credit Discrepancy (Point 3)",
            5: "TDS/TCS Credit Mismatch (Point 5)",
            7: "ITC from Cancelled Suppliers (Point 7)",
            8: "ITC from Non-Filing Suppliers (Point 8)",
            10: "Import ITC Discrepancy (Point 10)"
        }
        
        # Detailed Instruction Map (SOP-Specific Intent)
        self.instruction_map = {
            3: (
                "<b>SOP-3:</b> This check identifies discrepancies in ISD Credit.<br>"
                "Please select the column representing the <b>eligible Input Tax</b> or <b>Distributed Tax</b> amount.<br>"
                "The selected value will be used to compute the total available credit."
            ),

            5: ("<b>SOP-5:</b> This check identifies under-reporting of <b>Taxable Turnover</b> (TDS/TCS).<br>"
                "Please select the <b>Base Value</b> column (e.g., 'Taxable Value', 'Net Amount Liable').<br>"
                "❌ Do not select tax component columns like IGST/CGST/Tax Deducted."),
            7: (
                "<b>SOP-7:</b> This check identifies ITC availed from suppliers whose registration was cancelled.<br>"
                "Please select the <b>Tax Amount (IGST/CGST/SGST)</b> column.<br>"
                "This value quantifies the ineligible ITC claimed."
            ),
            8: (
                "<b>SOP-8:</b> This check identifies ITC from suppliers who have NOT filed their GSTR-3B returns.<br>"
                "Select the IGST / CGST / SGST tax amount column used to compute inadmissible ITC from non-filing suppliers.<br>"
                "Do NOT select taxable value, GSTIN, filing status, or period columns."
            ),
            10: (
                "<b>SOP-10:</b> This check identifies discrepancies in Import ITC (IMPG).<br>"
                "Please select the <b>IGST Amount</b> or <b>Integrated Tax</b> column.<br>"
                "This is essential to compare the claimed credit against the BOE records."
            )
        }
        
        # Sanitize SOP ID
        try:
            val_str = str(sop_id).lower().replace("sop_", "").replace("sop", "").strip()
            sop_int = int(val_str)
        except:
            sop_int = 0
            
        friendly_name = self.issue_map.get(sop_int, f"SOP Point {sop_id}")
        specific_instr = self.instruction_map.get(sop_int, "Please select the relevant tax amount column for this analysis.")
        
        # Header Info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #fff7ed; border: 1px solid #ffedd5; border-radius: 6px; padding: 12px;")
        info_layout = QVBoxLayout(info_frame)
        
        lbl_title = QLabel(f"Clarification Needed: {friendly_name}")
        lbl_title.setStyleSheet("color: #c2410c; font-weight: bold; font-size: 15px;")
        info_layout.addWidget(lbl_title)
        
        instruction_text = (
            f"<div style='color: #431407; margin-bottom: 8px; font-size: 13px; line-height: 1.4;'>"
            f"{specific_instr}"
            f"</div>"
            f"<div style='color: #7c2d12; font-size: 11px; margin-top: 5px; font-style: italic;'>"
            f"⚠️ Caution: Selecting a non-tax column (e.g. GSTIN, Date, Status) will result in incorrect liability computation."
            f"</div>"
        )
        msg = QLabel(instruction_text)
        msg.setWordWrap(True)
        info_layout.addWidget(msg)
        
        layout.addWidget(info_frame)
        
        # Split Options
        recommended = []
        others = []
        
        self.options = options
        self.btn_map = {} 
        
        for idx, option in enumerate(options):
            if isinstance(option, dict) and option.get('category') == 'recommended':
                recommended.append((idx, option))
            else:
                others.append((idx, option))
                
        self.btn_group = QButtonGroup(self)
        
        # Scroll Area for Options if list is long? 
        # For now, just a VBox, but with spacing.
        self.radio_layout = QVBoxLayout()
        self.radio_layout.setSpacing(8)
        
        btn_layout_idx = 0
        
        # Render Recommended (CONDITIONAL)
        if recommended:
            lbl_rec = QLabel("✅ Recommended (Likely Match)")
            lbl_rec.setStyleSheet("color: #15803d; font-weight: bold; font-size: 12px; margin-top: 10px; border-bottom: 1px solid #bbf7d0; padding-bottom: 4px;")
            self.radio_layout.addWidget(lbl_rec)
            
            for g_idx, option in recommended:
                text = option.get('label') if isinstance(option, dict) else str(option)
                
                # Row Widget
                row = QWidget()
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(0, 0, 0, 0)
                
                rb = QRadioButton() # No text on radio
                rb.setStyleSheet("QRadioButton { background: #f0fdf4; }") 
                
                lbl = QLabel(text)
                lbl.setWordWrap(True)
                lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #14532d; padding: 4px;")
                
                r_layout.addWidget(rb, 0, Qt.AlignmentFlag.AlignTop)
                r_layout.addWidget(lbl, 1)
                
                # Container Style to mimic previous look
                row.setStyleSheet("""
                    QWidget { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; }
                    QWidget:hover { background: #dcfce7; }
                """)
                
                self.btn_group.addButton(rb, btn_layout_idx)
                self.btn_map[btn_layout_idx] = g_idx
                self.radio_layout.addWidget(row)
                btn_layout_idx += 1
        else:
            # NO RECOMMENDED FOUND
            lbl_warn = QLabel(
                "No IGST / CGST / SGST column could be identified in this file.\n"
                "If the file does not contain tax amounts, please cancel. The system will mark this issue as ‘Data Not Available’."
            )
            lbl_warn.setStyleSheet("color: #b45309; font-weight: bold; font-size: 12px; margin-top: 10px; padding: 8px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 4px;")
            lbl_warn.setWordWrap(True)
            self.radio_layout.addWidget(lbl_warn)

        # Render Others
        if others:
            header_text = "Other Columns (Review Carefully)"
            if not recommended:
                header_text = "Columns detected in file (None appear to contain tax amounts)"
                
            lbl_other = QLabel(header_text)
            lbl_other.setStyleSheet("color: #64748b; font-weight: bold; font-size: 11px; margin-top: 15px; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;")
            self.radio_layout.addWidget(lbl_other)
            
            for g_idx, option in others:
                text = option.get('label') if isinstance(option, dict) else str(option)
                
                # Row Widget
                row = QWidget()
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(0, 0, 0, 0)
                
                rb = QRadioButton()
                
                lbl = QLabel(text)
                lbl.setWordWrap(True)
                lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lbl.setStyleSheet("font-size: 13px; color: #475569; padding: 2px;")
                
                r_layout.addWidget(rb, 0, Qt.AlignmentFlag.AlignTop)
                r_layout.addWidget(lbl, 1)
                
                row.setStyleSheet("""
                   QWidget { border: 1px solid #f1f5f9; border-radius: 4px; }
                   QWidget:hover { background: #f8fafc; }
                """)

                self.btn_group.addButton(rb, btn_layout_idx)
                self.btn_map[btn_layout_idx] = g_idx
                self.radio_layout.addWidget(row)
                btn_layout_idx += 1
                
        layout.addLayout(self.radio_layout)
        
        layout.addStretch()
        
        # Footer Actions
        btn_layout = QHBoxLayout()
        
        cancel_text = QLabel("If Cancelled: Analysis marked as 'Data Not Available'.")
        cancel_text.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")
        btn_layout.addWidget(cancel_text)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel Analysis")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton { border: 1px solid #d1d5db; background: white; padding: 6px 12px; border-radius: 4px; color: #ef4444; }
            QPushButton:hover { background: #fef2f2; border-color: #fca5a5; }
        """)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Confirm Selection")
        ok_btn.clicked.connect(self.accept_selection)
        ok_btn.setEnabled(False) 
        ok_btn.setStyleSheet("""
            QPushButton[disabled="false"] { background: #2563eb; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-weight: 600; }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #94a3b8; }
        """)
        btn_layout.addWidget(ok_btn)
        
        self.ok_btn = ok_btn
        self.btn_group.buttonClicked.connect(self.on_selection_change)
        
        layout.addLayout(btn_layout)

    def on_selection_change(self):
        self.ok_btn.setEnabled(True)
        
    def accept_selection(self):
        local_idx = self.btn_group.checkedId()
        if local_idx in self.btn_map:
            global_idx = self.btn_map[local_idx]
            option = self.options[global_idx]
            if isinstance(option, dict):
                self.selected_header = option.get('value')
            else:
                self.selected_header = option
            self.accept()


