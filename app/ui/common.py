import logging
import re
from functools import wraps

from pydantic import ValidationError
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.validation import validation_message

PAGE_MARGINS = (14, 12, 14, 12)
DIALOG_MARGINS = (14, 12, 14, 12)
SECTION_MARGINS = (10, 12, 10, 10)
SIDEBAR_MARGINS = (8, 10, 8, 8)
TOPBAR_MARGINS = (14, 4, 14, 4)
LAYOUT_SPACING = 8
TOOLBAR_SPACING = 6
CONTROL_MIN_HEIGHT = 28
BUTTON_MIN_WIDTH = 84
COMPACT_FIELD_MIN_WIDTH = 110
FILTER_FIELD_MIN_WIDTH = 120
SEARCH_FIELD_MIN_WIDTH = 240
FORM_DIALOG_MIN_WIDTH = 460
TABLE_ROW_HEIGHT = 28
CHART_MIN_HEIGHT = 190
TOPBAR_MIN_HEIGHT = 36


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


def button_metrics(*widgets):
    """Apply the shared Windows desktop button footprint."""
    for widget in widgets:
        widget.setMinimumHeight(CONTROL_MIN_HEIGHT)
        widget.setMinimumWidth(BUTTON_MIN_WIDTH)
    if len(widgets) == 1:
        return widgets[0]
    return widgets


def button(text, callback=None, primary=False, danger=False):
    widget = QPushButton(text)
    widget.setObjectName("primary" if primary else "danger" if danger else "")
    widget.setAutoDefault(False)
    button_metrics(widget)
    if primary:
        font = widget.font()
        font.setBold(True)
        widget.setFont(font)
    if danger:
        style = QApplication.instance().style() if QApplication.instance() else None
        if style:
            widget.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
    if callback:
        widget.clicked.connect(callback)
    return widget


def control_metrics(*widgets, min_width=None):
    """Apply shared desktop field metrics without repainting native controls."""
    for widget in widgets:
        widget.setMinimumHeight(CONTROL_MIN_HEIGHT)
        if min_width is not None:
            widget.setMinimumWidth(min_width)
    if len(widgets) == 1:
        return widgets[0]
    return widgets


def label(text, kind="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(kind)
    widget.setWordWrap(wrap)
    return widget


def set_label_kind(widget, kind):
    widget.setObjectName(kind)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def card():
    """Compact native panel for visualizations or untitled content."""
    frame = QFrame()
    frame.setObjectName("card")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setFrameShadow(QFrame.Shadow.Plain)
    frame.setLineWidth(1)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*SECTION_MARGINS)
    layout.setSpacing(LAYOUT_SPACING)
    return frame, layout


def native_group(title):
    """Native Windows-style titled section for forms and utility workflows."""
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.setContentsMargins(*SECTION_MARGINS)
    layout.setSpacing(LAYOUT_SPACING)
    return group, layout


def form_group(title):
    group = QGroupBox(title)
    layout = form_layout(group)
    layout.setContentsMargins(*SECTION_MARGINS)
    return group, layout


def toolbar_layout(parent=None):
    layout = QHBoxLayout(parent) if parent is not None else QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(TOOLBAR_SPACING)
    return layout


def stack_layout(parent=None, margins=(0, 0, 0, 0), spacing=LAYOUT_SPACING):
    """Shared vertical rhythm for page bodies and reusable widgets."""
    layout = QVBoxLayout(parent) if parent is not None else QVBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def form_layout(parent=None):
    layout = QFormLayout(parent) if parent is not None else QFormLayout()
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(8)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    return layout


def form_grid(parent=None):
    layout = QGridLayout(parent) if parent is not None else QGridLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(12)
    layout.setVerticalSpacing(LAYOUT_SPACING)
    return layout


def content_grid(parent=None):
    layout = QGridLayout(parent) if parent is not None else QGridLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(LAYOUT_SPACING)
    return layout


def dialog_layout(dialog):
    return stack_layout(dialog, DIALOG_MARGINS)


def dialog_button_box(buttons, default=None):
    """Create a native dialog button box with the same control metrics everywhere."""
    box = QDialogButtonBox(buttons)
    for control in box.buttons():
        button_metrics(control)
        control.setAutoDefault(False)
    if default is not None:
        control = box.button(default)
        if control is not None:
            control.setAutoDefault(True)
            control.setDefault(True)
    return box


def page_scroll():
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return scroll


def grid_place(layout, widget, row, column, row_span=1, column_span=1):
    """Move an existing widget inside a grid without leaving duplicate layout entries."""
    layout.removeWidget(widget)
    layout.addWidget(widget, row, column, row_span, column_span)


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setShowGrid(True)
    widget.verticalHeader().setVisible(False)
    widget.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setWordWrap(False)
    widget.setTextElideMode(Qt.TextElideMode.ElideRight)
    widget.setMouseTracking(True)
    widget.setCornerButtonEnabled(False)
    widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    widget.horizontalHeader().setHighlightSections(False)
    widget.horizontalHeader().setMinimumSectionSize(55)
    widget.horizontalHeader().setMinimumHeight(CONTROL_MIN_HEIGHT)
    widget.horizontalHeader().setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    widget.horizontalHeader().setStretchLastSection(True)
    return widget


def align_table_columns(widget, right=(), center=()):
    """Keep table headers aligned with the data they describe."""
    for column in right:
        item = widget.horizontalHeaderItem(column)
        if item is not None:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    for column in center:
        item = widget.horizontalHeaderItem(column)
        if item is not None:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


def palette_color(role):
    return QApplication.palette().color(role)


def chart_palette():
    """Theme-aware colors shared by every pyqtgraph widget."""
    accent = palette_color(QPalette.ColorRole.Highlight)
    axis = palette_color(QPalette.ColorRole.Mid)
    text = palette_color(QPalette.ColorRole.WindowText)
    fill = QColor(accent)
    fill.setAlpha(28)
    grid = QColor(axis)
    grid.setAlpha(72)
    return {
        "accent": accent,
        "axis": axis,
        "text": text,
        "fill": fill,
        "grid": grid,
        "warning": semantic_color("warning"),
    }


def semantic_color(kind):
    palette = QApplication.palette()
    dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
    colors = (
        {
            "success": "#6ccb5f",
            "warning": "#f5a623",
            "error": "#ff8a80",
        }
        if dark
        else {
            "success": "#107c10",
            "warning": "#ca5010",
            "error": "#c42b1c",
        }
    )
    return QColor(colors[kind])


def populate(widget, rows):
    widget.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value if value is not None else "—"))
            item.setToolTip(item.text())
            if value in ("合格", "启用", "正常"):
                item.setForeground(semantic_color("success"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif value in ("返工", "演示数据", "停用", "重复", "编号冲突"):
                item.setForeground(semantic_color("warning"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif value in ("异常", "无法识别"):
                item.setForeground(semantic_color("error"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif value == "正式数据":
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
        self.layout = stack_layout(self, PAGE_MARGINS)
        self.title_label = label(title, "title")
        self.subtitle_label = label(subtitle, "subtitle", True)
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addSpacing(2)

    def refresh(self):
        pass
