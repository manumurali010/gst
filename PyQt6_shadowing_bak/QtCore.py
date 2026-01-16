class QObject:
    def __init__(self, parent=None):
        pass

class pyqtSignal:
    def __init__(self, *args, **kwargs):
        pass
    def emit(self, *args, **kwargs):
        print(f"SIGNAL EMIT: {args}")
