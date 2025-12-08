import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def verify_ui():
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        print("MainWindow initialized successfully.")
        print(f"Stylesheet applied: {bool(window.styleSheet())}")
        return True
    except Exception as e:
        print(f"UI Initialization Failed: {e}")
        return False

if __name__ == "__main__":
    verify_ui()
