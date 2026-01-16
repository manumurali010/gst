from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
                             QPushButton, QFontComboBox, QSpinBox, QTextEdit, QColorDialog)
from PyQt6.QtGui import QTextCharFormat, QFont, QColor, QTextCursor, QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal


class RichTextEditor(QWidget):
    """
    A rich text editor widget with formatting toolbar.
    Provides Word-like formatting capabilities for document drafting.
    """
    
    textChanged = pyqtSignal()  # Signal emitted when text changes
    
    def __init__(self, placeholder="Enter text here...", parent=None):
        super().__init__(parent)
        self.init_ui(placeholder)
    
    def init_ui(self, placeholder):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Create text editor first (needed by toolbar)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(placeholder)
        self.editor.setAcceptRichText(True)
        
        # Create toolbar (references self.editor)
        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)
        
        # Add editor to layout
        self.editor.textChanged.connect(self.textChanged.emit)
        layout.addWidget(self.editor)
    
    def create_toolbar(self):
        """Create the formatting toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                spacing: 2px;
            }
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                background-color: white;
                color: black; /* Ensure text is black */
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #d0d0d0;
                border: 1px solid #a0a0a0;
            }
        """)
        
        # Font family
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Bookman Old Style"))
        self.font_combo.currentFontChanged.connect(self.change_font)
        self.font_combo.setMaximumWidth(150)
        toolbar.addWidget(self.font_combo)
        
        toolbar.addSeparator()
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setValue(11)
        self.font_size.setRange(8, 72)
        self.font_size.setSuffix(" pt")
        self.font_size.valueChanged.connect(self.change_font_size)
        self.font_size.setMaximumWidth(80)
        toolbar.addWidget(self.font_size)
        
        toolbar.addSeparator()
        
        # Bold
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.bold_btn.clicked.connect(self.toggle_bold)
        toolbar.addWidget(self.bold_btn)
        
        # Italic
        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        italic_font = QFont("Arial", 10)
        italic_font.setItalic(True)
        self.italic_btn.setFont(italic_font)
        self.italic_btn.clicked.connect(self.toggle_italic)
        toolbar.addWidget(self.italic_btn)
        
        # Underline
        self.underline_btn = QPushButton("U")
        self.underline_btn.setCheckable(True)
        underline_font = QFont("Arial", 10)
        underline_font.setUnderline(True)
        self.underline_btn.setFont(underline_font)
        self.underline_btn.clicked.connect(self.toggle_underline)
        toolbar.addWidget(self.underline_btn)
        
        toolbar.addSeparator()
        
        # Text color
        color_btn = QPushButton("A")
        color_btn.setToolTip("Text Color")
        color_btn.clicked.connect(self.change_text_color)
        toolbar.addWidget(color_btn)
        
        # Background color
        bg_color_btn = QPushButton("⬛")
        bg_color_btn.setToolTip("Background Color")
        bg_color_btn.clicked.connect(self.change_bg_color)
        toolbar.addWidget(bg_color_btn)
        
        toolbar.addSeparator()
        
        # Alignment
        align_left_btn = QPushButton("≡")
        align_left_btn.setToolTip("Align Left")
        align_left_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        toolbar.addWidget(align_left_btn)
        
        align_center_btn = QPushButton("≡")
        align_center_btn.setToolTip("Align Center")
        align_center_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        toolbar.addWidget(align_center_btn)
        
        align_right_btn = QPushButton("≡")
        align_right_btn.setToolTip("Align Right")
        align_right_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        toolbar.addWidget(align_right_btn)
        
        align_justify_btn = QPushButton("≡")
        align_justify_btn.setToolTip("Justify")
        align_justify_btn.clicked.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify))
        toolbar.addWidget(align_justify_btn)
        
        toolbar.addSeparator()
        
        # Lists
        bullet_btn = QPushButton("•")
        bullet_btn.setToolTip("Bullet List")
        bullet_btn.clicked.connect(self.insert_bullet_list)
        toolbar.addWidget(bullet_btn)
        
        number_btn = QPushButton("1.")
        number_btn.setToolTip("Numbered List")
        number_btn.clicked.connect(self.insert_numbered_list)
        toolbar.addWidget(number_btn)
        
        toolbar.addSeparator()
        
        # Undo/Redo
        undo_btn = QPushButton("↶")
        undo_btn.setToolTip("Undo")
        undo_btn.clicked.connect(self.editor.undo)
        toolbar.addWidget(undo_btn)
        
        redo_btn = QPushButton("↷")
        redo_btn.setToolTip("Redo")
        redo_btn.clicked.connect(self.editor.redo)
        toolbar.addWidget(redo_btn)
        
        return toolbar
    
    def toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_btn.isChecked() else QFont.Weight.Normal)
        self.merge_format(fmt)
    
    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self.merge_format(fmt)
    
    def toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_btn.isChecked())
        self.merge_format(fmt)
    
    def change_font(self, font):
        fmt = QTextCharFormat()
        fmt.setFont(font)
        self.merge_format(fmt)
    
    def change_font_size(self, size):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.merge_format(fmt)
    
    def change_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self.merge_format(fmt)
    
    def change_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self.merge_format(fmt)
    
    def set_alignment(self, alignment):
        self.editor.setAlignment(alignment)
    
    def insert_bullet_list(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextCursor.ListStyle.ListDisc)
    
    def insert_numbered_list(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextCursor.ListStyle.ListDecimal)
    
    def merge_format(self, fmt):
        """Apply format to current selection or cursor position"""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
    
    # Public API methods
    def toHtml(self):
        """Get HTML content"""
        return self.editor.toHtml()
    
    def toPlainText(self):
        """Get plain text content"""
        return self.editor.toPlainText()
    
    def setText(self, text):
        """Set plain text content"""
        self.editor.setText(text)
    
    def setHtml(self, html):
        """Set HTML content"""
        self.editor.setHtml(html)
    
    def setPlaceholderText(self, text):
        """Set placeholder text"""
        self.editor.setPlaceholderText(text)
    
    def setMinimumHeight(self, height):
        """Set minimum height"""
        self.editor.setMinimumHeight(height)
    
    def clear(self):
        """Clear content"""
        self.editor.clear()

    def insertHtml(self, html):
        """Insert HTML at current cursor position"""
        cursor = self.editor.textCursor()
        cursor.insertHtml(html)
        
    def setFocus(self):
        """Set focus to the editor"""
        self.editor.setFocus()

    def set_read_only(self, read_only: bool):
        """Delegate read-only state to the internal text editor."""
        self.editor.setReadOnly(read_only)
        # Also disable toolbar to prevent formatting even if read-only
        if hasattr(self, 'toolbar'):
             self.toolbar.setEnabled(not read_only)
