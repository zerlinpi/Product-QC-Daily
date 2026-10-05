from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame

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
    assert sidebar is not None and sidebar.width() == 184
    assert window.pages[2].table.verticalHeader().defaultSectionSize() == 34


def test_native_primitives_are_not_overpainted_by_global_theme(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    apply_theme("light")
    stylesheet = QApplication.instance().styleSheet()
    assert "font-family" not in stylesheet
    assert "QScrollBar" not in stylesheet
    assert "QCheckBox::indicator" not in stylesheet
    dialog = TaskProgressDialog(window, "导出报表")
    qtbot.addWidget(dialog)
    assert not bool(dialog.windowFlags() & Qt.WindowType.WindowCloseButtonHint)
