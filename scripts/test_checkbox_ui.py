import sys
from PyQt6.QtWidgets import QApplication
from src.ui.adjudication_wizard import AdjudicationWizard

app = QApplication(sys.argv)

def mock_navigate(page, pid=None):
    pass

wizard = AdjudicationWizard(mock_navigate)

# Check if checkbox exists and is visible
print(f"Checkbox exists: {hasattr(wizard, 'show_letterhead_cb')}")
if hasattr(wizard, 'show_letterhead_cb'):
    print(f"Checkbox parent: {wizard.show_letterhead_cb.parent()}")
    print(f"Checkbox visible: {wizard.show_letterhead_cb.isVisible()}")
    print(f"Checkbox text: {wizard.show_letterhead_cb.text()}")
    print(f"Checkbox geometry: {wizard.show_letterhead_cb.geometry()}")
    
    # Check parent widget
    parent = wizard.show_letterhead_cb.parent()
    if parent:
        print(f"Parent visible: {parent.isVisible()}")
        print(f"Parent geometry: {parent.geometry()}")

# Show the wizard
wizard.show()
wizard.resize(1400, 800)

print("\nAfter showing wizard:")
print(f"Checkbox visible: {wizard.show_letterhead_cb.isVisible()}")
print(f"Checkbox geometry: {wizard.show_letterhead_cb.geometry()}")

sys.exit(app.exec())
