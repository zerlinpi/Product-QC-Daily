"""Consistent Chinese Excel save dialogs for every export entry point."""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QListView, QSplitter

from app.ui.common import FILE_DIALOG_MAX_SIZE, FILE_DIALOG_SIDEBAR_MIN_WIDTH


def _use_native_windows_dialog() -> bool:
    """Use the real Windows file picker in normal desktop runs.

    Offscreen runs intentionally keep the Qt dialog so CI and the packaged
    self-test can exercise it without opening an OS modal window.
    """
    return sys.platform == "win32" and os.environ.get("QT_QPA_PLATFORM", "").lower() != "offscreen"


class ExcelSaveDialog(QFileDialog):
    def __init__(self, parent, title, default_path, file_filter):
        destination = Path(default_path).expanduser()
        # Qt silently falls back to the last directory if this one is missing.
        # Create the user's configured export directory before opening the picker.
        destination.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(parent, title)
        native_windows = _use_native_windows_dialog()
        self.setOption(QFileDialog.Option.DontUseNativeDialog, not native_windows)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setNameFilter(file_filter)
        self.setDefaultSuffix("xlsx")
        self.setDirectory(str(destination.parent))
        self.selectFile(destination.name)
        screen = parent.screen() if parent else QApplication.primaryScreen()
        available = screen.availableGeometry()
        width = min(FILE_DIALOG_MAX_SIZE[0], available.width() - 40)
        height = min(FILE_DIALOG_MAX_SIZE[1], available.height() - 40)
        self.resize(width, height)
        if not native_windows:
            sidebar = self.findChild(QListView, "sidebar")
            if sidebar:
                sidebar.setMinimumWidth(FILE_DIALOG_SIDEBAR_MIN_WIDTH)
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
