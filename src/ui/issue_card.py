from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QGridLayout)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard

class IssueCard(QFrame):
    # Signal emitted when any value changes, passing the calculated totals
    valuesChanged = pyqtSignal(dict)
    # Signal emitted when remove button is clicked
    removeClicked = pyqtSignal()

    def __init__(self, template, parent=None):
        super().__init__(parent)
        self.template = template
        self.variables = template.get('variables', {}).copy()
        self.calc_logic = template.get('calc_logic', "")
        self.tax_mapping = template.get('tax_demand_mapping', {})
        
        self.init_ui()
        self.calculate_values() # Initial calculation

    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("IssueCard { background-color: #ffffff; border: 1px solid #bdc3c7; border-radius: 5px; margin-bottom: 10px; }")
        
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.title = QLabel(f"<b>{self.template.get('issue_name')}</b>")
        self.title.setStyleSheet("font-size: 14px; color: #2c3e50;")
        header_layout.addWidget(self.title)
        
        header_layout.addStretch()
        
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
        remove_btn.clicked.connect(self.removeClicked.emit)
        header_layout.addWidget(remove_btn)
        
        layout.addLayout(header_layout)
        
        # Section 1: Table (Collapsible)
        table_card = ModernCard("Table", collapsible=True)
        
        # Check if we have grid_data (Excel Import) or legacy placeholders
        if 'grid_data' in self.template:
            self.init_grid_ui(table_card)
        elif isinstance(self.template.get('tables'), dict):
            self.init_excel_table_ui(table_card)
            
        # Also load legacy placeholders if they exist (Hybrid Mode)
        if self.template.get('placeholders'):
            self.init_legacy_ui(table_card)
            
        layout.addWidget(table_card)
            
        # Mini Totals (Read Only)
        totals_layout = QHBoxLayout()
        totals_layout.addWidget(QLabel("<b>Calculated Demand:</b>"))
        
        self.lbl_tax = QLabel("Tax: ₹0")
        self.lbl_interest = QLabel("Interest: ₹0")
        self.lbl_penalty = QLabel("Penalty: ₹0")
        
        for lbl in [self.lbl_tax, self.lbl_interest, self.lbl_penalty]:
            lbl.setStyleSheet("background-color: #ecf0f1; padding: 5px; border-radius: 3px; border: 1px solid #bdc3c7;")
            totals_layout.addWidget(lbl)
            
        totals_layout.addStretch()
        layout.addLayout(totals_layout)
        
        # Section 2: Brief Facts (Collapsible)
        facts_card = ModernCard("Brief Facts & Grounds", collapsible=True)
        self.editor = RichTextEditor()
        self.editor.setMinimumHeight(150)
        self.update_editor_content()
        facts_card.addWidget(self.editor)
        layout.addWidget(facts_card)

    def init_excel_table_ui(self, layout):
        """Initialize UI from Excel-like Table Builder Data"""
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        import re
        
        table_data = self.template['tables']
        rows = table_data.get('rows', 4)
        cols = table_data.get('cols', 4)
        cells = table_data.get('cells', [])
        
        self.table = QTableWidget(rows, cols)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.cell_formulas = {} # (row, col) -> formula_string
        
        for r in range(rows):
            row_data = cells[r] if r < len(cells) else []
            for c in range(cols):
                txt = row_data[c] if c < len(row_data) else ""
                item = QTableWidgetItem(txt)
                
                # Check for formula
                if txt.startswith('='):
                    self.cell_formulas[(r, c)] = txt[1:] # Store without '='
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setForeground(Qt.GlobalColor.blue)
                    item.setText("0") # Initial value
                elif r == 0 or c == 0:
                    # Headers (First row/col)
                    item.setBackground(Qt.GlobalColor.lightGray)
                    item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                
                self.table.setItem(r, c, item)
        
        self.table.itemChanged.connect(self.on_excel_table_changed)
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(400)
        # Prevent table from forcing window width too wide
        from PyQt6.QtWidgets import QSizePolicy
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table)
        
        # Initial Calc will be triggered by calculate_values in __init__

    def on_excel_table_changed(self, item):
        # Avoid recursion
        if self.table.signalsBlocked(): return
        self.calculate_excel_table()

    def calculate_excel_table(self):
        """Evaluate formulas in the Excel-like table"""
        import re
        
        # Helper to get cell value
        def get_cell_val(ref):
            # ref is like "A1", "B2"
            # Parse ref
            match = re.match(r"([A-Z]+)([0-9]+)", ref.upper())
            if not match: return 0
            
            col_str, row_str = match.groups()
            
            # Convert col_str to index (A=0, B=1, AA=26)
            col = 0
            for char in col_str:
                col = col * 26 + (ord(char) - ord('A') + 1)
            col -= 1
            
            row = int(row_str) - 1
            
            if row < 0 or row >= self.table.rowCount() or col < 0 or col >= self.table.columnCount():
                return 0
                
            item = self.table.item(row, col)
            if not item: return 0
            
            try:
                return float(item.text())
            except:
                return 0

        # Iterate formulas
        # Simple 2-pass for dependencies
        for _ in range(2):
            for (r, c), formula in self.cell_formulas.items():
                try:
                    # Replace references with values
                    # Regex to find A1, B2 etc.
                    # We use a callback to replace
                    def replace_ref(match):
                        return str(get_cell_val(match.group(0)))
                    
                    eval_expr = re.sub(r"[A-Z]+[0-9]+", replace_ref, formula.upper())
                    
                    # Safe Eval
                    allowed_names = {"abs": abs, "min": min, "max": max, "round": round}
                    res = eval(eval_expr, {"__builtins__": {}}, allowed_names)
                    
                    # Update Item
                    item = self.table.item(r, c)
                    if item:
                        self.table.blockSignals(True)
                        item.setText(str(res))
                        self.table.blockSignals(False)
                        
                except Exception as e:
                    # print(f"Formula Error {formula}: {e}")
                    pass
        
        # Populate variables with all cell values for placeholders
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        for r in range(rows):
            for c in range(cols):
                item = self.table.item(r, c)
                if item:
                    val = item.text()
                    # Get address
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    
                    addr = f"{col_label}{r+1}"
                    self.variables[addr] = val
                    
        # Trigger update of editor content to reflect new variable values
        self.update_editor_content()
        
        # Emit valuesChanged signal to update preview and totals
        # We can pass the breakdown directly if needed, but for now just emit
        self.valuesChanged.emit(self.get_tax_breakdown())

    def get_tax_breakdown(self):
        """
        Extract tax breakdown (CGST, SGST, IGST, Cess) from the table.
        Assumes the LAST ROW contains the totals/difference.
        """
        breakdown = {
            'CGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'SGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'IGST': {'tax': 0, 'interest': 0, 'penalty': 0},
            'Cess': {'tax': 0, 'interest': 0, 'penalty': 0}
        }
        
        if not hasattr(self, 'table'):
            return breakdown
            
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        if rows == 0:
            return breakdown
            
        # Use the LAST row for values
        target_row = rows - 1
        
        # Find columns by header name
        # We assume headers are in the first row (row 0)
        header_map = {}
        for c in range(cols):
            item = self.table.item(0, c)
            if item:
                header_text = item.text().strip().upper()
                header_map[header_text] = c
                
        # Helper to get float value
        def get_val(r, c):
            if c is None: return 0.0
            item = self.table.item(r, c)
            if not item: return 0.0
            try:
                return float(item.text().replace(',', ''))
            except:
                return 0.0

        # Extract values based on column headers
        # We map "CGST", "SGST", "IGST" columns to the 'tax' component of the breakdown
        # Interest and Penalty are usually separate columns or calculated elsewhere.
        # BUT, the user's table might just have "CGST", "SGST", "IGST" as amounts.
        # The standard DRC-01A table has Tax, Interest, Penalty columns.
        # The Issue Table usually calculates the TAX amount (Difference).
        # Interest and Penalty might be calculated in the main table or separate columns.
        # For now, we assume the values in CGST/SGST/IGST columns of the issue table are TAX amounts.
        
        if 'CGST' in header_map:
            breakdown['CGST']['tax'] = get_val(target_row, header_map['CGST'])
            
        if 'SGST' in header_map:
            breakdown['SGST']['tax'] = get_val(target_row, header_map['SGST'])
            
        if 'IGST' in header_map:
            breakdown['IGST']['tax'] = get_val(target_row, header_map['IGST'])
            
        if 'CESS' in header_map:
            breakdown['Cess']['tax'] = get_val(target_row, header_map['CESS'])
            
        return breakdown

    def init_grid_ui(self, layout):
        """Initialize UI from Excel Grid Data"""
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        
        grid_data = self.template['grid_data']
        if not grid_data:
            return
            
        rows = len(grid_data)
        cols = len(grid_data[0]) if rows > 0 else 0
        
        self.table = QTableWidget(rows, cols)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Populate Table
        self.cell_widgets = {} # Map var_name -> QTableWidgetItem
        
        for r, row_data in enumerate(grid_data):
            for c, cell_info in enumerate(row_data):
                item = QTableWidgetItem()
                val = cell_info.get('value')
                
                # Format value
                if val is None:
                    text = ""
                else:
                    text = str(val)
                    
                item.setText(text)
                
                # Styling based on type
                ctype = cell_info.get('type', 'empty')
                if ctype == 'static':
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setBackground(Qt.GlobalColor.lightGray)
                    item.setForeground(Qt.GlobalColor.black)
                elif ctype == 'formula':
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setBackground(Qt.GlobalColor.white) # Formula results are read-only but look like data
                    item.setForeground(Qt.GlobalColor.blue)
                elif ctype == 'input':
                    item.setBackground(Qt.GlobalColor.white)
                
                # Store metadata
                item.setData(Qt.ItemDataRole.UserRole, cell_info)
                self.table.setItem(r, c, item)
                
                # Map variable name to item for easy access
                var_name = cell_info.get('var')
                if var_name:
                    self.cell_widgets[var_name] = item
                    # Initialize variable
                    # Try to convert to float if possible for calculation
                    try:
                        self.variables[var_name] = float(text) if text else 0.0
                    except:
                        self.variables[var_name] = text
        
        self.table.itemChanged.connect(self.on_grid_item_changed)
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(400)
        from PyQt6.QtWidgets import QSizePolicy
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table)

    def init_legacy_ui(self, layout):
        """Initialize UI from legacy placeholders"""
        inputs_layout = QGridLayout()
        self.input_widgets = {}
        
        placeholders = self.template.get('placeholders', [])
        row = 0
        col = 0
        
        for p in placeholders:
            if p.get('computed'):
                continue
                
            label = QLabel(p['name'].replace('_', ' ').title() + ":")
            inputs_layout.addWidget(label, row, col)
            
            inp = QLineEdit()
            inp.setText(str(self.variables.get(p['name'], '')))
            inp.textChanged.connect(lambda val, name=p['name']: self.update_variable(name, val))
            self.input_widgets[p['name']] = inp
            inputs_layout.addWidget(inp, row, col + 1)
            
            col += 2
            if col > 2:
                col = 0
                row += 1
                
        layout.addLayout(inputs_layout)

    def on_grid_item_changed(self, item):
        """Handle changes in grid table"""
        cell_info = item.data(Qt.ItemDataRole.UserRole)
        if not cell_info:
            return
            
        # Update variable
        var_name = cell_info.get('var')
        text = item.text()
        
        try:
            val = float(text)
        except ValueError:
            val = text
            
        self.variables[var_name] = val
        
        # Trigger calculation
        self.calculate_values()

    def update_variable(self, name, value):
        self.variables[name] = value
        self.calculate_values()

    def calculate_values(self):
        # 1. Handle Excel Grid Calculation
        if 'grid_data' in self.template:
            self.calculate_grid()
        elif isinstance(self.template.get('tables'), dict) and self.template['tables'].get('rows', 0) > 0:
            self.calculate_excel_table()
            
        # 2. Handle Legacy Python Logic
        elif self.calc_logic:
            try:
                local_scope = {}
                exec(self.calc_logic, {}, local_scope)
                compute_func = local_scope.get('compute')
                
                if compute_func:
                    results = compute_func(self.variables)
                    self.variables.update(results)
            except Exception as e:
                print(f"Legacy Calculation Error: {e}")

        # 3. Update Totals
        tax = 0
        interest = 0
        penalty = 0
        
        mapping = self.tax_mapping
        
        # Helper to get value from mapping
        def get_val(key):
            ref_var = mapping.get(key)
            if not ref_var: return 0
            # If ref_var is in variables, use it
            val = self.variables.get(ref_var, 0)
            try:
                return float(val)
            except:
                return 0
                
        if 'grid_data' in self.template:
            # Use mapping to find variables
            tax = get_val('tax_cgst') + get_val('tax_sgst') + get_val('tax_igst') # Sum up components?
            # Or just 'tax' if legacy?
            if not tax: tax = get_val('tax') # Fallback for legacy
            
            interest = get_val('interest')
            penalty = get_val('penalty')
        else:
            # Legacy mapping
            tax = self.variables.get(mapping.get('tax', 'calculated_tax'), 0)
            interest = self.variables.get(mapping.get('interest', 'calculated_interest'), 0)
            penalty = self.variables.get(mapping.get('penalty', 'calculated_penalty'), 0)

        self.lbl_tax.setText(f"Tax: ₹{tax}")
        self.lbl_interest.setText(f"Interest: ₹{interest}")
        self.lbl_penalty.setText(f"Penalty: ₹{penalty}")
        
        self.valuesChanged.emit({
            'tax': tax,
            'interest': interest,
            'penalty': penalty
        })

    def calculate_grid(self):
        """Evaluate formulas in the grid"""
        # Simple iterative pass (can be improved to topological sort)
        # We do 2 passes to handle simple forward references
        
        grid_data = self.template['grid_data']
        
        for _ in range(2): 
            for r, row_data in enumerate(grid_data):
                for c, cell_info in enumerate(row_data):
                    if cell_info.get('type') == 'formula':
                        formula = cell_info.get('python_formula')
                        if not formula: continue
                        
                        try:
                            # Evaluate formula using current variables
                            # We expose 'v' as the variables dict
                            # Also expose 'round', 'max', 'min' etc.
                            context = {
                                'v': self.variables,
                                'round': round,
                                'max': max,
                                'min': min,
                                'abs': abs
                            }
                            
                            result = eval(formula, {}, context)
                            
                            # Update variable
                            var_name = cell_info.get('var')
                            self.variables[var_name] = result
                            
                            # Update UI
                            item = self.cell_widgets.get(var_name)
                            if item:
                                # Block signal to prevent recursion
                                self.table.blockSignals(True)
                                item.setText(str(result))
                                self.table.blockSignals(False)
                                
                        except Exception as e:
                            # print(f"Formula Error {formula}: {e}")
                            pass

    def calculate_excel_table(self):
        """Calculate values for dictionary-based table structure"""
        # This handles the 'tables' (plural) or 'table' (singular) dict structure if it has formulas
        # Currently OUT_001 uses 'calc_logic' (legacy), so this might not be hit for it.
        # But we implement it for completeness.
        
        tables = self.template.get('tables') or self.template.get('table')
        if not tables: return
        
        # If it's a single table dict (like in OUT_001)
        if isinstance(tables, dict) and 'rows' in tables:
            rows = tables['rows']
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        for key, val in row.items():
                            # Check if value looks like a formula {{...}} or just relies on variables
                            pass
            else:
                # rows might be an int (count) or something else
                pass
        
        # If we had explicit formulas in the table definition (not the case for OUT_001),
        # we would evaluate them here.
        pass

    def update_editor_content(self):
        """Populate editor with template text"""
        # We construct the initial text from the template
        t = self.template.get('templates', {})
        
        html = f"""
        <div style="margin-bottom: 15px;">
            <b>Brief Facts:</b><br>
            {t.get('brief_facts', '')}
        </div>
        
        <div style="margin-bottom: 15px;">
            <b>Grounds:</b><br>
            {t.get('grounds', '')}
        </div>
        
        <div style="margin-bottom: 15px;">
            <b>Legal Provisions:</b><br>
            {t.get('legal', '')}
        </div>
        
        <div style="margin-bottom: 15px;">
            <b>Conclusion:</b><br>
            {t.get('conclusion', '')}
        </div>
        """
        
        # Replace placeholders in the text
        for var_name, var_val in self.variables.items():
            html = html.replace(f"{{{{{var_name}}}}}", str(var_val))
            
        self.editor.setHtml(html)

    def generate_html(self):
        """Generate HTML representation of this issue for the report"""
        # 1. Text Content (Brief Facts, Grounds, etc.)
        html = self.editor.toHtml()
        
        # 2. Append the specific tables for this issue
        if 'grid_data' in self.template:
            grid_data = self.template['grid_data']
            html += f"""
            <div style="margin-bottom: 15px; margin-top: 10px;">
                <b>Calculation Table</b>
                <table border="1" cellspacing="0" cellpadding="5" style="width: 100%; border-collapse: collapse; font-size: 10pt;">
            """
            
            for r, row_data in enumerate(grid_data):
                html += "<tr>"
                for c, cell_info in enumerate(row_data):
                    # Determine style based on type
                    style = "border: 1px solid #000; padding: 4px;"
                    ctype = cell_info.get('type', 'empty')
                    
                    if ctype == 'static':
                        style += "background-color: #f2f2f2; font-weight: bold;"
                    elif ctype == 'formula':
                        style += "color: blue;"
                        
                    # Get current value from variables if it's a variable
                    var_name = cell_info.get('var')
                    val = cell_info.get('value', '')
                    
                    if var_name and var_name in self.variables:
                        val = self.variables[var_name]
                        
                    # Format numbers
                    try:
                        if isinstance(val, (int, float)):
                            val = f"{val:.2f}"
                    except:
                        pass
                        
                    html += f"<td style='{style}'>{val}</td>"
                html += "</tr>"
                

    @staticmethod
    def generate_table_html(template, variables):
        """Generate HTML for the table portion of the card"""
        html = ""
        # print(f"DEBUG: Generating table HTML for template {template.get('issue_id')}")
        # print(f"DEBUG: Variables: {variables}")
        
        # New Schema Table Support (Excel-like Dict)
        if isinstance(template.get('tables'), dict) and template['tables'].get('rows', 0) > 0:
            table_data = template['tables']
            rows = table_data.get('rows', 0)
            cols = table_data.get('cols', 0)
            
            html += """
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">Calculation Table</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
            """
            
            # Reconstruct grid from variables (A1, B1, etc.)
            for r in range(rows):
                html += "<tr>"
                for c in range(cols):
                    # Calculate address (A1, B1...)
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    addr = f"{col_label}{r+1}"
                    
                    # Get value
                    val = variables.get(addr, "")
                    
                    # Basic Styling
                    style = "border: 1px solid #000; padding: 8px; word-wrap: break-word; vertical-align: top;"
                    
                    # Heuristic: First row is usually header
                    if r == 0:
                        style += "background-color: #f2f2f2; font-weight: bold; text-align: center;"
                        
                        # Set Column Widths
                        if cols > 1:
                            if c == 0:
                                style += "width: 40%;"
                            else:
                                width_pct = 60 // (cols - 1)
                                style += f"width: {width_pct}%;"
                    else:
                        # Check if numeric
                        try:
                            float(str(val).replace(',', '').replace('₹', '').strip())
                            style += "text-align: right;"
                        except:
                            style += "text-align: left;"
                            
                    html += f"<td style='{style}'>{val}</td>"
                html += "</tr>"
                
            html += """
                </table>
            </div>
            """

        # Legacy Table Support (Single Table)
        elif 'table' in template:
            table = template['table']
            html += f"""
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">{table.get('title', 'Table')}</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
                    <thead>
                        <tr>
            """
            
            for col in table['columns']:
                html += f"<th style='border: 1px solid #000; padding: 8px; background-color: #f2f2f2; text-align: center; font-weight: bold;'>{col['label']}</th>"
                
            html += """
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for row in table['rows']:
                html += "<tr>"
                for col in table['columns']:
                    key = col['key']
                    val_template = row.get(key, "")
                    val = str(val_template)
                    for var_name, var_val in variables.items():
                        val = val.replace(f"{{{{{var_name}}}}}", str(var_val))
                    
                    # Align numbers to right
                    align = "left"
                    try:
                        float(val.replace(',', '').replace('₹', '').strip())
                        align = "right"
                    except:
                        pass
                        
                    html += f"<td style='border: 1px solid #000; padding: 8px; text-align: {align};'>{val}</td>"
                html += "</tr>"
                
            html += """
                    </tbody>
                </table>
            </div>
            """
            
        return html

    def generate_html(self):
        """Generate HTML for preview/PDF"""
        # 1. Get Editor Content
        html = self.editor.toHtml()
        
        # 2. Append Table
        html += self.generate_table_html(self.template, self.variables)
            
        return html

    def get_data(self):
        """Return current state for saving"""
        return {
            'issue_id': self.template['issue_id'],
            'variables': self.variables,
            'content': self.editor.toHtml(),
            'tax_breakdown': self.get_tax_breakdown()
        }

    def load_data(self, data):
        """Restore state from saved data"""
        # 1. Restore Variables
        if 'variables' in data:
            self.variables = data['variables']
            
        # 2. Restore Content
        if 'content' in data:
            self.editor.setHtml(data['content'])
            
        # 3. Synchronize UI with Variables
        
        # A. Legacy Inputs
        if hasattr(self, 'input_widgets'):
            for name, widget in self.input_widgets.items():
                if name in self.variables:
                    widget.blockSignals(True)
                    widget.setText(str(self.variables[name]))
                    widget.blockSignals(False)
                    
        # B. Grid Table (Excel Import)
        if hasattr(self, 'cell_widgets'):
            for var_name, item in self.cell_widgets.items():
                if var_name in self.variables:
                    self.table.blockSignals(True)
                    item.setText(str(self.variables[var_name]))
                    self.table.blockSignals(False)
                    
        # C. Excel-like Table (Manual Builder)
        # This one is trickier as it doesn't map 1:1 to named variables usually,
        # but relies on cell positions.
        # If we saved the table state explicitly, we could restore it.
        # But currently we only save 'variables'.
        # If the table cells populate variables (e.g. A1, B2), we can reverse map.
        if hasattr(self, 'table') and not hasattr(self, 'cell_widgets'):
            # Iterate all cells and check if they map to a variable
            rows = self.table.rowCount()
            cols = self.table.columnCount()
            for r in range(rows):
                for c in range(cols):
                    # Reconstruct address
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    addr = f"{col_label}{r+1}"
                    
                    if addr in self.variables:
                        item = self.table.item(r, c)
                        if item:
                            # Only update if it's not a formula (formulas are re-calculated)
                            # But wait, formulas might depend on inputs.
                            # We should update inputs first.
                            # Check if item is editable (input)
                            if item.flags() & Qt.ItemFlag.ItemIsEditable:
                                self.table.blockSignals(True)
                                item.setText(str(self.variables[addr]))
                                self.table.blockSignals(False)

        # 4. Trigger Calculation to update totals and formulas
        self.calculate_values()

    def get_tax_breakdown(self):
        """Return tax breakdown by Act"""
        breakdown = {}
        
        # Helper to safely get float
        def get_v(key):
            try: return float(self.variables.get(key, 0))
            except: return 0.0

        # 1. Try explicit Act variables first (if defined in template/variables)
        igst = get_v('tax_igst') or get_v('igst_tax')
        cgst = get_v('tax_cgst') or get_v('cgst_tax')
        sgst = get_v('tax_sgst') or get_v('sgst_tax')
        cess = get_v('tax_cess') or get_v('cess_tax')
        
        if igst or cgst or sgst or cess:
            if igst: breakdown['IGST'] = {'tax': igst, 'interest': get_v('interest_igst'), 'penalty': get_v('penalty_igst')}
            if cgst: breakdown['CGST'] = {'tax': cgst, 'interest': get_v('interest_cgst'), 'penalty': get_v('penalty_cgst')}
            if sgst: breakdown['SGST'] = {'tax': sgst, 'interest': get_v('interest_sgst'), 'penalty': get_v('penalty_sgst')}
            if cess: breakdown['Cess'] = {'tax': cess, 'interest': get_v('interest_cess'), 'penalty': get_v('penalty_cess')}
            return breakdown

        # 2. Smart Detection for Grid Tables (if mapping is missing)
        if isinstance(self.template.get('tables'), dict) and self.template['tables'].get('rows', 0) > 0:
            try:
                table_data = self.template['tables']
                rows = table_data.get('rows', 0)
                cols = table_data.get('cols', 0)
                cells = table_data.get('cells', [])
                
                # Find Header Row (usually row 0)
                header_map = {} # 'CGST': col_index
                if rows > 0 and len(cells) > 0:
                    for c, val in enumerate(cells[0]):
                        val_str = str(val).upper()
                        if 'CGST' in val_str: header_map['CGST'] = c
                        elif 'SGST' in val_str: header_map['SGST'] = c
                        elif 'IGST' in val_str: header_map['IGST'] = c
                        elif 'CESS' in val_str: header_map['Cess'] = c
                
                # Find Data Row (Difference, Tax, Total)
                # We search from bottom up as totals are usually at the bottom
                for r in range(rows - 1, 0, -1):
                    row_label = str(cells[r][0]).upper() if len(cells[r]) > 0 else ""
                    if 'DIFFERENCE' in row_label or 'TAX' in row_label or 'TOTAL' in row_label:
                        # Found a candidate row
                        # Extract values based on header map
                        for act, col_idx in header_map.items():
                            # Reconstruct address (e.g., B4)
                            col_label = ""
                            temp = col_idx
                            while temp >= 0:
                                col_label = chr(ord('A') + (temp % 26)) + col_label
                                temp = (temp // 26) - 1
                            addr = f"{col_label}{r+1}"
                            
                            val = get_v(addr)
                            if val > 0:
                                if act not in breakdown:
                                    breakdown[act] = {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
                                breakdown[act]['tax'] = val
                        
                        if breakdown:
                            return breakdown
            except Exception as e:
                print(f"Smart Tax Detection Error: {e}")

        # 3. Fallback to mapped totals (Legacy)
        # If we only have total tax, we don't know the Act.
        # We default to IGST to ensure it appears in the table.
        tax = get_v(self.tax_mapping.get('tax', 'calculated_tax'))
        interest = get_v(self.tax_mapping.get('interest', 'calculated_interest'))
        penalty = get_v(self.tax_mapping.get('penalty', 'calculated_penalty'))
        
        if tax or interest or penalty:
            breakdown['IGST'] = {'tax': tax, 'interest': interest, 'penalty': penalty}
            
        return breakdown
