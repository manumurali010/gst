from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.utils.formatting import format_indian_number

def render_grid_to_table_widget(table_widget: QTableWidget, grid_data: dict, interactive: bool = False) -> dict:
    """
    Renders a unified dictionary-based grid_data into a QTableWidget.
    
    Args:
        table_widget: The QTableWidget instance to populate.
        grid_data: The canonical grid dictionary with keys "columns" and "rows".
        interactive: If True, stores cell metadata in UserRole and returns widget map.
        
    Returns:
        dict: valid variable map {var_name: QTableWidgetItem} if interactive, else {}.
    """
    cell_widgets = {}

    # Defensive checks (Contract Enforcement)
    if not isinstance(grid_data, dict):
        return {}

    columns = grid_data.get("columns", [])
    rows = grid_data.get("rows", [])
    
    # [ROBUSTNESS] Infer columns from rows if missing (Direct Pass-Through support)
    if not columns and rows:
        max_cols = 0
        inferred_headers = []
        
        # Scan first few rows to guess structure
        sample_row = rows[0]
        if isinstance(sample_row, dict):
            inferred_headers = list(sample_row.keys())
        elif isinstance(sample_row, list):
            max_cols = max(len(r) for r in rows if isinstance(r, list))
            inferred_headers = [f"Col {i+1}" for i in range(max_cols)]
            
        # Reconstruct canonical columns
        columns = [{"id": h if isinstance(sample_row, dict) else f"col{i}", "label": str(h)} 
                   for i, h in enumerate(inferred_headers)]

    if not columns and not rows:
        table_widget.setRowCount(0)
        table_widget.setColumnCount(0)
        return {}

    # Extract Headers and IDs
    col_labels = []
    col_ids = []
    
    for i, h in enumerate(columns):
        if isinstance(h, dict):
            lbl = h.get('label') or h.get('value', '')
            cid = h.get('id') or f"col{i}"
            col_labels.append(lbl)
            col_ids.append(cid)
        else:
            col_labels.append(str(h))
            col_ids.append(f"col{i}")

    # Setup Table Config
    table_widget.setColumnCount(len(col_labels))
    table_widget.setRowCount(len(rows))
    table_widget.setHorizontalHeaderLabels(col_labels)
    table_widget.verticalHeader().setVisible(False)
    
    # Standard styling
    header = table_widget.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    # [Polish] Header Styling
    header.setStyleSheet("""
        QHeaderView::section {
            background-color: #f1f5f9;
            color: #1e293b;
            font-weight: bold;
            border: 1px solid #e2e8f0;
            padding: 4px;
        }
    """)
    table_widget.setStyleSheet("""
        QTableWidget {
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            gridline-color: #e2e8f0;
        }
        QTableWidget::item {
            padding: 4px;
            border-bottom: 1px solid #f1f5f9;
        }
    """)
    
    # Populate Rows
    # Populate Rows
    for r, row_data in enumerate(rows):
        # [ROBUSTNESS] Support both Dict and List rows (ASMT-10 Direct Pass-Through)
        if not isinstance(row_data, (dict, list)):
            print(f"RENDER ERROR: Row {r} must be dict or list, got {type(row_data)}")
            continue

        for c, col_id in enumerate(col_ids):
            # Fetch cell logic (Dict vs List)
            cell = {}
            if isinstance(row_data, dict):
                 cell = row_data.get(col_id, {})
            elif isinstance(row_data, list):
                 if c < len(row_data):
                     cell = row_data[c]
            
            # Normalize Cell to Dict or extract value
            if isinstance(cell, dict):
                # [ROBUSTNESS] Try multiple known keys or fallback to first value
                val = cell.get('value')
                if val is None: val = cell.get('amount')
                if val is None: val = cell.get('label')
                # If still None, maybe it's {key:val}? Try implicit value
                if val is None and len(cell) == 1:
                     val = list(cell.values())[0]
                if val is None: val = '' # Final fallback to empty string (not None)

                style = cell.get('style', 'normal')
                var_name = cell.get('var')
                ctype = cell.get('type', 'static')
            else:
                # Handle primitive values (str, int, float) from raw lists
                val = cell
                style = 'normal'
                var_name = None
                ctype = 'static'
            
            # Format Value
            val_str = str(val)
            try:
                if isinstance(val, (int, float)):
                   # Format to Indian Numbering without currency symbol
                   val_str = format_indian_number(val, prefix_rs=False)
            except:
                pass
            
            item = QTableWidgetItem(val_str)
            
            # Store metadata if interactive
            if interactive:
                item.setData(Qt.ItemDataRole.UserRole, cell)
                if var_name:
                    cell_widgets[var_name] = item

            # Alignment
            # Use format_indian_number result check (contains commas, or 0)
            if isinstance(val, (int, float)) or val_str == "0":
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Styling & Editability
            if style == 'bold' or style == 'red_bold':
                f = table_widget.font()
                f.setBold(True)
                item.setFont(f)
            
            if style == 'red_bold':
                item.setForeground(Qt.GlobalColor.red)
                
            # Interactivity flags
            if interactive:
                if ctype == 'static':
                     item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                     item.setBackground(Qt.GlobalColor.lightGray)
                elif ctype == 'formula':
                     item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                     item.setForeground(Qt.GlobalColor.blue)
                # else input, default editable
                
            table_widget.setItem(r, c, item)

    # Resize rows
    table_widget.resizeRowsToContents()
    
    return cell_widgets
