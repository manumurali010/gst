from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QSplitter, QFrame, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat
import json
from src.ui.developer.logic_validator import LogicValidator

class LogicLab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info Header
        info_lbl = QLabel("Logic Lab: Define and test Python calculation logic safely.")
        info_lbl.setStyleSheet("color: #7f8c8d; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(info_lbl)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT: Editor ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,10,0)
        
        l_lbl = QLabel("Python Logic Definition:")
        l_lbl.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(l_lbl)
        
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setPlaceholderText("def compute(v):\n    # Your logic here...")
        self.code_editor.setText(LogicValidator.get_default_logic_template())
        left_layout.addWidget(self.code_editor)
        
        splitter.addWidget(left_widget)
        
        # --- RIGHT: Test & Output ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10,0,0,0)
        
        # Test Inputs
        i_lbl = QLabel("Test Inputs (JSON):")
        i_lbl.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(i_lbl)
        
        self.input_editor = QTextEdit()
        self.input_editor.setFont(QFont("Consolas", 10))
        self.input_editor.setPlaceholderText('{"taxable_value": 1000}')
        self.input_editor.setText('{\n    "taxable_value": 50000,\n    "tax_rate": 18\n}')
        self.input_editor.setMaximumHeight(150)
        right_layout.addWidget(self.input_editor)
        
        # Run Button
        self.run_btn = QPushButton("▶ Run & Validate")
        self.run_btn.setStyleSheet("""
            background-color: #27ae60; color: white; 
            padding: 10px; font-weight: bold; font-size: 14px;
            border-radius: 4px;
        """)
        self.run_btn.clicked.connect(self.run_validation)
        right_layout.addWidget(self.run_btn)
        
        # Output
        o_lbl = QLabel("Output Result:")
        o_lbl.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(o_lbl)
        
        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setFont(QFont("Consolas", 10))
        self.output_console.setStyleSheet("background-color: #2c3e50; color: #ecf0f1;")
        right_layout.addWidget(self.output_console)
        
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)

    def run_validation(self):
        self.output_console.clear()
        
        # 1. Parse Input
        try:
            inputs = json.loads(self.input_editor.toPlainText())
        except json.JSONDecodeError as e:
            self.output_console.setText(f"Input JSON Error:\n{str(e)}")
            return
            
        # 2. Run Logic
        code = self.code_editor.toPlainText()
        success, result = LogicValidator.validate_logic(code, inputs)
        
        if success:
            self.output_console.setTextColor(QColor("#2ecc71")) # Green
            formatted_res = json.dumps(result, indent=4)
            self.output_console.setText(f"Success:\n{formatted_res}")
        else:
            self.output_console.setTextColor(QColor("#e74c3c")) # Red
            self.output_console.setText(f"Validation Failed:\n{result}")
