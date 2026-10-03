from PySide6.QtCore import QObject, Signal, Slot


class Worker(QObject):
    completed = Signal(object, object)

    def __init__(self, function):
        super().__init__()
        self.function = function

    @Slot()
    def run(self):
        try:
            self.completed.emit(self.function(), None)
        except Exception as error:
            self.completed.emit(None, error)
