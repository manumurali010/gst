from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class GridAdapter:
    """
    Adapter to bridge the logic-layer 'grid_data' schema directly to QTableWidget.
    Supports:
    - Structure generation (columns/headers)
    - Data population (rows)
    - Formatting projection
    """
    
    @staticmethod
    def normalize_to_schema(data):
        """
        Normalize various grid data formats to the canonical dictionary schema:
        {
            "columns": [{"id": "col0", "label": "A"}, ...],
            "rows": [{"col0": {"value": 10}, ...}]
        }
        """
        if not data: return {"columns": [], "rows": []}
        
        print(f"[GridAdapter] Normalizing data type: {type(data)}")
        if isinstance(data, list) and len(data) > 0:
             print(f"[GridAdapter] First item type: {type(data[0])}")
             print(f"[GridAdapter] First item sample: {data[0]}")
        elif isinstance(data, dict):
             print(f"[GridAdapter] Dict keys: {list(data.keys())}")

        # Case 0: Already canonical
        # [Strict Check] Columns must be list of dicts, rows list of dicts
        if isinstance(data, dict) and "rows" in data and isinstance(data['rows'], list):
            # Check if columns is valid (list of dicts)
            cols = data.get('columns')
            if isinstance(cols, list) and len(cols) > 0 and isinstance(cols[0], dict):
                return data
            elif not cols and not data['rows']:
                return data
            # If columns exist but are NOT dicts (e.g. strings), fall through to re-normalization
            if isinstance(cols, list) and len(cols) > 0 and not isinstance(cols[0], dict):
                print("[GridAdapter] Detected pseudo-canonical data (string columns). Re-normalizing.")
                # We need to treat this as partial data. 
                # If rows are already normalized (dicts of {value:.., type:..}), we just need to fix columns?
                # Or if rows are just dicts of values?
                # The user says "columns is a list of strings instead of dicts".
                # If rows are [{'Tax': 100}], we can treat this as Case 1 (List of Dicts) by just passing 'rows'.
                return GridAdapter.normalize_to_schema(data['rows'])

            
        # Case 1: List of Dicts [{"A": 1}, {"A": 2}]
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Use keys of first item as columns
            # Order is preserved in Python 3.7+
            headers = list(data[0].keys())
            columns = []
            col_ids = []
            
            for i, h in enumerate(headers):
                cid = f"col{i}"
                columns.append({"id": cid, "label": str(h)})
                col_ids.append(cid)
            
            rows = []
            for row_dict in data:
                normalized_row = {}
                for i, h in enumerate(headers):
                    val = row_dict.get(h, "")
                    cid = col_ids[i]
                    normalized_row[cid] = {"value": val, "type": "static"}
                rows.append(normalized_row)
                
            return {"columns": columns, "rows": rows}
            
        # Case 2: List of Lists [[A, B], [1, 2]]
        if isinstance(data, list):
            rows = []
            if not data: return {"columns": [], "rows": []}
            
            # Assume row 0 is header
            headers = data[0] if len(data) > 0 else []
            columns = []
            col_ids = []
            for i, h in enumerate(headers):
                cid = f"col{i}"
                columns.append({"id": cid, "label": str(h)})
                col_ids.append(cid)
                
            # Process remaining rows
            for r_idx, row_vals in enumerate(data[1:]):
                row_dict = {}
                for c_idx, val in enumerate(row_vals):
                    if c_idx < len(col_ids):
                        row_dict[col_ids[c_idx]] = {"value": val, "type": "static"}
                rows.append(row_dict)
                
            return {"columns": columns, "rows": rows}
            
        # Fallback
        return {"columns": [], "rows": []}
    
    @staticmethod
    def render_schema(table_widget: QTableWidget, schema_raw: dict, read_only=True):
        """
        Populate QTableWidget based on grid_data schema.
        args:
            table_widget: Target widget
            schema_raw: dict/list schema
        """
        schema = GridAdapter.normalize_to_schema(schema_raw)
        
        if not schema or not isinstance(schema, dict):
            table_widget.setRowCount(0)
            table_widget.setColumnCount(0)
            return

        cols = schema.get("columns", [])
        rows = schema.get("rows", [])

        # 1. Setup Columns
        table_widget.setColumnCount(len(cols))
        headers = []
        for c in cols:
            label = c.get("label", "") if isinstance(c, dict) else str(c)
            headers.append(label)
        table_widget.setHorizontalHeaderLabels(headers)
        
        # 2. Setup Rows
        table_widget.setRowCount(len(rows))
        
        # 3. Populate
        col_ids = [c.get("id", f"col{i}") if isinstance(c, dict) else f"col{i}" for i, c in enumerate(cols)]
        
        for r_idx, row_data in enumerate(rows):
            for c_idx, col_id in enumerate(col_ids):
                # Safe access
                cell = row_data.get(col_id, {})
                val = cell.get("value", "")
                
                # Check for formula placeholders
                if isinstance(val, str) and val.startswith("{{") and val.endswith("}}"):
                    # Render as placebo
                    display_val = val
                    bg_color = QColor("#e8f4f8") # Light blue for formula
                else:
                    display_val = str(val)
                    bg_color = QColor("white")
                    
                item = QTableWidgetItem(display_val)
                item.setBackground(bg_color)
                
                # Style override from schema
                style = cell.get("style", "normal")
                if style == "bold":
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                
                # Read-only enforcement
                if read_only:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    
                table_widget.setItem(r_idx, c_idx, item)
                
        # 4. Polish
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_widget.verticalHeader().setVisible(False)
        table_widget.setAlternatingRowColors(True)
