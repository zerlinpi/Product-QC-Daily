from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QGroupBox, QListWidget, QPushButton

from app.ui.dialogs.progress_dialog import TaskProgressDialog
from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_theme, preferred_style_name


def test_windows_prefers_native_desktop_style():
    assert preferred_style_name("win32", ["Fusion", "WindowsVista", "Windows"]) == "WindowsVista"


def test_windows_falls_back_to_windows_style_when_vista_style_is_unavailable():
    assert preferred_style_name("win32", ["Fusion", "Windows"]) == "Windows"


def test_non_windows_keeps_stable_fusion_fallback():
    assert preferred_style_name("linux", ["Windows", "Fusion"]) == "Fusion"


def test_main_navigation_uses_native_list_and_compact_desktop_metrics(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    navigation = window.findChild(QListWidget, "navigation")
    assert navigation is not None
    assert [navigation.item(i).text() for i in range(navigation.count())] == [
        "质量总览",
        "日检录入",
        "检验记录",
        "质量分析",
        "不良项目",
        "报表中心",
        "系统设置",
    ]
    assert all(not navigation.item(i).icon().isNull() for i in range(navigation.count()))
    assert all(navigation.item(i).sizeHint().height() == 28 for i in range(navigation.count()))
    sidebar = window.findChild(QFrame, "qcSidebar")
    assert sidebar is not None and sidebar.width() == 176
    navigation.setCurrentRow(3)
    assert window.stack.currentIndex() == 3
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
        "QListWidget {",
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



def test_native_navigation_reverts_when_unsaved_entry_refuses_page_change(
    ctx, qtbot, monkeypatch
):
    import app.ui.pages.inspection_page as inspection_module

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(1)
    entry = window.pages[1]
    entry.work_order.setText("UNSAVED")
    entry.dirty = True
    monkeypatch.setattr(inspection_module, "confirm", lambda *args, **kwargs: False)

    window.navigation.setCurrentRow(2)

    assert window.stack.currentIndex() == 1
    assert window.navigation.currentRow() == 1
    assert entry.work_order.text() == "UNSAVED"
    assert entry.dirty



def test_reports_page_uses_native_group_boxes_and_compact_export_actions(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]

    groups = {group.title(): group for group in page.findChildren(QGroupBox)}
    assert "导入历史日检表" in groups
    assert "导出质量报表" in groups
    buttons = {button.text(): button for button in page.findChildren(QPushButton)}
    assert "按原表导出" in buttons
    assert "导出明细报表" in buttons
    assert "月份筛选" in buttons["导出明细报表"].toolTip()
