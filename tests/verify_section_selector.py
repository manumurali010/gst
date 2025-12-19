import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt6.QtWidgets import QApplication
from src.ui.components.section_selector import SectionSelectorDialog
from src.database.db_manager import DatabaseManager

# Initialize simplified mock DB if real one fails or is complex to setup in isolation
# but here we can try using the real one since it relies on sqlite file

def main():
    app = QApplication(sys.argv)
    
    # Ensure DB is init
    db = DatabaseManager()
    
    dialog = SectionSelectorDialog()
    if dialog.exec():
        print("Dialog Accepted")
        selected = dialog.get_selected_sections()
        print(f"Selected {len(selected)} sections:")
        for s in selected:
            print(f"- {s['title']}")
    else:
        print("Dialog Rejected")

if __name__ == "__main__":
    main()
