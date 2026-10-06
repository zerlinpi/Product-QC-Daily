import logging
import re
from functools import wraps

from pydantic import ValidationError
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

from app.core.validation import validation_message


def friendly_error(parent, error):
    logging.getLogger("qc.ui").error("操作失败", exc_info=(type(error), error, error.__traceback__))
    if isinstance(error, ValidationError):
        message = validation_message(error)
        location = error.errors()[0]["loc"]
        widget = getattr(parent, str(location[0]), None) if location else None
        if isinstance(widget, QWidget):
            widget.setFocus()
    elif isinstance(error, ValueError):
        message = (
            str(error)
            if re.search(r"[\u4e00-\u9fff]", str(error))
            else "输入内容或文件格式不符合要求，请检查后重试。详细原因已写入日志。"
        )
    elif isinstance(error, PermissionError):
        message = "文件可能被其他程序占用，或目录没有写入权限。请关闭文件后重试。"
    elif isinstance(error, OSError):
        message = "无法读写文件。请检查路径、磁盘剩余空间和文件权限。"
    else:
        message = "操作未完成。请检查文件和数据库是否被占用；详细原因已写入日志。"
    QMessageBox.warning(parent, "操作未完成", message[:1500])


def confirm(parent, title, message, action="确认", cancel="取消", danger=False):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
    accept = dialog.addButton(action, QMessageBox.ButtonRole.AcceptRole)
    accept.setObjectName("danger" if danger else "primary")
    reject = dialog.addButton(cancel, QMessageBox.ButtonRole.RejectRole)
    dialog.setDefaultButton(reject)
    dialog.setEscapeButton(reject)
    dialog.exec()
    return dialog.clickedButton() == accept


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
    """Compact native section panel; avoid web-style rounded card chrome."""
    frame = QFrame()
    frame.setObjectName("card")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setLineWidth(1)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(8)
    return frame, layout


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setShowGrid(True)
    widget.verticalHeader().setVisible(False)
    widget.verticalHeader().setDefaultSectionSize(28)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setWordWrap(False)
    widget.setMouseTracking(True)
    widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    widget.horizontalHeader().setHighlightSections(False)
    widget.horizontalHeader().setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    widget.horizontalHeader().setStretchLastSection(True)
    return widget


def populate(widget, rows):
    widget.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value if value is not None else "—"))
            item.setToolTip(item.text())
            if value in ("合格", "返工", "演示数据"):
                item.setForeground(QColor("#107c10" if value == "合格" else "#ca5010"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif value in ("正式数据", "启用", "停用"):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                or isinstance(value, str)
                and re.fullmatch(r"[+-]?\d[\d,]*(?:\.\d+)?%?", value.strip())
            ):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            widget.setItem(row, col, item)


class Page(QWidget):
    def __init__(self, ctx, window, title, subtitle):
        super().__init__()
        self.ctx, self.window = ctx, window
        self.setObjectName("page")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(6)
        self.title_label = label(title, "title")
        self.subtitle_label = label(subtitle, "subtitle", True)
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addSpacing(2)

    def refresh(self):
        pass
