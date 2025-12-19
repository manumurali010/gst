from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QPageSize

try:
    print(f"QPrinter.PageSize: {QPrinter.PageSize}")
    print(f"QPrinter.PageSize.A4: {QPrinter.PageSize.A4}")
except Exception as e:
    print(f"Error accessing QPrinter.PageSize: {e}")

try:
    print(f"QPageSize.PageSizeId: {QPageSize.PageSizeId}")
    print(f"QPageSize.PageSizeId.A4: {QPageSize.PageSizeId.A4}")
except Exception as e:
    print(f"Error accessing QPageSize.PageSizeId: {e}")
