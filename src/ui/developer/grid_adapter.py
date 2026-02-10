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
            # If columns exist but are NOT dicts (e.g. strings), FAIL FAST
            if isinstance(cols, list) and len(cols) > 0 and not isinstance(cols[0], dict):
                # [USER REQUEST] GridAdapter must not "fix" string columns -- it should reject them.
                # This ensures upstream sources (like SCN conversion) MUST output canonical data.
                error_msg = "[GridAdapter] CRITICAL: Detected pseudo-canonical data (string columns). Rejected to prevent corruption."
                print(error_msg)
                raise ValueError(error_msg)

            
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

    @staticmethod
    def hydrate_from_grid_schema(grid_data):
        """
        [PHASE A] Read-Only Hydration (Hardened)
        Converts Semantic Grid Schema -> 2D Array for TableBuilder.
        
        Rules:
        1. [Fix Duplication] If 'columns' contains a description field, map it to Col 0 ONLY.
           Do not render it again in the data columns.
        2. [UX] Row 0 is Headers, Col 0 is Row Labels (Description).
        3. [Safety] Assert single description column.
        """
        if not grid_data:
            return None
            
        columns = grid_data.get('columns', [])
        rows = grid_data.get('rows', [])
        
        if not columns and not rows:
            return None
            
        # --- Rule 1: Smart Column Deduping ---
        # Identify if we have an explicit description column
        desc_col_candidates = ['desc', 'description', 'particulars', 'gstin']
        
        found_desc_col = None
        data_columns = []
        
        for col in columns:
            col_id = col.get('id', '').lower()
            if not found_desc_col and col_id in desc_col_candidates:
                found_desc_col = col
                # print(f"[GridAdapter] Found Description Column: {col_id} -> Mapping to Col 0") # Diagnostic
            else:
                data_columns.append(col)
        
        if found_desc_col:
            # Use the explicit column's label for Col 0 header
            row_label_header = found_desc_col.get('label', 'Description')
        else:
            # Fallback
            row_label_header = "(Row Label)"
            # print("[GridAdapter] No explicit description column found. Using fallback.")
            
        # 1. Prepare Header Row (Row 0)
        # Col 0 = Row Label Header
        header_row = [row_label_header] + [c.get('label', c.get('id', '')) for c in data_columns]
        
        # 2. Prepare Data Rows
        data_rows = []
        for r_dict in rows:
            # Resolve Row Label (Col 0)
            # If we found a desc column, use its ID. Otherwise try common keys.
            row_label_val = ""
            
            if found_desc_col:
                # Strict: Use the ID of the identified column
                target_id = found_desc_col.get('id')
                val = r_dict.get(target_id, "")
                if isinstance(val, dict): val = val.get('value', '')
                row_label_val = str(val or "")
            else:
                # Loose: Try to find a label
                for key in ['desc', 'description', 'label', 'id', 'particulars']:
                   if key in r_dict:
                       val = r_dict[key]
                       if isinstance(val, dict): val = val.get('value', '')
                       if val:
                           row_label_val = str(val)
                           break
            
            row_cells = [row_label_val] 
            
            # Map remaining data columns
            for col in data_columns:
                col_id = col.get('id')
                cell = r_dict.get(col_id, {})
                val = ""
                if isinstance(cell, dict):
                    val = cell.get('value', '')
                else:
                    val = str(cell)
                row_cells.append(str(val))
            
            data_rows.append(row_cells)
            
        # 3. Assemble 2D Grid
        grid_2d = {
            "rows": len(data_rows) + 1,
            "cols": len(header_row),
            "cells": [header_row] + data_rows,
            "is_semantic_view": True,
            "_meta": { 
                "type": "semantic_grid_snapshot",
                "original_desc_col": found_desc_col.get('id') if found_desc_col else None
            }
        }
        
        return grid_2d
