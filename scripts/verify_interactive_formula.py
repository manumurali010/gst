import sys
from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QLineEdit
from PyQt6.QtCore import Qt, QEvent, QPoint
from PyQt6.QtTest import QTest
from src.ui.developer.table_builder import TableBuilderWidget

def verify_interactive_formula():
    app = QApplication(sys.argv)
    
    widget = TableBuilderWidget()
    widget.resize(600, 400)
    widget.show()
    
    # Setup table
    table = widget.table
    table.setItem(0, 0, QTableWidgetItem("")) # Target
    table.setItem(0, 1, QTableWidgetItem("10")) # Source (B1)
    
    # Start editing (0,0)
    table.setCurrentCell(0, 0)
    table.editItem(table.item(0, 0))
    
    # Find the active editor
    editor = None
    for child in table.findChildren(QLineEdit):
        if child.isVisible():
            editor = child
            break
            
    if not editor:
        print("FAIL: Could not find active editor")
        return
        
    # Type "="
    editor.setText("=")
    
    # Simulate Click on (0, 1) -> B1
    # We need to calculate the position of cell (0, 1)
    rect = table.visualRect(table.model().index(0, 1))
    center = rect.center()
    
    print(f"Clicking at {center} for cell B1")
    
    # We need to send the event to the viewport, just like a real click
    # QTest.mouseClick sends to the widget.
    # But our event filter is on the viewport.
    
    # Let's manually construct the event and send it to the viewport
    # to test if the event filter intercepts it.
    
    # Note: QTest.mouseClick might bypass event filters if not careful, 
    # but usually it goes through the event loop.
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
    
    # Check result
    text = editor.text()
    print(f"Editor Text: '{text}'")
    
    if text == "=B1":
        print("PASS: Formula updated correctly to '=B1'")
    else:
        print(f"FAIL: Expected '=B1', got '{text}'")
        
    # Check if we are still editing (editor should still be visible)
    if editor.isVisible():
        print("PASS: Still in editing mode")
    else:
        print("FAIL: Editing mode ended prematurely")

    # app.exec() # Don't block

if __name__ == "__main__":
    verify_interactive_formula()
