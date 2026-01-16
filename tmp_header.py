import pandas as pd
import re
import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class AmbiguityError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class GSTR2AAnalyzer(QObject):
    """
    Deterministic GSTR-2A Analyzer for Scrutiny SOPs 3, 5, 7, 8, 10.
    Enforces strict scope, deterministic header parsing, and ambiguity handling.
    """
