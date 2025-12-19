import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6.QtCore import QMarginsF

app = QApplication(sys.argv)
printer = QPrinter()

print(f"Has setPageSize: {hasattr(printer, 'setPageSize')}")
print(f"Has setPageLayout: {hasattr(printer, 'setPageLayout')}")

print("\nAll attributes on QPrinter:")
print([attr for attr in dir(printer) if 'Page' in attr])

print("\nAll attributes on QPageSize:")
print([attr for attr in dir(QPageSize) if 'A4' in attr or 'PageSize' in attr])
