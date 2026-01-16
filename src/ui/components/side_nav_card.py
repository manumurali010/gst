from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class SideNavCard(QWidget):
    clicked = pyqtSignal(int)
    
    def __init__(self, index, icon, title, parent=None):
        super().__init__(parent)
        self.index = index
        self.is_active = False
        
        self.setObjectName("NavCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(75)
        
        # Main container for styling (since QWidget styling is limited without paintEvent)
        self.frame = QFrame(self)
        self.frame.setObjectName("NavFrame")
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.frame)
        
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 18px;")
        h_layout.addWidget(self.icon_lbl)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 13px; background: transparent;")
        h_layout.addWidget(self.title_lbl)
        h_layout.addStretch()
        layout.addLayout(h_layout)
        
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500; background: transparent;")
        layout.addWidget(self.summary_lbl)
        
        self.update_style()

    def set_active(self, active):
        if not self.isEnabled(): return
        self.is_active = active
        self.update_style()

    def set_enabled(self, enabled: bool):
        """Canonical method for enabling/disabling nav card"""
        self.setEnabled(enabled)
        self.update_style()
        if not enabled:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_enabled(self) -> bool:
        """Canonical method for checking enabled state"""
        return self.isEnabled()

    def update_style(self):
        if not self.isEnabled():
            # Disabled state
            self.frame.setStyleSheet("""
                #NavFrame { 
                    background-color: #f8fafc; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 8px; 
                }
            """)
            self.title_lbl.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 13px; background: transparent;")
            self.icon_lbl.setStyleSheet("font-size: 18px; opacity: 0.5;")
            self.summary_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 500; background: transparent;")
        elif self.is_active:
            # Active state
            self.frame.setStyleSheet("""
                #NavFrame { 
                    background-color: #eff6ff; 
                    border: 1px solid #3b82f6; 
                    border-left: 4px solid #3b82f6;
                    border-radius: 8px; 
                }
            """)
            self.title_lbl.setStyleSheet("font-weight: 700; color: #2563eb; font-size: 13px; background: transparent;")
            self.summary_lbl.setStyleSheet("color: #60a5fa; font-size: 11px; font-weight: 500; background: transparent;")
        else:
            # Normal/Inactive state
            self.frame.setStyleSheet("""
                #NavFrame { 
                    background-color: white; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 8px; 
                }
                #NavFrame:hover { background-color: #f8fafc; border-color: #cbd5e1; }
            """)
            self.title_lbl.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 13px; background: transparent;")
            self.summary_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500; background: transparent;")

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.clicked.emit(self.index)
        super().mousePressEvent(event)
        
    def set_summary(self, text):
        self.summary_lbl.setText(text)
