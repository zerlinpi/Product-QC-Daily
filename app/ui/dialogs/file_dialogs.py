"""Consistent Chinese Excel save dialogs for every export entry point."""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QListView, QSplitter


class ExcelSaveDialog(QFileDialog):
    def __init__(self, parent, title, default_path, file_filter):
        destination = Path(default_path).expanduser()
        # Qt silently falls back to the last directory if this one is missing.
        # Create the user's configured export directory before opening the picker.
        destination.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(parent, title)
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setNameFilter(file_filter)
        self.setDefaultSuffix("xlsx")
        self.setDirectory(str(destination.parent))
        self.selectFile(destination.name)
        screen = parent.screen() if parent else QApplication.primaryScreen()
        available = screen.availableGeometry()
        width, height = min(840, available.width() - 40), min(540, available.height() - 40)
        self.resize(width, height)
        sidebar = self.findChild(QListView, "sidebar")
        if sidebar:
            sidebar.setMinimumWidth(128)
        splitter = self.findChild(QSplitter, "splitter")
        if splitter:
            splitter.setSizes([160, max(320, width - 190)])


def save_excel(parent, title, default_path, file_filter):
    dialog = ExcelSaveDialog(parent, title, default_path, file_filter)
    try:
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return str(Path(dialog.selectedFiles()[0])), dialog.selectedNameFilter()
        return "", ""
    finally:
        dialog.deleteLater()
