from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QStackedWidget, QMessageBox, QCompleter, QCheckBox, QScrollArea, QFrame,
                             QTextBrowser, QSplitter, QDateEdit, QMenu, QSizePolicy)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QStringListModel, QDate, QParallelAnimationGroup, QPropertyAnimation, QAbstractAnimation
from src.database.db_manager import DatabaseManager
from src.utils.constants import PROCEEDING_TYPES, FORMS_MAP, SECTIONS_FILE, TEMPLATES_FILE, TAX_TYPES
from src.utils.document_generator import DocumentGenerator
from src.utils.config_manager import ConfigManager
import datetime
import pandas as pd
import json
import os
from src.ui.collapsible_box import CollapsibleBox


class AdjudicationWizard(QWidget):
    def __init__(self, home_callback):
        super().__init__()
        self.home_callback = home_callback
        self.db = DatabaseManager()
        self.doc_gen = DocumentGenerator()
        self.config = ConfigManager()  # Add config manager
        self.current_step = 0
        self.case_data = {}
        self.current_case_id = None # Track current active case
        
        # Setup Debounce Timer for Preview (Initialize early)
        from PyQt6.QtCore import QTimer
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300) # 300ms debounce
        self.preview_timer.timeout.connect(self.update_live_preview)
        
        self.load_reference_data() # Load reference data first
        self.load_templates() # Load letterhead and form header templates
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Header
        self.header_label = QLabel("Create New Case File")
        self.header_label.setStyleSheet("""
            QLabel {
                font-size: 12px; 
                font-weight: bold; 
                color: #2c3e50;
                padding: 4px 10px;
                background-color: #ecf0f1;
                border-bottom: 1px solid #bdc3c7;
            }
        """)
        self.header_label.setFixedHeight(25) # Force fixed small height
        self.layout.addWidget(self.header_label)
        
        self.layout.setContentsMargins(0, 0, 0, 0) # Remove all outer margins
        self.layout.setSpacing(0) # Remove spacing between header and content

        # Create splitter for form and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Wizard form
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # Wizard Steps (Stacked)
        self.stack = QStackedWidget()
        left_layout.addWidget(self.stack)

        # Letterhead Checkbox (Initialize early)
        self.show_letterhead_cb = QCheckBox("Show Letterhead in Preview")
        self.show_letterhead_cb.setChecked(True)
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview_update)
        
        # Combined Step 1-4: Google Form Style
        self.step1_4_combined = self.create_combined_step1_4()
        self.stack.addWidget(self.step1_4_combined)

        # Step 5: Facts
        self.step5 = self.create_step5()
        self.stack.addWidget(self.step5)

        # Step 6: Amounts
        self.step6 = self.create_step6()
        self.stack.addWidget(self.step6)

        # Step 7: Preview
        self.step7 = self.create_step7()
        self.stack.addWidget(self.step7)

        # Navigation Buttons
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        self.back_btn.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        nav_layout.addWidget(self.back_btn)
        
        nav_layout.addStretch()
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 10px 30px; font-size: 14px; border-radius: 5px;")
        self.next_btn.clicked.connect(self.go_next)
        nav_layout.addWidget(self.next_btn)

        left_layout.addLayout(nav_layout)
        
        # Right side: Document Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        preview_label = QLabel("Live Document Preview")
        preview_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        right_layout.addWidget(preview_label)
        
        # Add letterhead checkbox to right layout with prominent styling
        self.show_letterhead_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 8px;
                background-color: #ecf0f1;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.show_letterhead_cb.setMinimumHeight(35)
        self.show_letterhead_cb.show()  # Explicitly show the checkbox
        right_layout.addWidget(self.show_letterhead_cb)
        
        # Scroll Area for Image Preview
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("border: 1px solid #dadce0; background-color: #525659;") # Dark background for PDF feel
        
        self.preview_image_label = QLabel()
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setStyleSheet("background-color: transparent;")
        
        self.preview_scroll.setWidget(self.preview_image_label)
        right_layout.addWidget(self.preview_scroll)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # Set initial sizes (50% form, 50% preview)
        splitter.setSizes([500, 500])
        
        self.layout.addWidget(splitter)
        
        # Connect inputs to timer
        self.connect_inputs_to_preview()

    def connect_inputs_to_preview(self):
        """Connect all input fields to the debounce timer"""
        # Text Inputs
        for widget in [self.gstin_input, self.legal_name_input, self.trade_name_input, self.address_input, self.facts_text]:
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.textChanged.connect(self.trigger_preview_update)
                
        # Combos
        for combo in [self.proceeding_combo, self.form_combo, self.fy_combo, self.drc_section_combo]:
            combo.currentIndexChanged.connect(self.trigger_preview_update)
            
        # Letterhead Checkbox
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview_update)
        
        # Add checkbox to layout (assuming there's a place for it, e.g., near the form combo or preview label)
        # Finding a suitable layout... self.preview_container layout seems appropriate if accessible, 
        # or add to the form_layout in setup_ui.
        # Since setup_ui is not easily accessible here without more context, let's try to find where to add it.
        # Looking at previous file content, there is a `right_layout` for preview.
        # Let's add it to the top of the right layout or near the preview label.
        
        # Date
        self.compliance_date.dateChanged.connect(self.trigger_preview_update)

    def trigger_preview_update(self):
        """Restart the debounce timer"""
        self.preview_timer.start()

    def update_live_preview(self):
        """Generate and display the preview image"""
        from src.utils.preview_generator import PreviewGenerator
        
        # Check if form type is selected
        if self.form_combo.currentIndex() <= 0:
            # Show placeholder
            self.preview_image_label.setText("Select a Form Type to view preview")
            self.preview_image_label.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
            return
            
        self.preview_image_label.setStyleSheet("background-color: transparent;")
        
        # 1. Generate HTML based on form type
        form_type = self.form_combo.currentText()
        if "Show Cause Notice" in form_type or "SCN" in form_type:
            html_content = self.generate_scn_html()
        else:
            html_content = self.generate_drc01a_html()
        
        if not html_content or "Error" in html_content:
            return

        # 2. Generate Image
        img_bytes = PreviewGenerator.generate_preview_image(html_content)
        
        if img_bytes:
            pixmap = PreviewGenerator.get_qpixmap_from_bytes(img_bytes)
            
            # Scale to fit width if needed, but keep aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(self.preview_scroll.width() - 30, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(scaled_pixmap)
        else:
            self.preview_image_label.setText("Preview Generation Failed")

    def reset_form(self):
        """Reset all form fields to default state"""
        self.current_case_id = None
        self.current_step = 0
        self.stack.setCurrentIndex(0)
        
        # Clear Text Inputs
        for widget in [self.gstin_input, self.legal_name_input, self.trade_name_input, 
                      self.address_input, self.facts_text, self.oc_number_input, 
                      self.scn_number_input, self.oio_number_input, self.issue_input,
                      self.relied_docs_input, self.copy_to_input]:
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.clear()
                
        # Reset Combos
        self.fy_combo.setCurrentIndex(0)
        self.proceeding_combo.setCurrentIndex(0)
        self.form_combo.setCurrentIndex(0)
        self.drc_section_combo.setCurrentIndex(0)
        self.drc_section_combo.hide()
        
        # Reset Date
        self.compliance_date.setDate(QDate.currentDate().addDays(30))
        
        # Reset Amounts
        self.amount_table.setRowCount(0)
        self.add_amount_row() # Add one empty row
        
        # Reset Preview
        self.preview_image_label.clear()
        self.preview_image_label.setText("Select a Form Type to view preview")
        self.preview_image_label.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")

    def load_letterhead(self):
        # Initial load
        self.trigger_preview_update()

    def load_reference_data(self):
        # Load sections
        try:
            with open(SECTIONS_FILE, 'r') as f:
                self.sections_list = [line.strip() for line in f if line.strip()]
        except:
            self.sections_list = []

        # Load templates
        try:
            with open(TEMPLATES_FILE, 'r') as f:
                self.templates_list = f.read().split('\n\n')
        except:
            self.templates_list = []
            
        # Load GSTINs for auto-complete
        try:
            all_taxpayers = self.db.search_taxpayers("")
            self.gstin_list = [str(t.get('GSTIN', '')) for t in all_taxpayers if t.get('GSTIN')]
        except Exception as e:
            print(f"Error loading GSTINs: {e}")
            self.gstin_list = []
    
    def load_templates(self):
        """Load letterhead and form header templates"""
        # Load PDF letterhead (HTML only) for preview
        letterhead_path = self.config.get_letterhead_path('pdf')
        
        try:
            with open(letterhead_path, 'r', encoding='utf-8') as f:
                self.letterhead_html = f.read()
        except Exception as e:
            print(f"Error loading letterhead: {e}")
            self.letterhead_html = "<html><body><h2>Letterhead template not found</h2></body></html>"
        
        # Load DRC-01A HTML
        drc01a_path = os.path.join('templates', 'drc_01a.html')
        try:
            with open(drc01a_path, 'r', encoding='utf-8') as f:
                self.drc01a_html = f.read()
        except Exception as e:
            print(f"Error loading DRC-01A template: {e}")
            self.drc01a_html = ""
        
        # Load form headers JSON
        form_headers_path = os.path.join('templates', 'form_headers.json')
        try:
            with open(form_headers_path, 'r', encoding='utf-8') as f:
                self.form_headers = json.load(f)
        except Exception as e:
            print(f"Error loading form headers: {e}")
            self.form_headers = {}
    
    def reload_letterhead(self):
        """Reload letterhead and update preview"""
        # Reload PDF letterhead for preview
        letterhead_path = self.config.get_letterhead_path('pdf')
        
        try:
            with open(letterhead_path, 'r', encoding='utf-8') as f:
                self.letterhead_html = f.read()
        except Exception as e:
            print(f"Error loading letterhead: {e}")
            self.letterhead_html = "<html><body><h2>Letterhead template not found</h2></body></html>"
        
        # Update preview
        self.update_preview_header()
    
    def load_letterhead(self):
        """Load and display the letterhead template in preview"""
        self.trigger_preview_update()
    
    def generate_drc01a_html(self):
        """Generate HTML for DRC-01A with current data"""
        if not self.drc01a_html:
            return "<p>Error: DRC-01A template not loaded</p>"
            
        html = self.drc01a_html
        
        # LOGGING: Print all data to debug NoneType error
        print("DEBUG: Starting DRC-01A Generation")
        print(f"DEBUG: Form Type: {self.form_combo.currentText()}")
        print(f"DEBUG: GSTIN: {self.gstin_input.text()}")
        print(f"DEBUG: Legal Name: {self.legal_name_input.text()}")
        print(f"DEBUG: Address: {self.address_input.toPlainText()}")
        print(f"DEBUG: Compliance Date: {self.compliance_date.date().toString('dd/MM/yyyy')}")
        
        # Extract section from proceeding type (e.g., "Section 73" from "Section 73 (Demand)")
        # If DRC-01A specific section is visible, use that
        if not self.drc_section_combo.isHidden():
            proceeding_section = self.drc_section_combo.currentText()
        else:
            # Fallback to proceeding type logic (though for DRC-01A we should rely on the combo)
            proceeding_type = self.proceeding_combo.currentText()
            if "Section 73" in proceeding_type:
                proceeding_section = "Section 73(5)"
            elif "Section 74" in proceeding_type:
                proceeding_section = "Section 74(5)"
            else:
                proceeding_section = "Section 73(5)/Section 74(5)"  # Default if neither
        
        # Basic Details
        html = html.replace("{{SelectedSection}}", proceeding_section) # Replaces both Subject and Body placeholders
        html = html.replace("{{OCNumber}}", "")  # Placeholder for O.C. Number - user can fill manually
        html = html.replace("{{CurrentDate}}", datetime.date.today().strftime("%d/%m/%Y"))
        html = html.replace("{{GSTIN}}", self.gstin_input.text() or "_________________")
        html = html.replace("{{LegalName}}", self.legal_name_input.text() or "_________________")
        html = html.replace("{{Address}}", self.address_input.toPlainText() or "_________________")
        
        # Compliance Date
        compliance_date = self.compliance_date.date().toString("dd/MM/yyyy")
        html = html.replace("{{ComplianceDate}}", compliance_date)
        
        # SCN Section Logic
        if "73" in proceeding_section:
            scn_section = "section 73(1)"
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {compliance_date} , failing which Show Cause Notice will be issued under section 73(1)."
        elif "74" in proceeding_section:
            scn_section = "section 74(1)"
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {compliance_date} , failing which Show Cause Notice will be issued under section 74(1)."
        else:
            scn_section = "section 73(1)/74(1)"
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {compliance_date} , failing which Show Cause Notice will be issued under section 73(1)/74(1)."
            
        html = html.replace("{{SCNSection}}", scn_section)
        
        # Facts / Grounds
        facts = self.facts_text.toPlainText()
        html = html.replace("{{GroundsContent}}", facts if facts else "(Grounds and quantification will appear here...)")
        
        # Advice Text
        html = html.replace("{{AdviceText}}", advice_text)
        
        # Additional Placeholders
        html = html.replace("{{CaseID}}", self.current_case_id or "")
        html = html.replace("{{FinancialYear}}", self.fy_combo.currentText())
        html = html.replace("{{TradeName}}", self.trade_name_input.text() or "")
        html = html.replace("{{FormType}}", self.form_combo.currentText())
        
        # Sections Violated (from checkboxes)
        violated_sections = []
        for cb in self.provision_checks:
            if cb.isChecked():
                violated_sections.append(cb.text())
        sections_text = "<br>".join(violated_sections) if violated_sections else "(No sections selected)"
        html = html.replace("{{SectionsViolated}}", sections_text)
        
        # Inject Letterhead
        if self.letterhead_html and hasattr(self, 'show_letterhead_cb') and self.show_letterhead_cb.isChecked():
            html = html.replace('<div id="letterhead-placeholder"></div>', self.letterhead_html)
        
        # Tax Data
        tax_rows = ""
        total_tax = 0
        total_int = 0
        total_pen = 0
        total_grand = 0
        
        # Get Financial Year parts
        fy_text = self.fy_combo.currentText()
        try:
            start_year = int(fy_text.split("-")[0])
            end_year = int("20" + fy_text.split("-")[1])
        except:
            start_year = datetime.date.today().year
            end_year = start_year + 1

        # Iterate over fixed rows (CGST, SGST, IGST)
        for row in range(self.amount_table.rowCount()):
            item = self.amount_table.item(row, 0)
            if not item:
                continue
            act = item.text()
            
            # Get From/To Months from Combos
            from_widget = self.amount_table.cellWidget(row, 1)
            to_widget = self.amount_table.cellWidget(row, 2)
            
            if not from_widget or not to_widget:
                continue
                
            from_month = from_widget.currentText()
            to_month = to_widget.currentText()
            
            # Determine Year
            # April-December -> Start Year, January-March -> End Year
            first_half = ["April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            from_year = start_year if from_month in first_half else end_year
            to_year = start_year if to_month in first_half else end_year
            
            from_str = f"{from_month}, {from_year}"
            to_str = f"{to_month}, {to_year}"

            try: tax = float(self.amount_table.item(row, 3).text() or 0)
            except: tax = 0.0
            try: interest = float(self.amount_table.item(row, 4).text() or 0)
            except: interest = 0.0
            try: penalty = float(self.amount_table.item(row, 5).text() or 0)
            except: penalty = 0.0
            try: total = float(self.amount_table.item(row, 6).text() or 0)
            except: total = 0.0
            
            print(f"DEBUG: Row {row} - Tax: {tax}, Int: {interest}, Pen: {penalty}, Total: {total}")
            
            total_tax += tax
            total_int += interest
            total_pen += penalty
            total_grand += total
            
            tax_rows += f"""
            <tr>
                <td style="border: 1px solid #000; padding: 4px;">{act}</td>
                <td style="border: 1px solid #000; padding: 4px;">{from_str}</td>
                <td style="border: 1px solid #000; padding: 4px;">{to_str}</td>
                <td style="border: 1px solid #000; padding: 4px;">{tax:,.0f}</td>
                <td style="border: 1px solid #000; padding: 4px;">{interest:,.0f}</td>
                <td style="border: 1px solid #000; padding: 4px;">{penalty:,.0f}</td>
                <td style="border: 1px solid #000; padding: 4px;">{total:,.0f}</td>
            </tr>
            """
            
        # Add Total Row
        tax_rows += f"""
        <tr style="font-weight: bold; background-color: #f9f9f9;">
            <td colspan="3" style="border: 1px solid #000; padding: 4px; text-align: right;">Total</td>
            <td style="border: 1px solid #000; padding: 4px;">{total_tax:,.0f}</td>
            <td style="border: 1px solid #000; padding: 4px;">{total_int:,.0f}</td>
            <td style="border: 1px solid #000; padding: 4px;">{total_pen:,.0f}</td>
            <td style="border: 1px solid #000; padding: 4px;">{total_grand:,.0f}</td>
        </tr>
        """
            
        html = html.replace("{{TaxTableRows}}", tax_rows)
        
        # New Placeholders
        html = html.replace("{{PeriodFrom}}", self.period_from_date.date().toString("dd/MM/yyyy"))
        html = html.replace("{{PeriodTo}}", self.period_to_date.date().toString("dd/MM/yyyy"))
        html = html.replace("{{IssueDescription}}", self.issue_input.text() or "(Issue Description)")
        
        html = html.replace("{{TaxAmount}}", f"{total_tax:,.0f}")
        html = html.replace("{{InterestAmount}}", f"{total_int:,.0f}")
        html = html.replace("{{PenaltyAmount}}", f"{total_pen:,.0f}")
        html = html.replace("{{TotalAmount}}", f"{total_grand:,.0f}")
        
        return html

    def generate_scn_html(self):
        """Generate HTML for SCN with current data"""
        try:
            with open('templates/scn.html', 'r', encoding='utf-8') as f:
                html = f.read()
        except Exception as e:
            print(f"Error loading SCN template: {e}")
            return "<p>Error: SCN template not found</p>"
        
        # Basic Details
        html = html.replace("{{OCNumber}}", "")  # Placeholder for O.C. Number
        html = html.replace("{{CurrentDate}}", datetime.date.today().strftime("%d/%m/%Y"))
        html = html.replace("{{SCNNumber}}", "")  # Placeholder for SCN Number
        
        # Section
        proceeding_section = self.proceeding_combo.currentText()
        if "73" in proceeding_section:
            section = "Section 73"
        elif "74" in proceeding_section:
            section = "Section 74"
        else:
            section = "Section 73/74"
        html = html.replace("{{Section}}", section)
        
        # Taxpayer Details
        html = html.replace("{{GSTIN}}", self.gstin_input.text() or "_________________")
        html = html.replace("{{LegalName}}", self.legal_name_input.text() or "_________________")
        html = html.replace("{{TradeName}}", self.trade_name_input.text() or "_________________")
        html = html.replace("{{Address}}", self.address_input.toPlainText() or "_________________")
        html = html.replace("{{Constitution}}", self.constitution_input.text() or "registered")
        
        # Grounds Content
        facts = self.facts_text.toPlainText()
        html = html.replace("{{GroundsContent}}", facts if facts else "(Grounds and quantification will appear here...)")
        
        # SCN Specific Fields
        html = html.replace("{{Issue}}", self.issue_input.text() or "tax liability")
        html = html.replace("{{Jurisdiction}}", "Paravur Range")  # Can be made configurable
        
        # Calculate totals from amount table
        cgst_total = 0
        sgst_total = 0
        igst_total = 0
        
        for row in range(self.amount_table.rowCount()):
            act_item = self.amount_table.item(row, 0)
            if not act_item:
                continue
            act = act_item.text()
            
            try:
                tax = float(self.amount_table.item(row, 3).text() or 0)
            except:
                tax = 0.0
            
            if "CGST" in act:
                cgst_total += tax
            elif "SGST" in act or "UTGST" in act:
                sgst_total += tax
            elif "IGST" in act:
                igst_total += tax
        
        total_amount = cgst_total + sgst_total + igst_total
        
        html = html.replace("{{CGSTAmount}}", f"{cgst_total:,.0f}")
        html = html.replace("{{SGSTAmount}}", f"{sgst_total:,.0f}")
        html = html.replace("{{IGSTAmount}}", f"{igst_total:,.0f}")
        html = html.replace("{{TotalAmount}}", f"{total_amount:,.0f}")
        
        # Section references
        html = html.replace("{{SectionContravened}}", section)
        html = html.replace("{{SectionDemand}}", section)
        
        # Relied Documents
        relied_docs = self.relied_docs_input.toPlainText().strip()
        if relied_docs:
            docs_rows = ""
            for i, doc in enumerate(relied_docs.split('\n'), 1):
                if doc.strip():
                    docs_rows += f"""
                    <tr>
                        <td style="border: 1px solid black; padding: 8px; text-align: center;">{i}</td>
                        <td style="border: 1px solid black; padding: 8px;">{doc.strip()}</td>
                    </tr>
                    """
            html = html.replace("{{ReliedDocumentsRows}}", docs_rows)
        else:
            html = html.replace("{{ReliedDocumentsRows}}", "<tr><td colspan='2' style='border: 1px solid black; padding: 8px; text-align: center;'>(Documents will be listed here)</td></tr>")
        
        # Officer Details (can be made configurable)
        html = html.replace("{{OfficerName}}", "")
        html = html.replace("{{OfficerDesignation}}", "Superintendent")
        
        # Copy Submitted To
        copy_to = self.copy_to_input.toPlainText().strip()
        html = html.replace("{{CopySubmittedTo}}", copy_to if copy_to else "(Copy submission details)")
        
        return html

    def check_form_type_for_case_flow(self, form_type):
        """
        Handle workflow logic based on selected form type.
        - SCN: Prompt to continue from DRC-01A
        - Order: Check for active case
        """
        # Reset current case ID if user changes form type manually (unless we just set it)
        # self.current_case_id = None 
        
        if "SCN" in form_type or "Show Cause Notice" in form_type:
            # Prompt for existing DRC-01A
            reply = QMessageBox.question(
                self, 
                "Case Workflow", 
                "Do you want to continue from an existing DRC-01A?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.select_existing_case("DRC-01A_GENERATED")
                
        elif "DRC-07" in form_type or "Order" in form_type:
            # We will check for active case during generation or we could prompt now
            # For now, let's just log it or maybe auto-fill if GSTIN is present
            pass

    def select_existing_case(self, status_filter):
        """Show dialog to select an existing case"""
        from PyQt6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QAbstractItemView
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Existing Case")
        dialog.resize(800, 400)
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Case ID", "GSTIN", "Legal Name", "Section", "Date"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Get cases
        all_cases = self.db.get_all_case_files()
        filtered_cases = [c for c in all_cases if c.get('Status') == status_filter]
        
        table.setRowCount(len(filtered_cases))
        for i, case in enumerate(filtered_cases):
            table.setItem(i, 0, QTableWidgetItem(str(case.get('CaseID', ''))))
            table.setItem(i, 1, QTableWidgetItem(str(case.get('GSTIN', ''))))
            table.setItem(i, 2, QTableWidgetItem(str(case.get('Legal Name', ''))))
            table.setItem(i, 3, QTableWidgetItem(str(case.get('Section', ''))))
            table.setItem(i, 4, QTableWidgetItem(str(case.get('Created_At', ''))))
            
        layout.addWidget(table)
        
        select_btn = QPushButton("Select Case")
        def on_select():
            row = table.currentRow()
            if row >= 0:
                case_id = table.item(row, 0).text()
                self.load_case_data(case_id)
                dialog.accept()
                
        select_btn.clicked.connect(on_select)
        layout.addWidget(select_btn)
        
        dialog.exec()

    def load_case_data(self, case_data, mode=None):
        """Load data from a selected case into the wizard"""
        if isinstance(case_data, str):
            # It's an ID, fetch the case
            case = self.db.get_case_file(case_data)
        else:
            # It's already the data dict
            case = case_data
            
        if not case:
            return
            
        self.current_case_id = case.get('CaseID')
        
        # Populate fields
        self.gstin_input.setText(case.get('GSTIN', ''))
        self.legal_name_input.setText(case.get('Legal Name', ''))
        self.trade_name_input.setText(case.get('Trade Name', ''))
        
        # Try to match section
        section = case.get('Section', '')
        index = self.proceeding_combo.findText(section, Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.proceeding_combo.setCurrentIndex(index)
            
        # Handle Mode (Pre-select Form)
        if mode == "SCN":
            # Select Show Cause Notice
            index = self.form_combo.findText("Show Cause Notice", Qt.MatchFlag.MatchContains)
            if index >= 0:
                self.form_combo.setCurrentIndex(index)
        elif mode == "Order":
            # Select Order
            index = self.form_combo.findText("Order", Qt.MatchFlag.MatchContains)
            if index >= 0:
                self.form_combo.setCurrentIndex(index)
            
        QMessageBox.information(self, "Case Loaded", f"Loaded case details for {case.get('Legal Name')}\nMode: {mode if mode else 'View'}")

    def update_preview_header(self):
        """Update preview with form header based on selected form type"""
        # Just trigger a full preview update since we are now using image preview
        self.trigger_preview_update()
    
    def create_combined_step1_4(self):
        """Combined Google Form-style layout for steps 1-4 with UX improvements"""
        # Main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Stepper Progress Bar ---
        stepper_container = QWidget()
        stepper_container.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        stepper_layout = QHBoxLayout(stepper_container)
        stepper_layout.setContentsMargins(20, 10, 20, 10)
        
        steps = ["Basic Info", "Taxpayer", "Notices", "Compliance"]
        for i, step in enumerate(steps):
            step_label = QLabel(f"{i+1}. {step}")
            if i == 0:
                step_label.setStyleSheet("font-weight: bold; color: #1a73e8;")
            else:
                step_label.setStyleSheet("color: #5f6368;")
            stepper_layout.addWidget(step_label)
            
            if i < len(steps) - 1:
                arrow = QLabel(">")
                arrow.setStyleSheet("color: #dadce0; margin: 0 10px;")
                stepper_layout.addWidget(arrow)
                
        stepper_layout.addStretch()
        main_layout.addWidget(stepper_container)
        
        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f8f9fa; }")
        
        # Form container
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # ===== SECTION 0: Basic Info (Financial Year & Proceeding) =====
        section0 = self.create_form_section(
            "Case Information",
            "Enter basic case details - you can select document type (DRC-01A/SCN/Order/PH) later",
            required=True
        )
        
        # Two-column layout for FY and Proceeding
        row0 = QHBoxLayout()
        
        # Financial Year
        fy_layout = QVBoxLayout()
        fy_label = QLabel("Financial Year")
        fy_label.setStyleSheet("font-weight: bold;")
        fy_layout.addWidget(fy_label)
        
        # Generate financial years
        current_year = datetime.date.today().year
        current_month = datetime.date.today().month
        if current_month >= 4:
            end_year = current_year
        else:
            end_year = current_year - 1
        
        financial_years = []
        for year in range(2017, end_year + 1):
            fy = f"{year}-{str(year + 1)[-2:]}"
            financial_years.append(fy)
            
        self.fy_combo = QComboBox()
        self.fy_combo.addItem("-- Select Financial Year --")
        self.fy_combo.addItems(financial_years)
        self.fy_combo.setStyleSheet(self.get_combo_style())
        self.fy_combo.currentIndexChanged.connect(self.trigger_preview_update)
        fy_layout.addWidget(self.fy_combo)
        row0.addLayout(fy_layout)
        
        # Proceeding Type
        proc_layout = QVBoxLayout()
        proc_label = QLabel("Proceeding Type")
        proc_label.setStyleSheet("font-weight: bold;")
        proc_layout.addWidget(proc_label)
        
        self.proceeding_combo = QComboBox()
        self.proceeding_combo.addItem("-- Select Proceeding Type --")
        self.proceeding_combo.addItems(PROCEEDING_TYPES)
        self.proceeding_combo.setStyleSheet(self.get_combo_style())
        self.proceeding_combo.currentIndexChanged.connect(self.update_form_options)
        self.proceeding_combo.currentIndexChanged.connect(self.trigger_preview_update)
        proc_layout.addWidget(self.proceeding_combo)
        row0.addLayout(proc_layout)
        
        section0.layout().addLayout(row0)
        
        # Period Selection
        period_layout = QHBoxLayout()
        
        # Period From
        p_from_layout = QVBoxLayout()
        p_from_label = QLabel("Period From")
        p_from_label.setStyleSheet("font-weight: bold;")
        p_from_layout.addWidget(p_from_label)
        self.period_from_date = QDateEdit()
        self.period_from_date.setCalendarPopup(True)
        self.period_from_date.setDate(QDate.currentDate().addMonths(-12))
        self.period_from_date.setStyleSheet(self.get_input_style())
        self.period_from_date.dateChanged.connect(self.trigger_preview_update)
        p_from_layout.addWidget(self.period_from_date)
        period_layout.addLayout(p_from_layout)
        
        # Period To
        p_to_layout = QVBoxLayout()
        p_to_label = QLabel("Period To")
        p_to_label.setStyleSheet("font-weight: bold;")
        p_to_layout.addWidget(p_to_label)
        self.period_to_date = QDateEdit()
        self.period_to_date.setCalendarPopup(True)
        self.period_to_date.setDate(QDate.currentDate())
        self.period_to_date.setStyleSheet(self.get_input_style())
        self.period_to_date.dateChanged.connect(self.trigger_preview_update)
        p_to_layout.addWidget(self.period_to_date)
        period_layout.addLayout(p_to_layout)
        
        section0.layout().addLayout(period_layout)
        
        form_layout.addWidget(section0)
        
        # ===== HIDDEN: Form Type and Section (Not needed for case file creation) =====
        # These are hidden but kept for backward compatibility with existing code
        self.form_combo = QComboBox()
        self.form_combo.addItem("DRC-01A (Intimation)")
        self.form_combo.setCurrentIndex(0)
        self.form_combo.hide()
        
        self.drc_section_combo = QComboBox()
        self.drc_section_combo.addItem("Section 73(5)")
        self.drc_section_combo.addItem("Section 74(5)")
        self.drc_section_combo.hide()
        
        # Hidden document number fields for compatibility
        self.oc_number_input = QLineEdit()
        self.oc_number_input.hide()
        self.scn_number_input = QLineEdit()
        self.scn_number_input.hide()
        self.oio_number_input = QLineEdit()
        self.oio_number_input.hide()
        self.scn_number_widget = QWidget()
        self.scn_number_widget.hide()
        self.oio_number_widget = QWidget()
        self.oio_number_widget.hide()
        
        # ===== SECTION 2: Taxpayer Details =====
        section2 = self.create_form_section(
            "Taxpayer Details",
            "Enter or search for the taxpayer's GSTIN",
            required=True
        )
        
        # GSTIN Search
        gstin_layout = QVBoxLayout()
        gstin_label = QLabel("GSTIN *")
        gstin_label.setStyleSheet("font-weight: bold;")
        gstin_layout.addWidget(gstin_label)
        
        self.gstin_input = QLineEdit()
        self.gstin_input.setPlaceholderText("Enter GSTIN to search...")
        self.gstin_input.setStyleSheet(self.get_input_style())
        self.gstin_input.textChanged.connect(self.search_gstin)
        self.gstin_input.textChanged.connect(self.trigger_preview_update)
        
        # Auto-complete
        completer = QCompleter(self.gstin_list)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.gstin_input.setCompleter(completer)
        gstin_layout.addWidget(self.gstin_input)
        
        section2.layout().addLayout(gstin_layout)
        
        # Two-column layout for Names
        names_row = QHBoxLayout()
        
        # Legal Name
        legal_layout = QVBoxLayout()
        legal_label = QLabel("Legal Name")
        legal_label.setStyleSheet("font-weight: bold;")
        legal_layout.addWidget(legal_label)
        self.legal_name_input = QLineEdit()
        self.legal_name_input.setPlaceholderText("Auto-populated")
        self.legal_name_input.setStyleSheet(self.get_input_style())
        self.legal_name_input.textChanged.connect(self.trigger_preview_update)
        legal_layout.addWidget(self.legal_name_input)
        names_row.addLayout(legal_layout)
        
        # Trade Name
        trade_layout = QVBoxLayout()
        trade_label = QLabel("Trade Name")
        trade_label.setStyleSheet("font-weight: bold;")
        trade_layout.addWidget(trade_label)
        self.trade_name_input = QLineEdit()
        self.trade_name_input.setPlaceholderText("Auto-populated")
        self.trade_name_input.setStyleSheet(self.get_input_style())
        self.trade_name_input.textChanged.connect(self.trigger_preview_update)
        trade_layout.addWidget(self.trade_name_input)
        names_row.addLayout(trade_layout)
        
        section2.layout().addLayout(names_row)
        
        # Address
        addr_layout = QVBoxLayout()
        addr_label = QLabel("Address")
        addr_label.setStyleSheet("font-weight: bold;")
        addr_layout.addWidget(addr_label)
        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("Taxpayer Address")
        self.address_input.setMaximumHeight(80)
        self.address_input.setStyleSheet(self.get_input_style())
        self.address_input.textChanged.connect(self.trigger_preview_update)
        addr_layout.addWidget(self.address_input)
        section2.layout().addLayout(addr_layout)
        
        # Email and Mobile (Two Columns)
        contact_row = QHBoxLayout()
        
        # Email
        email_layout = QVBoxLayout()
        email_label = QLabel("Email")
        email_label.setStyleSheet("font-weight: bold;")
        email_layout.addWidget(email_label)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address")
        self.email_input.setStyleSheet(self.get_input_style())
        email_layout.addWidget(self.email_input)
        contact_row.addLayout(email_layout)
        
        # Mobile
        mobile_layout = QVBoxLayout()
        mobile_label = QLabel("Mobile")
        mobile_label.setStyleSheet("font-weight: bold;")
        mobile_layout.addWidget(mobile_label)
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("Mobile Number")
        self.mobile_input.setStyleSheet(self.get_input_style())
        mobile_layout.addWidget(self.mobile_input)
        contact_row.addLayout(mobile_layout)
        
        section2.layout().addLayout(contact_row)
        
        # Hidden fields
        self.constitution_input = QLineEdit()
        self.constitution_input.hide()
        section2.layout().addWidget(self.constitution_input)
        
        form_layout.addWidget(section2)
        
        # ===== SECTION 3: Additional Details =====
        section3 = self.create_form_section(
            "Additional Details",
            "Enter issue description, relied documents, and copy to",
            required=False
        )
        
        # Issue
        issue_layout = QVBoxLayout()
        issue_label = QLabel("Issue / Subject")
        issue_label.setStyleSheet("font-weight: bold;")
        issue_layout.addWidget(issue_label)
        self.issue_input = QLineEdit()
        self.issue_input.setPlaceholderText("Brief description of the issue")
        self.issue_input.setStyleSheet(self.get_input_style())
        issue_layout.addWidget(self.issue_input)
        section3.layout().addLayout(issue_layout)
        
        # Two-column for Relied Docs and Copy To
        details_row = QHBoxLayout()
        
        # Relied Docs
        relied_layout = QVBoxLayout()
        relied_label = QLabel("Relied Documents")
        relied_label.setStyleSheet("font-weight: bold;")
        relied_layout.addWidget(relied_label)
        self.relied_docs_input = QTextEdit()
        self.relied_docs_input.setPlaceholderText("One document per line")
        self.relied_docs_input.setMaximumHeight(80)
        self.relied_docs_input.setStyleSheet(self.get_input_style())
        relied_layout.addWidget(self.relied_docs_input)
        details_row.addLayout(relied_layout)
        
        # Copy To
        copy_layout = QVBoxLayout()
        copy_label = QLabel("Copy To")
        copy_label.setStyleSheet("font-weight: bold;")
        copy_layout.addWidget(copy_label)
        self.copy_to_input = QTextEdit()
        self.copy_to_input.setPlaceholderText("Copy submitted to...")
        self.copy_to_input.setMaximumHeight(80)
        self.copy_to_input.setStyleSheet(self.get_input_style())
        copy_layout.addWidget(self.copy_to_input)
        details_row.addLayout(copy_layout)
        
        section3.layout().addLayout(details_row)
        form_layout.addWidget(section3)
        
        # ===== SECTION 4: Contravened Provisions =====
        section4 = self.create_form_section(
            "Contravened Provisions",
            "Check the boxes to select applicable sections/rules",
            required=False
        )
        
        # Provisions scroll area
        provisions_scroll = QScrollArea()
        provisions_scroll.setWidgetResizable(True)
        provisions_scroll.setMaximumHeight(300)
        provisions_scroll.setStyleSheet("QScrollArea { border: 1px solid #bdc3c7; border-radius: 4px; background-color: white; }")
        
        provisions_content = QWidget()
        self.provisions_layout = QVBoxLayout(provisions_content)
        self.provisions_layout.setSpacing(8)
        
        self.provision_checks = []
        # Populate provisions
        for section in self.sections_list:
            cb = QCheckBox(section)
            cb.setEnabled(True)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("""
                QCheckBox { 
                    font-size: 13px; 
                    padding: 5px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #5f6368;
                    border-radius: 3px;
                    background-color: white;
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #1a73e8;
                    background-color: #e8f0fe;
                }
                QCheckBox::indicator:checked {
                    background-color: #1a73e8;
                    border: 2px solid #1a73e8;
                    image: url(none);
                }
            """)
            self.provisions_layout.addWidget(cb)
            self.provision_checks.append(cb)
        
        self.provisions_layout.addStretch()
        provisions_scroll.setWidget(provisions_content)
        section4.layout().addWidget(provisions_scroll)
        
        form_layout.addWidget(section4)

        # ===== SECTION 5: Compliance Details =====
        section5 = self.create_form_section(
            "Compliance Details",
            "Enter the date for compliance/payment/submissions",
            required=True
        )
        
        date_label = QLabel("Compliance / Reply Date *")
        date_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        section5.layout().addWidget(date_label)
        
        self.compliance_date = QDateEdit()
        self.compliance_date.setCalendarPopup(True)
        self.compliance_date.setDate(QDate.currentDate().addDays(30)) # Default to 30 days
        self.compliance_date.setStyleSheet("""
            QDateEdit {
                padding: 10px;
                border: 1px solid #dadce0;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
        """)
        self.compliance_date.dateChanged.connect(self.update_preview_header)
        section5.layout().addWidget(self.compliance_date)
        
        form_layout.addWidget(section5)
        
        # Add stretch at the end
        form_layout.addStretch()
        
        scroll.setWidget(form_container)
        main_layout.addWidget(scroll)
        
        # Initialize form options
        self.update_form_options()
        
        return main_widget

    def create_form_section(self, title, description, required=False):
        """Create a clean form section with card-like design and collapsible behavior"""
        # Create the collapsible box
        section = CollapsibleBox(title=f"{title} {'*' if required else ''}")
        
        # Create a container for the content
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # Add description if present
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("font-size: 12px; color: #5f6368; margin-bottom: 10px; border: none;")
            content_layout.addWidget(desc_label)
            
        # Set the content widget of the collapsible box
        section.setContentWidget(content_widget)
        
        # Monkey patch layout() to return content_layout so existing code works
        # We attach the layout to the section object to keep it alive just in case
        section._content_layout = content_layout 
        section.layout = lambda: section._content_layout
        
        return section
    
    def get_combo_style(self):
        """Get consistent modern combo box styling"""
        return """
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 14px;
                min-height: 25px;
            }
            QComboBox:hover {
                border: 1px solid #1a73e8;
                background-color: white;
            }
            QComboBox:focus {
                border: 2px solid #1a73e8;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(none);
                border-left: 2px solid #5f6368;
                border-bottom: 2px solid #5f6368;
                width: 8px;
                height: 8px;
                transform: rotate(-45deg);
                margin-right: 10px;
            }
        """
    
    def get_combo_style(self):
        """Get consistent modern combo box styling"""
        return """
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 1px solid #1a73e8;
            }
            QComboBox:focus {
                border: 2px solid #1a73e8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 0px;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                image: url(none);
                border-left: 2px solid #5f6368;
                border-bottom: 2px solid #5f6368;
                width: 8px;
                height: 8px;
                transform: rotate(-45deg);
                margin-top: -3px;
                margin-right: 10px;
            }
        """

    def get_input_style(self):
        """Get consistent modern input field styling"""
        return """
            QLineEdit, QTextEdit, QDateEdit {
                padding: 8px 12px;
                border: 1px solid #dadce0;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
                selection-background-color: #d2e3fc;
                selection-color: #174ea6;
            }
            QLineEdit:hover, QTextEdit:hover, QDateEdit:hover {
                border: 1px solid #1a73e8;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
                border: 2px solid #1a73e8;
                background-color: #f8f9fa;
            }
        """

    def create_step5(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Grounds and Quantification:"))
        
        # Templates dropdown
        template_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItem("Select a template to append...")
        template_layout.addWidget(self.template_combo)
        
        add_template_btn = QPushButton("Add Template")
        add_template_btn.clicked.connect(self.add_template)
        template_layout.addWidget(add_template_btn)
        l.addLayout(template_layout)

        self.facts_text = QTextEdit()
        self.facts_text.textChanged.connect(self.update_preview_header) # Real-time preview update
        l.addWidget(self.facts_text)
        
        # --- SCN Specific Fields (Hidden by default) ---
        self.scn_fields_widget = QWidget()
        scn_layout = QVBoxLayout(self.scn_fields_widget)
        scn_layout.setContentsMargins(0, 10, 0, 0)
        
        # Issue Description
        scn_layout.addWidget(QLabel("Issue Description (e.g., 'short payment of tax'):"))
        self.issue_input = QLineEdit()
        self.issue_input.setPlaceholderText("Brief description of the issue")
        self.issue_input.setStyleSheet(self.get_input_style())
        scn_layout.addWidget(self.issue_input)
        
        # Relied Documents
        scn_layout.addWidget(QLabel("Relied Documents (One per line):"))
        self.relied_docs_input = QTextEdit()
        self.relied_docs_input.setPlaceholderText("List documents relied upon...")
        self.relied_docs_input.setMaximumHeight(100)
        self.relied_docs_input.setStyleSheet(self.get_input_style())
        scn_layout.addWidget(self.relied_docs_input)
        
        # Copy Submitted To
        scn_layout.addWidget(QLabel("Copy Submitted To (One per line):"))
        self.copy_to_input = QTextEdit()
        self.copy_to_input.setPlaceholderText("List officials/departments...")
        self.copy_to_input.setMaximumHeight(100)
        self.copy_to_input.setStyleSheet(self.get_input_style())
        scn_layout.addWidget(self.copy_to_input)
        
        l.addWidget(self.scn_fields_widget)
        self.scn_fields_widget.hide() # Hide initially
        
        return w

    def create_step6(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Tax, Interest, Penalty Amount Entry:"))
        
        # Act Selection Menu
        act_layout = QHBoxLayout()
        self.act_btn = QPushButton("Select Applicable Acts")
        self.act_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.act_menu = QMenu()
        self.act_menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #bdc3c7; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #ecf0f1; }")
        
        acts = ["CGST Act", "SGST/UTGST Act", "IGST Act", "Cess"]
        self.act_actions = {}
        
        for act in acts:
            action = QAction(act, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, a=act: self.toggle_act_row(a, checked))
            self.act_menu.addAction(action)
            self.act_actions[act] = action
            
        self.act_btn.setMenu(self.act_menu)
        act_layout.addWidget(self.act_btn)
        act_layout.addStretch()
        l.addLayout(act_layout)
        
        # Dynamic Table
        self.amount_table = QTableWidget()
        self.amount_table.setColumnCount(7)
        self.amount_table.setHorizontalHeaderLabels(["Act", "From", "To", "Tax", "Interest", "Penalty", "Total"])
        self.amount_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Initialize with 0 rows
        self.amount_table.setRowCount(0)
        
        self.amount_table.itemChanged.connect(self.update_preview_header) # Real-time preview update
        l.addWidget(self.amount_table)
        
        btn_layout = QHBoxLayout()
        calc_btn = QPushButton("Calculate Totals")
        calc_btn.clicked.connect(self.calculate_totals)
        btn_layout.addWidget(calc_btn)
        l.addLayout(btn_layout)
        
        # Default Selection: CGST
        self.act_actions["CGST Act"].setChecked(True)
        self.toggle_act_row("CGST Act", True)
        
        return w

    def toggle_act_row(self, act_name, checked):
        """Add or remove row for the selected act"""
        if checked:
            # Add Row
            row = self.amount_table.rowCount()
            self.amount_table.insertRow(row)
            
            # Act Name (Read-only)
            item = QTableWidgetItem(act_name)
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.amount_table.setItem(row, 0, item)
            
            months = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"]
            
            # From Month (Dropdown)
            from_combo = QComboBox()
            from_combo.addItems(months)
            from_combo.setStyleSheet("QComboBox { border: none; background: transparent; }")
            from_combo.currentIndexChanged.connect(self.update_preview_header)
            self.amount_table.setCellWidget(row, 1, from_combo)
            
            # To Month (Dropdown)
            to_combo = QComboBox()
            to_combo.addItems(months)
            to_combo.setStyleSheet("QComboBox { border: none; background: transparent; }")
            to_combo.currentIndexChanged.connect(self.update_preview_header)
            self.amount_table.setCellWidget(row, 2, to_combo)
            
            # Amounts (0.00 default)
            for col in range(3, 7):
                self.amount_table.setItem(row, col, QTableWidgetItem("0.00"))
                
        else:
            # Remove Row
            for row in range(self.amount_table.rowCount()):
                item = self.amount_table.item(row, 0)
                if item and item.text() == act_name:
                    self.amount_table.removeRow(row)
                    break
        
        # Sync Preview
        self.update_preview_header()

    def create_step7(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Preview & Generate:"))
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        l.addWidget(self.preview_text)
        
        btn_layout = QHBoxLayout()
        gen_pdf_btn = QPushButton("Generate PDF")
        gen_pdf_btn.clicked.connect(lambda: self.generate_document('pdf'))
        btn_layout.addWidget(gen_pdf_btn)
        
        gen_word_btn = QPushButton("Generate Word")
        gen_word_btn.clicked.connect(lambda: self.generate_document('word'))
        btn_layout.addWidget(gen_word_btn)
        
        l.addLayout(btn_layout)
        return w

    # --- Logic ---

    def validate_combined_form(self):
        """Validate all fields in the combined step 1-4"""
        # 1. Financial Year
        if self.fy_combo.currentIndex() <= 0:
            QMessageBox.warning(self, "Validation Error", "Please select a Financial Year.")
            return False
            
        # 2. Proceeding Type
        if self.proceeding_combo.currentIndex() <= 0:
            QMessageBox.warning(self, "Validation Error", "Please select a Proceeding Type.")
            return False
            
        # Form type is auto-set to DRC-01A, no validation needed
            
        # 3. Taxpayer Details
        if not self.gstin_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter GSTIN.")
            return False
            
        if not self.legal_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter Legal Name.")
            return False
            
        if not self.address_input.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter Address.")
            return False
            
        return True

    def go_next(self):
        # New structure: Step 0 (combined 1-4), Step 1 (Facts), Step 2 (Amounts), Step 3 (Preview)
        if self.current_step < 3:
            # Validation and setup for next step
            if self.current_step == 0:
                # Validate combined form before proceeding
                if not self.validate_combined_form():
                    return
                self.update_templates_list()
            elif self.current_step == 2:
                # Before preview, update it
                self.update_preview()
                self.next_btn.setText("Finish")
            
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_header_label()
            self.back_btn.setEnabled(True)
        else:
            self.finish_wizard()

    def go_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
        # Provisions are now optional - no validation needed
        # has_provision = any(cb.isChecked() for cb in self.provision_checks)
        # if not has_provision:
        #     QMessageBox.warning(self, "Validation Error", "Please select at least one contravened provision.")
        #     return False
        
        return True

    def update_form_options(self):
        selected_proc = self.proceeding_combo.currentText()
        
        # Skip if placeholder is selected
        if selected_proc.startswith("--"):
            return
            
        # Extract section number (e.g., "Section 73")
        section = selected_proc.split('(')[0].strip()
        
        forms = FORMS_MAP.get(section, FORMS_MAP["Default"])
        self.form_combo.clear()
        self.form_combo.addItem("-- Select Form / Notice Type --")
        self.form_combo.addItems(forms)

    def on_form_type_changed(self):
        """Handle form type changes: Show/hide relevant fields"""
        form_type = self.form_combo.currentText()
        
        # DRC Section Combo
        if "DRC-01A" in form_type:
            self.drc_section_combo.show()
        else:
            self.drc_section_combo.hide()
            
        # SCN Fields
        if "SCN" in form_type or "Show Cause Notice" in form_type:
            self.scn_fields_widget.show()
            self.scn_number_widget.show()
        else:
            self.scn_fields_widget.hide()
            self.scn_number_widget.hide()
        
        # OIO Number Field
        if "DRC-07" in form_type or "Order" in form_type:
            self.oio_number_widget.show()
        else:
            self.oio_number_widget.hide()
            
        # Trigger case flow check
        self.check_form_type_for_case_flow(form_type)

    def search_gstin(self, text=None):
        # Handle signal arguments:
        # - text is str from completer.activated
        # - text is bool from button.clicked
        # - text is None from returnPressed (if no arg passed)
        
        if isinstance(text, str) and text:
            gstin = text.strip()
            # Also update the input field if it's not already set (e.g. if triggered programmatically)
            self.gstin_input.setText(gstin)
        else:
            gstin = self.gstin_input.text().strip()

        if not gstin:
            return
            
        data = self.db.get_taxpayer(gstin)
        if data:
            # Helper function to safely convert values, handling NaN
            def safe_str(value):
                if pd.isna(value) or value == 'nan':
                    return ''
                return str(value)
            
            # Helper function to format mobile number without decimal
            def format_mobile(value):
                if pd.isna(value) or value == 'nan':
                    return ''
                try:
                    # Convert to int first to remove decimal, then to string
                    return str(int(float(value)))
                except (ValueError, TypeError):
                    return str(value)
            
            self.legal_name_input.setText(safe_str(data.get('Legal Name', '')))
            self.trade_name_input.setText(safe_str(data.get('Trade Name', '')))
            self.address_input.setText(safe_str(data.get('Address', '')))
            self.email_input.setText(safe_str(data.get('Email', '')))
            self.mobile_input.setText(format_mobile(data.get('Mobile', '')))
            self.constitution_input.setText(safe_str(data.get('Constitution', '')))
        else:
            # Only show warning if explicitly searched (not just typing)
            # But here we are triggering on selection, so warning is okay if not found (unexpected)
            # However, for smooth UX, maybe just log it or show status
            pass # Suppress warning for smoother UX during typing/selecting, or keep it?
            # If user explicitly clicked Search, they expect feedback.
            # If triggered by completer, it should exist.
            if not isinstance(text, str): # If button clicked
                 QMessageBox.warning(self, "Not Found", "GSTIN not found in database. Please enter details manually.")

    def update_header_label(self):
        """Update the header label based on the current step"""
        steps = [
            "Step 1: Basic Details",
            "Step 2: Grounds & Detailed Facts",
            "Step 3: Tax & Dues",
            "Step 4: Preview & Generate"
        ]
        
        if 0 <= self.current_step < len(steps):
            self.header_label.setText(f"Adjudication Wizard - {steps[self.current_step]}")
        else:
            self.header_label.setText("Adjudication Wizard")


    def update_templates_list(self):
        self.template_combo.clear()
        self.template_combo.addItem("Select a template to append...")
        
        # 1. Load active issues from DB (New Method)
        active_issues = self.db.get_active_issues()
        if active_issues:
            self.template_combo.addItem("--- Active Issues ---")
            for issue in active_issues:
                # Issue JSON contains 'issue_name' and 'templates' dict
                name = issue.get('issue_name', 'Unnamed Issue')
                # Store full issue object
                self.template_combo.addItem(f"Issue: {name}", userData={'type': 'issue', 'data': issue})
        
        # 2. Load legacy file templates (Fallback)
        if self.templates_list:
             self.template_combo.addItem("--- Legacy Templates ---")
             for i, tmpl in enumerate(self.templates_list):
                preview = tmpl[:50].replace('\n', ' ') + "..."
                self.template_combo.addItem(preview, userData={'type': 'legacy', 'data': tmpl})

    def extract_html_body(self, html):
        """Extract content from body tag to avoid nested html document issues"""
        import re
        if not html: return ""
        match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return html

    def add_template(self):
        idx = self.template_combo.currentIndex()
        if idx > 0:
            item_data = self.template_combo.itemData(idx)
            
            # 1. Handle Active Issue (Dict)
            if isinstance(item_data, dict) and item_data.get('type') == 'issue':
                issue = item_data['data']
                templates = issue.get('templates', {})
                
                # Construct formatted content
                content_parts = []
                
                if templates.get('brief_facts'):
                    clean_facts = self.extract_html_body(templates['brief_facts'])
                    content_parts.append(f"<b>Brief Facts:</b><br>{clean_facts}")
                    
                if templates.get('grounds'):
                    clean_grounds = self.extract_html_body(templates['grounds'])
                    content_parts.append(f"<b>Grounds:</b><br>{clean_grounds}")
                    
                if templates.get('legal'):
                    clean_legal = self.extract_html_body(templates['legal'])
                    content_parts.append(f"<b>Legal Provisions:</b><br>{clean_legal}")
                    
                if templates.get('conclusion'):
                    clean_concl = self.extract_html_body(templates['conclusion'])
                    content_parts.append(f"<b>Conclusion:</b><br>{clean_concl}")
                    
                full_content = "<br><br>".join(content_parts)
                
                # Append to Facts Editor
                cursor = self.facts_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.facts_text.setTextCursor(cursor)
                
                if self.facts_text.toPlainText().strip():
                     self.facts_text.insertHtml("<br><br><hr><br>")
                
                self.facts_text.insertHtml(full_content)
                
                # Also Auto-fill Issue Description if empty
                if not self.issue_input.text():
                    self.issue_input.setText(issue.get('issue_name', ''))
                    
            # 2. Handle Legacy Template (String)
            elif isinstance(item_data, dict) and item_data.get('type') == 'legacy':
                tmpl = item_data['data']
                current_text = self.facts_text.toPlainText()
                if current_text:
                    current_text += "\n\n"
                self.facts_text.setPlainText(current_text + tmpl)

            # 3. Handle Old Format (Raw String) - Fallback
            elif isinstance(item_data, str): 
                current_text = self.facts_text.toPlainText()
                if current_text:
                    current_text += "\n\n"
                self.facts_text.setPlainText(current_text + item_data)

    def add_amount_row(self):
        row = self.amount_table.rowCount()
        self.amount_table.insertRow(row)
        
        # Add combo for Period (Column 0)
        period_combo = QComboBox()
        period_combo.addItem("-- Select Tax Period --")
        
        # Generate tax periods (last 3 years, monthly and quarterly)
        import datetime
        current_year = datetime.datetime.now().year
        
        # Add quarterly periods
        for year in range(current_year, current_year - 3, -1):
            for quarter in [('Apr-Jun', 'Q1'), ('Jul-Sep', 'Q2'), ('Oct-Dec', 'Q3'), ('Jan-Mar', 'Q4')]:
                period_combo.addItem(f"{quarter[0]} {year} ({quarter[1]})")
        
        # Add monthly periods
        months = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
        for year in range(current_year, current_year - 3, -1):
            for month in months:
                period_combo.addItem(f"{month} {year}")
        
        period_combo.currentIndexChanged.connect(self.update_preview_header) # Real-time preview update
        self.amount_table.setCellWidget(row, 0, period_combo)
        
        # Add combo for Tax Type (Column 1)
        tax_combo = QComboBox()
        tax_combo.addItems(TAX_TYPES)
        tax_combo.currentIndexChanged.connect(self.update_preview_header) # Real-time preview update
        self.amount_table.setCellWidget(row, 1, tax_combo)
        
        # Init other cells with 0
        for col in [2, 3, 4, 5, 6]:
            self.amount_table.setItem(row, col, QTableWidgetItem("0"))

    def calculate_totals(self):
        for row in range(self.amount_table.rowCount()):
            total = 0
            for col in [3, 4, 5]: # Tax, Int, Pen (Cols 3,4,5)
                item = self.amount_table.item(row, col)
                try:
                    val = float(item.text())
                    total += val
                except:
                    pass
            self.amount_table.setItem(row, 6, QTableWidgetItem(f"{total:.2f}"))

    def collect_data(self):
        data = {
            "financial_year": self.fy_combo.currentText(),
            "proceeding_type": self.proceeding_combo.currentText(),
            "form_type": self.form_combo.currentText(),
            "gstin": self.gstin_input.text(),
            "legal_name": self.legal_name_input.text(),
            "trade_name": self.trade_name_input.text(),
            "address": self.address_input.toPlainText(),
            "facts": self.facts_text.toPlainText(),
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "compliance_date": self.compliance_date.date().toString("dd/MM/yyyy"),
            "tax_data": []
        }
        
        # Provisions
        provisions = []
        for cb in self.provision_checks:
            if cb.isChecked():
                provisions.append(cb.text())
        data["provisions"] = provisions
        
        # Tax Data
        for row in range(self.amount_table.rowCount()):
            row_data = {
                "Act": self.amount_table.item(row, 0).text(),
                "From": self.amount_table.cellWidget(row, 1).currentText(),
                "To": self.amount_table.cellWidget(row, 2).currentText(),
                "Tax": self.amount_table.item(row, 3).text(),
                "Interest": self.amount_table.item(row, 4).text(),
                "Penalty": self.amount_table.item(row, 5).text(),
                "Total": self.amount_table.item(row, 6).text()
            }
            data["tax_data"].append(row_data)
            
        return data

    def update_preview(self):
        data = self.collect_data()
        preview = f"""GOVERNMENT OF INDIA
GOODS AND SERVICES TAX DEPARTMENT

NOTICE: {data['form_type']}

Date: {data['date']}
To,
{data['legal_name']} ({data['trade_name']})
GSTIN: {data['gstin']}
Address: {data['address']}

Subject: Notice under {data['proceeding_type']}

Brief Facts:
{data['facts']}

Tax Details:
"""
        for row in data['tax_data']:
            preview += f"{row['Act']} | {row['From']} - {row['To']} | Tax: {row['Tax']} | Int: {row['Interest']} | Pen: {row['Penalty']} | Total: {row['Total']}\n"
            
        self.preview_text.setPlainText(preview)

    def generate_document(self, doc_type):
        data = self.collect_data()
        filename = f"{data['legal_name']}_{data['form_type']}_{data['date']}".replace(" ", "_")
        
        try:
            if doc_type == 'pdf':
                # Always use HTML letterhead for PDF (from pdf_letterhead setting)
                letterhead_path = self.config.get_letterhead_path('pdf')
                
                # Check if we have DRC-01A form - use HTML-based generation
                form_code = data['form_type'].replace("Form ", "").replace("GST ", "").strip()
                
                if form_code == "DRC-01A":
                    # Regenerate HTML from template
                    form_html = self.generate_drc01a_html()
                    
                    # Extract letterhead content (just the div)
                    with open(letterhead_path, 'r', encoding='utf-8') as f:
                        letterhead_full = f.read()
                        
                    # Simple extraction of the letterhead div
                    import re
                    match = re.search(r'(<div class="letterhead.*?">.*?</div>)', letterhead_full, re.DOTALL)
                    if match:
                        letterhead_div = match.group(1)
                    else:
                        letterhead_div = "<div style='text-align:center'><h1>GOVERNMENT OF INDIA</h1></div>"
                        
                    # Inject letterhead INTO the form
                    html_content = form_html.replace(
                        '<div id="letterhead-placeholder"></div>',
                        letterhead_div
                    )
                    
                    path = self.doc_gen.generate_pdf_from_html(html_content, filename)
                    
                    # Save HTML for preview
                    html_path = os.path.join(os.path.dirname(path), filename + ".html")
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                        
                elif "SCN" in form_code or "Show Cause Notice" in data['form_type']:
                    # Regenerate HTML from template
                    form_html = self.generate_scn_html()
                    
                    # Extract letterhead content
                    with open(letterhead_path, 'r', encoding='utf-8') as f:
                        letterhead_full = f.read()
                        
                    # Simple extraction of the letterhead div
                    import re
                    match = re.search(r'(<div class="letterhead.*?">.*?</div>)', letterhead_full, re.DOTALL)
                    if match:
                        letterhead_div = match.group(1)
                    else:
                        letterhead_div = "<div style='text-align:center'><h1>GOVERNMENT OF INDIA</h1></div>"
                        
                    # Inject letterhead INTO the form
                    html_content = form_html.replace(
                        '<div id="letterhead-placeholder"></div>',
                        letterhead_div
                    )
                    
                    path = self.doc_gen.generate_pdf_from_html(html_content, filename)
                    
                    # Save HTML for preview
                    html_path = os.path.join(os.path.dirname(path), filename + ".html")
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                else:
                    # Use standard PDF generation for other forms
                    path = self.doc_gen.generate_pdf(data, filename)
                    html_path = "" # No HTML available
            else:
                # Use Word letterhead setting (can be HTML or DOCX)
                letterhead_path = self.config.get_letterhead_path('word')
                letterhead_type = self.config.get_letterhead_type(
                    self.config.get_word_letterhead()
                )
                
                if letterhead_type == 'docx':
                    # Use DOCX letterhead for Word generation
                    path = self.doc_gen.generate_word_from_docx(letterhead_path, data, filename)
                else:
                    # Use standard Word generation with HTML letterhead
                    path = self.doc_gen.generate_word(data, filename)
                html_path = ""
                
            QMessageBox.information(self, "Success", f"Document generated at:\n{path}")
            
            # Save case to DB (Legacy)
            case_record = {
                "CaseID": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                "GSTIN": data['gstin'],
                "Legal Name": data['legal_name'],
                "Proceeding Type": data['proceeding_type'],
                "Form Type": data['form_type'],
                "Date": data['date'],
                "Status": "Generated",
                "FilePath": path
            }
            self.db.add_case(case_record)

            # ---------------- Case File Register Logic ----------------
            form_type = data['form_type']
            
            # Calculate demands from amount table
            cgst_demand = 0
            sgst_demand = 0
            igst_demand = 0
            cess_demand = 0
            
            for row in range(self.amount_table.rowCount()):
                act_item = self.amount_table.item(row, 0)
                if not act_item:
                    continue
                act = act_item.text()
                
                try:
                    tax = float(self.amount_table.item(row, 3).text() or 0)
                except:
                    tax = 0.0
                
                if "CGST" in act:
                    cgst_demand += tax
                elif "SGST" in act or "UTGST" in act:
                    sgst_demand += tax
                elif "IGST" in act:
                    igst_demand += tax
                elif "Cess" in act:
                    cess_demand += tax
            
            total_demand = cgst_demand + sgst_demand + igst_demand + cess_demand
            
            # Common OC Register fields for ALL documents
            oc_data = {
                "OC_Number": self.oc_number_input.text(),
                "OC_Content": form_type,  # e.g., "Form DRC-01A", "Show Cause Notice"
                "OC_Date": datetime.date.today().strftime("%d/%m/%Y"),
                "OC_To": f"{data['legal_name']}, {data['gstin']}",
                "OC_Copy_To": self.copy_to_input.toPlainText() if hasattr(self, 'copy_to_input') else "",
                "CGST_Demand": cgst_demand,
                "SGST_Demand": sgst_demand,
                "IGST_Demand": igst_demand,
                "Cess_Demand": cess_demand,
                "Total_Demand": total_demand,
                "Financial_Year": data.get('financial_year', ''),
                "Issue_Description": self.issue_input.text() if hasattr(self, 'issue_input') else ""
            }
            
            # 1. DRC-01A Generation
            if "DRC-01A" in form_type:
                new_case_data = {
                    **oc_data,
                    "GSTIN": data['gstin'],
                    "Legal Name": data['legal_name'],
                    "Trade Name": data['trade_name'],
                    "Section": data['proceeding_type'],
                    "Status": "DRC-01A_GENERATED",
                    "DRC01A_Path": path,
                    "DRC01A_HTML_Path": html_path
                }
                self.current_case_id = self.db.create_case_file(new_case_data)
                print(f"DEBUG: Created new case {self.current_case_id}")

            # 2. SCN Generation
            elif "SCN" in form_type or "Show Cause Notice" in form_type:
                if self.current_case_id:
                    # Update existing case
                    updates = {
                        **oc_data,
                        "Status": "SCN_ISSUED",
                        "DRC01_Path": path,
                        "SCN_HTML_Path": html_path,
                        "SCN_Number": self.scn_number_input.text(),
                        "SCN_Date": datetime.date.today().strftime("%d/%m/%Y")
                    }
                    self.db.update_case_file(self.current_case_id, updates)
                    print(f"DEBUG: Updated case {self.current_case_id} with SCN")
                else:
                    # Direct SCN
                    new_case_data = {
                        **oc_data,
                        "GSTIN": data['gstin'],
                        "Legal Name": data['legal_name'],
                        "Trade Name": data['trade_name'],
                        "Section": data['proceeding_type'],
                        "Status": "SCN_DRAFTED_DIRECT",
                        "DRC01_Path": path,
                        "SCN_HTML_Path": html_path,
                        "SCN_Number": self.scn_number_input.text(),
                        "SCN_Date": datetime.date.today().strftime("%d/%m/%Y")
                    }
                    self.current_case_id = self.db.create_case_file(new_case_data)
                    print(f"DEBUG: Created direct SCN case {self.current_case_id}")

            # 3. Order (DRC-07) Generation
            elif "DRC-07" in form_type or "Order" in form_type:
                # Check for active case if not already selected
                if not self.current_case_id:
                    active_case = self.db.find_active_case(data['gstin'], data['proceeding_type'])
                    if active_case:
                        self.current_case_id = active_case['CaseID']

                if self.current_case_id:
                    # Update existing case
                    updates = {
                        **oc_data,
                        "Status": "ORDER_ISSUED",
                        "DRC07_Path": path,
                        "OIO_Number": self.oio_number_input.text(),
                        "OIO_Date": datetime.date.today().strftime("%d/%m/%Y")
                    }
                    self.db.update_case_file(self.current_case_id, updates)
                    print(f"DEBUG: Updated case {self.current_case_id} with Order")
                else:
                    # Direct Order
                    new_case_data = {
                        **oc_data,
                        "GSTIN": data['gstin'],
                        "Legal Name": data['legal_name'],
                        "Trade Name": data['trade_name'],
                        "Section": data['proceeding_type'],
                        "Status": "ORDER_ISSUED_DIRECT",
                        "DRC07_Path": path,
                        "OIO_Number": self.oio_number_input.text(),
                        "OIO_Date": datetime.date.today().strftime("%d/%m/%Y")
                    }
                    self.current_case_id = self.db.create_case_file(new_case_data)
                    print(f"DEBUG: Created direct Order case {self.current_case_id}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def finish_wizard(self):
        self.home_callback()
        # Reset wizard
        self.current_step = 0
        self.stack.setCurrentIndex(0)
        self.gstin_input.clear()
        self.legal_name_input.clear()
        self.facts_text.clear()
        self.amount_table.setRowCount(0)
