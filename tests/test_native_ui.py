from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QGroupBox

from app.ui.dialogs.progress_dialog import TaskProgressDialog
from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_theme, preferred_style_name


def test_windows_prefers_native_desktop_style():
    assert preferred_style_name("win32", ["Fusion", "WindowsVista", "Windows"]) == "WindowsVista"


def test_windows_falls_back_to_windows_style_when_vista_style_is_unavailable():
    assert preferred_style_name("win32", ["Fusion", "Windows"]) == "Windows"


def test_non_windows_keeps_stable_fusion_fallback():
    assert preferred_style_name("linux", ["Windows", "Fusion"]) == "Fusion"


def test_main_navigation_uses_system_icons_and_compact_desktop_metrics(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    assert [button.text() for button in window.nav_buttons] == [
        "质量总览",
        "日检录入",
        "检验记录",
        "质量分析",
        "不良项目",
        "报表中心",
        "系统设置",
    ]
    assert all(not button.icon().isNull() for button in window.nav_buttons)
    sidebar = window.findChild(QFrame, "qcSidebar")
    assert sidebar is not None and sidebar.width() == 176
    assert all(button.isFlat() and button.minimumHeight() == 30 for button in window.nav_buttons)
    records = window.pages[2].table
    assert records.verticalHeader().defaultSectionSize() == 28
    assert records.showGrid()


def test_native_primitives_are_not_overpainted_by_global_theme(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    apply_theme("light")
    stylesheet = QApplication.instance().styleSheet()
    assert "font-family" not in stylesheet
    assert "QScrollBar" not in stylesheet
    assert "QCheckBox::indicator" not in stylesheet
    for selector in (
        "QPushButton {",
        "QLineEdit",
        "QComboBox",
        "QDateEdit",
        "QMenu {",
        "QTableWidget {",
        "QHeaderView::section",
        "QGroupBox {",
        "QMessageBox {",
    ):
        assert selector not in stylesheet
    dialog = TaskProgressDialog(window, "导出报表")
    qtbot.addWidget(dialog)
    assert not bool(dialog.windowFlags() & Qt.WindowType.WindowCloseButtonHint)



def test_sections_and_metrics_use_native_desktop_frames(ctx, qtbot):
    from app.ui.common import card
    from app.ui.widgets.stat_card import stat_card

    panel, _ = card()
    qtbot.addWidget(panel)
    assert panel.frameShape() == QFrame.Shape.StyledPanel

    metric = stat_card("今日检验批次")
    qtbot.addWidget(metric)
    assert isinstance(metric, QGroupBox)
    assert metric.title() == "今日检验批次"
