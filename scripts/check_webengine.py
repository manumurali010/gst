try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
    print("QtWebEngine is available.")
except ImportError as e:
    print(f"QtWebEngine is NOT available: {e}")
except Exception as e:
    print(f"Error checking QtWebEngine: {e}")
