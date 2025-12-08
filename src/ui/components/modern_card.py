from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QPushButton, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QIcon

class ModernCard(QFrame):
    """
    A modern, card-like container with rounded corners, white background,
    and optional shadow/header. Supports collapsibility.
    """
    def __init__(self, title=None, parent=None, collapsible=True):
        super().__init__(parent)
        self.setObjectName("ModernCard")
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header Container
        self.header_frame = QFrame()
        self.header_frame.setObjectName("CardHeader")
        # Make header clickable if collapsible
        if collapsible:
            self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            self.header_frame.mousePressEvent = self.header_clicked
            
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(20, 15, 20, 15)
        self.header_layout.setSpacing(10)
        
        # Toggle Button (Arrow)
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setObjectName("CardToggle")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.clicked.connect(self.toggle_content)
        self.toggle_btn.setStyleSheet("""
            QPushButton#CardToggle {
                border: none;
                background: transparent;
                font-weight: bold;
                color: #7f8c8d;
            }
            QPushButton#CardToggle:hover {
                color: #2c3e50;
            }
        """)
        
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            self.header_layout.addWidget(self.title_label)
            self.header_layout.addStretch()
            
            if collapsible:
                self.header_layout.addWidget(self.toggle_btn)
                
        self.main_layout.addWidget(self.header_frame)
        
        # Divider line
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Plain)
        self.line.setObjectName("CardDivider")
        self.main_layout.addWidget(self.line)
            
        # Content Container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        self.main_layout.addWidget(self.content_widget)
        
        # Styling
        self.setStyleSheet("""
            #ModernCard {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            #CardTitle {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
            #CardDivider {
                color: #f0f0f0;
            }
        """)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)
        
    def header_clicked(self, event):
        """Handle click on header frame"""
        self.toggle_btn.click() # Trigger the button click
        
    def toggle_content(self):
        checked = self.toggle_btn.isChecked()
        self.toggle_btn.setText("▼" if checked else "▶")
        self.content_widget.setVisible(checked)
        self.line.setVisible(checked)
