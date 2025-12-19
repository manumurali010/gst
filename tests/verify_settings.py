
import sys
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView # Fix for context error
from PyQt6.QtWidgets import QApplication

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.ui.main_window import MainWindow
from src.ui.settings_tab import SettingsTab

def test_settings_tab():
    app = QApplication(sys.argv)
    
    try:
        # 1. Test SettingsTab Initialization
        print("Testing SettingsTab Initialization...")
        tab = SettingsTab(lambda: print("Home Clicked"))
        if tab:
            print("PASS: SettingsTab initialized successfully.")
        
        # 2. Test MainWindow Integration
        print("Testing MainWindow Integration...")
        window = MainWindow()
        
        # Check if index 11 is SettingsTab
        widget_at_11 = window.stack.widget(11)
        if isinstance(widget_at_11, SettingsTab):
            print("PASS: SettingsTab found at stack index 11.")
        else:
            print(f"FAIL: Index 11 is {type(widget_at_11)}")
            return

        # Check Sidebar Button
        print("Testing Sidebar Configuration...")
        found = False
        for btn in window.sidebar.buttons:
            if btn.text_label == "Settings" and btn.index == 11:
                found = True
                break
        
        if found:
            print("PASS: Settings button found in Sidebar.")
        else:
            print("FAIL: Settings button missing from Sidebar.")
            return

        print("ALL TESTS PASSED")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_settings_tab()
