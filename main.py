import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

# Fix for WebEngine OpenGL Context/GPU crashes
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-d3d11 --no-sandbox --disable-software-rasterizer --disable-gpu-compositing"
os.environ["QT_OPENGL"] = "software" # Force Qt to use software rendering
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView 
except ImportError:
    pass
from src.ui.main_window import MainWindow

def main():
    try:
        print("Starting application...")
        app = QApplication(sys.argv)
        print("QApplication initialized")
        
        # Ensure directories exist
        if not os.path.exists('data'):
            os.makedirs('data')
        if not os.path.exists('output'):
            os.makedirs('output')
            
        print("Initializing MainWindow...")
        window = MainWindow()
        print("MainWindow initialized")
        window.show()
        print("Window shown, entering event loop")
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...") # Keep window open if run from cmd

if __name__ == "__main__":
    main()
