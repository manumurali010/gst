import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.ui.main_window import MainWindow
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    try:
        app = QApplication(sys.argv)
        print("Initializing MainWindow...")
        window = MainWindow()
        print("MainWindow initialized successfully")
        # Don't show, just init to test
        sys.exit(0)
    except Exception as e:
        print(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
