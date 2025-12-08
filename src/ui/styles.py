class Theme:
    # Professional Blue/Slate Palette
    PRIMARY = "#2c3e50"      # Dark Slate Blue (Header, Sidebar)
    SECONDARY = "#3498db"    # Bright Blue (Primary Actions, Active State)
    ACCENT = "#1abc9c"       # Teal (Highlights)
    
    SUCCESS = "#27ae60"      # Green
    WARNING = "#f39c12"      # Orange
    DANGER = "#c0392b"       # Red
    
    BACKGROUND = "#f5f6fa"   # Very Light Blue-Gray (App Background)
    SURFACE = "#ffffff"      # White (Cards, Content Areas)
    
    TEXT_PRIMARY = "#2c3e50" # Dark Slate
    TEXT_SECONDARY = "#7f8c8d" # Gray
    TEXT_LIGHT = "#ecf0f1"   # Light Gray/White
    
    BORDER = "#bdc3c7"       # Light Gray Border

class Styles:
    @staticmethod
    def get_main_stylesheet():
        return f"""
            QMainWindow {{
                background-color: {Theme.BACKGROUND};
            }}
            QWidget {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 14px;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            /* --- Buttons --- */
            QPushButton {{
                background-color: {Theme.SECONDARY};
                color: {Theme.TEXT_LIGHT};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2980b9; /* Darker Blue */
            }}
            QPushButton:pressed {{
                background-color: #1c5980;
            }}
            QPushButton:disabled {{
                background-color: {Theme.BORDER};
                color: {Theme.TEXT_SECONDARY};
            }}
            
            /* --- Inputs --- */
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {Theme.SECONDARY};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {Theme.SECONDARY};
            }}
            
            /* --- Lists/Tables --- */
            QListWidget, QTableWidget {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER};
                border-radius: 4px;
                outline: none;
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: {Theme.SECONDARY};
                color: {Theme.TEXT_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {Theme.PRIMARY};
                color: {Theme.TEXT_LIGHT};
                padding: 6px;
                border: none;
            }}
            
            /* --- Scrollbars --- */
            QScrollBar:vertical {{
                border: none;
                background: {Theme.BACKGROUND};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.BORDER};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    @staticmethod
    def get_card_style():
        return f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 10px;
                border: 1px solid {Theme.BORDER};
            }}
        """
