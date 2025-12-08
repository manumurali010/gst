from PyQt6.QtWidgets import QApplication
import sys
from src.ui.proceedings_workspace import ProceedingsWorkspace
from src.ui.components.modern_card import ModernCard

def verify_ui():
    app = QApplication(sys.argv)
    
    try:
        # Initialize Workspace
        workspace = ProceedingsWorkspace(lambda x: None)
        print("ProceedingsWorkspace initialized successfully.")
        
        # Check if ModernCard is used
        found_card = False
        for child in workspace.findChildren(ModernCard):
            print(f"Found ModernCard: {child.title_label.text() if hasattr(child, 'title_label') else 'Untitled'}")
            found_card = True
            
        if found_card:
            print("SUCCESS: ModernCard widgets are present in the UI.")
        else:
            print("WARNING: No ModernCard widgets found (might be inside stacked widget).")
            
    except Exception as e:
        print(f"FAILED: Error initializing UI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ui()
