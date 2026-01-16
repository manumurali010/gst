
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    print("WebEngine Available")
except ImportError as e:
    print(f"WebEngine Not Available: {e}")
