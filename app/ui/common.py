import logging
from functools import wraps

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def friendly_error(parent, error):
    logging.getLogger("qc.ui").error("操作失败", exc_info=(type(error), error, error.__traceback__))
    if isinstance(error, ValueError):
        message = str(error)
        if "validation error" in message:
            message = (
                "请检查必填项、数量及不良项目。\n" + "\n".join(e["msg"] for e in error.errors())
                if hasattr(error, "errors")
                else message
            )
    elif isinstance(error, PermissionError):
        message = "文件可能已被 Excel 打开，或目录没有写入权限。请关闭文件后重试。"
    elif isinstance(error, OSError):
        message = "无法读写文件。请检查路径、磁盘剩余空间和文件权限。"
    else:
        message = "操作未完成。请检查文件和数据库是否被占用；详细原因已写入日志。"
    QMessageBox.warning(parent, "操作未完成", message[:1500])


def guarded(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except Exception as error:
            friendly_error(self, error)

    return wrapped


def button(text, callback=None, primary=False, danger=False):
    widget = QPushButton(text)
    widget.setObjectName("primary" if primary else "danger" if danger else "")
    widget.setAutoDefault(False)
    if callback:
        widget.clicked.connect(callback)
    return widget


def label(text, kind="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(kind)
    widget.setWordWrap(wrap)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)
    return frame, layout


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setShowGrid(False)
    widget.verticalHeader().setVisible(False)
    widget.verticalHeader().setDefaultSectionSize(42)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    widget.horizontalHeader().setStretchLastSection(True)
    return widget


def populate(widget, rows):
    widget.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value if value is not None else "—"))
            if value in ("合格", "返工", "demo"):
                item.setForeground(QColor("#12805c" if value == "合格" else "#c96c16"))
                item.setBackground(QColor("#e7f6ee" if value == "合格" else "#fff0dd"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setItem(row, col, item)


class Page(QWidget):
    def __init__(self, ctx, window, title, subtitle):
        super().__init__()
        self.ctx, self.window = ctx, window
        self.setObjectName("page")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 24, 28, 20)
        self.layout.setSpacing(16)
        self.layout.addWidget(label(title, "title"))
        self.layout.addWidget(label(subtitle, "subtitle", True))

    def refresh(self):
        pass
