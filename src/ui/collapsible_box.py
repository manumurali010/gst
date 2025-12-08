from PyQt6.QtWidgets import QWidget, QToolButton, QVBoxLayout, QScrollArea, QSizePolicy, QFrame, QLabel
from PyQt6.QtCore import Qt, QParallelAnimationGroup, QPropertyAnimation, QAbstractAnimation

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True) # Expanded by default
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        
        self.toggle_button.setStyleSheet("""
            QToolButton {
                text-align: left; 
                font-weight: bold; 
                font-size: 14px; 
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f1f3f4);
                padding: 10px 15px;
                color: #202124;
            }
            QToolButton:hover {
                background-color: #e8f0fe;
                border: 1px solid #1a73e8;
                color: #1a73e8;
            }
            QToolButton:checked {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                border-bottom: none;
            }
        """)
        
        self.toggle_animation = QParallelAnimationGroup(self)
        self.content_area = QScrollArea()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.toggle_button.clicked.connect(self.on_pressed)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)
        
        # Correct QScrollArea usage
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0) # Let external widgets handle margins
        self.content_area.setWidget(self.content_widget)
        self.content_area.setWidgetResizable(True)
        
        # Initialize animation
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1000) # Arbitrary max height
        
    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.animation.setDirection(QAbstractAnimation.Direction.Forward if checked else QAbstractAnimation.Direction.Backward)
        self.animation.start()
        
    def setContentLayout(self, layout):
        # Deprecated/Adapted: Set layout on the internal widget
        # Note: This might fail if a layout is already set. 
        # Better to use setContentWidget if you have a full widget.
        QWidget().setLayout(self.content_widget.layout()) # Hack to unparent existing layout
        self.content_widget.setLayout(layout)

    def setContentWidget(self, widget):
        self.content_area.setWidget(widget)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)
