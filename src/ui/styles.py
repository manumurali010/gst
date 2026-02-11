class Theme:
    # --- Colors ---
    # Primary Palette (Blue)
    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_PRESSED = "#1E40AF"
    
    # Danger Palette (Red)
    DANGER = "#DC2626"
    DANGER_HOVER = "#B91C1C"
    DANGER_PRESSED = "#991B1B"
    
    # Neutral Palette (Gray/Slate)
    NEUTRAL_900 = "#111827"  # Main Text
    NEUTRAL_500 = "#6B7280"  # Muted/Metadata
    NEUTRAL_200 = "#E5E7EB"  # Borders
    NEUTRAL_100 = "#F3F4F6"  # Backgrounds/Hovers
    
    # Surface
    SURFACE = "#FFFFFF"
    
    # --- Typography ---
    FONT_FAMILY = "'Segoe UI', 'Roboto', sans-serif"
    
    # Scale (Size / Weight)
    FONT_PAGE = "22px"      # Weight 600
    FONT_SECTION = "18px"   # Weight 600
    FONT_CARD = "16px"      # Weight 600
    FONT_BODY = "14px"      # Weight 400
    FONT_META = "13px"      # Weight 400
    
    WEIGHT_REGULAR = "400"
    WEIGHT_SEMIBOLD = "600"
    
    # --- Layout & Spacing ---
    # Base Unit: 8px
    SPACE_MICRO = "4px"     # Icons/Gaps only
    SPACE_SM = "8px"
    SPACE_MD = "16px"
    SPACE_LG = "24px"
    SPACE_XL = "32px"
    SPACE_2XL = "40px"
    
    RADIUS_MD = "8px"
    RADIUS_SM = "4px" # For inputs/small elements
    
    # --- Interaction ---
    TRANSITION = "0.15s ease-in-out" # Note: QSS support for transitions is limited to specific widgets/properties
    FOCUS_RING = f"2px solid {PRIMARY}"

    # --- Backward Compatibility Layer (Legacy Token Mapping) ---
    # Maps old variable names to new design tokens to prevent AttributeErrors
    SECONDARY = PRIMARY           # Old "Bright Blue" -> New Primary
    ACCENT = PRIMARY              # Old Teal -> New Primary
    
    SUCCESS = "#10B981"           # Emerald 500
    SUCCESS_HOVER = "#059669"     # Emerald 600
    SUCCESS_PRESSED = "#047857"   # Emerald 700
    
    WARNING = "#F59E0B"           # Amber 500
    
    BACKGROUND = NEUTRAL_100      # Old Light Blue-Gray -> New Neutral 100
    
    TEXT_PRIMARY = NEUTRAL_900    # Old Dark Slate -> New Neutral 900
    TEXT_SECONDARY = NEUTRAL_500  # Old Gray -> New Neutral 500
    TEXT_LIGHT = SURFACE          # Old Light Gray/White -> Surface
    
    BORDER = NEUTRAL_200          # Old Light Gray -> New Neutral 200

class Styles:
    @staticmethod
    def get_main_stylesheet():
        return f"""
            QMainWindow {{
                background-color: {Theme.NEUTRAL_100};
            }}
            QWidget {{
                font-family: {Theme.FONT_FAMILY};
                font-size: {Theme.FONT_BODY};
                color: {Theme.NEUTRAL_900};
            }}
            
            /* --- Buttons (Base Styles) --- */
            QPushButton {{
                border-radius: {Theme.RADIUS_MD};
                padding: {Theme.SPACE_SM} {Theme.SPACE_MD};
                font-weight: {Theme.WEIGHT_SEMIBOLD};
                border: none;
                outline: none;
            }}
            QPushButton:focus {{
                border: {Theme.FOCUS_RING};
            }}
            QPushButton:disabled {{
                opacity: 0.6;
                background-color: {Theme.NEUTRAL_200};
                color: {Theme.NEUTRAL_500};
            }}
            
            /* --- Inputs --- */
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.NEUTRAL_200};
                border-radius: {Theme.RADIUS_SM};
                padding: 6px; /* Micro adjustment for input height alignment */
                selection-background-color: {Theme.PRIMARY};
                color: {Theme.NEUTRAL_900};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: {Theme.FOCUS_RING};
            }}
            
            /* --- Lists/Tables --- */
            QListWidget, QTableWidget {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.NEUTRAL_200};
                border-radius: {Theme.RADIUS_MD};
                outline: none;
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: {Theme.NEUTRAL_100};
                color: {Theme.PRIMARY};
                border-left: 4px solid {Theme.PRIMARY}; 
            }}
            QHeaderView::section {{
                background-color: {Theme.NEUTRAL_100};
                color: {Theme.NEUTRAL_900};
                font-weight: {Theme.WEIGHT_SEMIBOLD};
                padding: {Theme.SPACE_SM};
                border: none;
                border-bottom: 1px solid {Theme.NEUTRAL_200};
            }}
            
            /* --- Scrollbars --- */
            QScrollBar:vertical {{
                border: none;
                background: {Theme.NEUTRAL_100};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.NEUTRAL_200};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.NEUTRAL_500};
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
                border-radius: {Theme.RADIUS_MD};
                border: 1px solid {Theme.NEUTRAL_200};
            }}
        """
