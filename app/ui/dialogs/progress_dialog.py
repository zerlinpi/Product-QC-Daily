from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QProgressBar

from app.ui.common import PROGRESS_DIALOG_MIN_WIDTH, dialog_layout, label


class TaskProgressDialog(QDialog):
    def __init__(self, parent, title, window_title="正在处理", message="请稍候…"):
        super().__init__(parent)
        self.setObjectName("taskProgressDialog")
        self.setWindowTitle(window_title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(PROGRESS_DIALOG_MIN_WIDTH)
        layout = dialog_layout(self)
        layout.addWidget(label(title, "status"))
        layout.addWidget(label(message, "muted", True))
        self.progress = QProgressBar()
        self.progress.setObjectName("taskProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
