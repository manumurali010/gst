from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from src.ui.styles import Theme

class SideNavCard(QFrame):
    clicked = pyqtSignal(int)
    
    def __init__(self, index, icon, title, parent=None):
        super().__init__(parent)
        self.index = index
        self.icon_char = icon
        self.title_text = title
        self.is_active = False
        self.is_enabled_flag = True
        
        # Setup Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 8, 0, 8) # Compact vertical padding
        self.layout.setSpacing(12)
        
        # Left Border Indicator (Active State)
        self.indicator = QFrame()
        self.indicator.setFixedWidth(4)
        self.indicator.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(self.indicator)
        
        # Icon / Number Bubble
        self.icon_lbl = QLabel(str(icon))
        self.icon_lbl.setFixedSize(24, 24)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(f"""
            background-color: {Theme.NEUTRAL_200}; 
            color: {Theme.NEUTRAL_500}; 
            border-radius: 12px; 
            font-size: 10pt; font-weight: bold;
        """)
        self.layout.addWidget(self.icon_lbl)
        
        # Text Column (Title + Summary)
        text_col = QFrame()
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # Title
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"font-size: {Theme.FONT_BODY}; color: {Theme.NEUTRAL_900}; font-weight: {Theme.WEIGHT_REGULAR}; border: none;")
        text_layout.addWidget(self.title_lbl)
        
        # Summary (Metadata)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet(f"font-size: {Theme.FONT_META}; color: {Theme.NEUTRAL_500}; border: none;")
        self.summary_lbl.hide() # Hidden by default
        text_layout.addWidget(self.summary_lbl)
        
        self.layout.addWidget(text_col, stretch=1)
        
        # Helper to set cursor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Initial State
        self.update_appearance()

    def set_summary(self, text):
        """Sets the summary text (e.g., '5 issues identified')."""
        self.summary_lbl.setText(text)
        if text:
            self.summary_lbl.show()
        else:
            self.summary_lbl.hide()

    def set_active(self, active):
        self.is_active = active
        self.update_appearance()

    def set_completed(self, completed):
        """Visual cue for completed step."""
        if completed:
            self.icon_lbl.setText("✓") # Checkmark
            self.icon_lbl.setStyleSheet(f"background-color: {Theme.SUCCESS}; color: white; border-radius: 12px;")
            self.title_lbl.setStyleSheet(f"color: {Theme.NEUTRAL_500}; text-decoration: none; border: none;") 
        else:
            self.icon_lbl.setText(str(self.icon_char))
            self.update_appearance()

    def update_style(self):
        """Backward compatibility alias."""
        self.update_appearance()

    def update_appearance(self):
        """Unified style update."""
        if not self.is_enabled_flag:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.setStyleSheet("background-color: transparent;")
            self.icon_lbl.setStyleSheet(f"background-color: {Theme.NEUTRAL_100}; color: {Theme.NEUTRAL_200}; border-radius: 12px;")
            self.title_lbl.setStyleSheet(f"color: {Theme.NEUTRAL_200}; font-weight: {Theme.WEIGHT_REGULAR};")
            return

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if self.is_active:
            self.setStyleSheet(f"background-color: {Theme.NEUTRAL_100};")
            self.indicator.setStyleSheet(f"background-color: {Theme.PRIMARY};")
            self.title_lbl.setStyleSheet(f"font-size: {Theme.FONT_BODY}; color: {Theme.PRIMARY}; font-weight: {Theme.WEIGHT_SEMIBOLD}; border: none;")
            self.icon_lbl.setStyleSheet(f"background-color: {Theme.PRIMARY}; color: {Theme.SURFACE}; border-radius: 12px;")
        else:
            self.setStyleSheet("background-color: transparent;")
            self.indicator.setStyleSheet("background-color: transparent;")
            self.title_lbl.setStyleSheet(f"font-size: {Theme.FONT_BODY}; color: {Theme.NEUTRAL_900}; font-weight: {Theme.WEIGHT_REGULAR}; border: none;")
            self.icon_lbl.setStyleSheet(f"background-color: {Theme.NEUTRAL_200}; color: {Theme.NEUTRAL_500}; border-radius: 12px;")

    def is_enabled(self):
        return self.is_enabled_flag
        
    def set_enabled(self, enabled):
        self.is_enabled_flag = enabled
        self.update_appearance()

    # [COMPATIBILITY] Proxy methods for QAbstractButton interface
    def setChecked(self, checked):
        """Proxy for set_active to match QPushButton interface"""
        self.set_active(checked)

    def isChecked(self):
        """Proxy for is_active"""
        return self.is_active

    def mousePressEvent(self, event):
        if self.is_enabled_flag:
            self.clicked.emit(self.index)
