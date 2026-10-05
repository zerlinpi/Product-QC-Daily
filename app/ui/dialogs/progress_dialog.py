from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QProgressBar, QVBoxLayout

from app.ui.common import label


class TaskProgressDialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setObjectName("taskProgressDialog")
        self.setWindowTitle("正在导出")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(label(title, "section"))
        layout.addWidget(label("正在生成文件，请稍候…", "muted"))
        self.progress = QProgressBar()
        self.progress.setObjectName("taskProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
