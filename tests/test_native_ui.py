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



def test_native_tables_use_alternating_rows_and_data_alignment(qtbot):
    from app.ui.common import populate, table

    widget = table(["名称", "数量", "比率", "判定", "来源"])
    qtbot.addWidget(widget)
    populate(widget, [["工单 A", 1234, "2.37%", "合格", "正式数据"]])

    assert widget.alternatingRowColors()
    assert widget.item(0, 1).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert widget.item(0, 2).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert widget.item(0, 3).textAlignment() & Qt.AlignmentFlag.AlignHCenter
    assert widget.item(0, 4).textAlignment() & Qt.AlignmentFlag.AlignHCenter


def test_core_pages_reflow_at_minimum_and_wide_desktop_widths(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window, before_close_func=lambda w: setattr(w.pages[1], "dirty", False))
    window.show()

    def position(layout, widget):
        index = layout.indexOf(widget)
        assert index >= 0
        return layout.getItemPosition(index)

    window.resize(1080, 720)
    qtbot.wait(50)

    window.navigate(0)
    dashboard = window.pages[0]
    qtbot.waitUntil(lambda: dashboard._layout_mode == "narrow")
    assert position(dashboard.grid, dashboard.cards[2][0]) == (1, 0, 1, 5)
    assert position(dashboard.grid, dashboard.chart_frames[0]) == (5, 0, 1, 10)

    window.navigate(1)
    entry = window.pages[1]
    qtbot.waitUntil(lambda: entry._layout_mode == "narrow")
    assert position(entry.content_grid, entry.left_panel) == (0, 0, 1, 1)
    assert position(entry.content_grid, entry.right_panel) == (1, 0, 1, 1)

    window.navigate(2)
    records = window.pages[2]
    qtbot.waitUntil(lambda: records._filter_layout_mode == "narrow")
    assert position(records.filters_grid, records.search_field) == (1, 2, 1, 1)
    assert position(records.filters_grid, records.defect_field) == (3, 0, 1, 2)

    window.navigate(3)
    analytics = window.pages[3]
    qtbot.waitUntil(lambda: analytics._layout_mode == "narrow")
    assert position(analytics.filters_grid, analytics.analyze_button) == (3, 2, 1, 1)
    assert position(analytics.grid, analytics.trend_frame) == (4, 0, 1, 10)

    window.resize(1440, 920)
    qtbot.wait(50)

    window.navigate(0)
    qtbot.waitUntil(lambda: dashboard._layout_mode == "wide")
    assert position(dashboard.grid, dashboard.cards[2][0]) == (0, 4, 1, 2)
    assert position(dashboard.grid, dashboard.chart_frames[0]) == (2, 0, 1, 5)

    window.navigate(1)
    qtbot.waitUntil(lambda: entry._layout_mode == "wide")
    assert position(entry.content_grid, entry.right_panel) == (0, 1, 1, 1)

    window.navigate(2)
    qtbot.waitUntil(lambda: records._filter_layout_mode == "wide")
    assert position(records.filters_grid, records.search_field) == (1, 0, 1, 2)
    assert position(records.filters_grid, records.defect_field) == (2, 0, 1, 2)

    window.navigate(3)
    qtbot.waitUntil(lambda: analytics._layout_mode == "wide")
    assert position(analytics.filters_grid, analytics.analyze_button) == (1, 5, 1, 1)
    assert position(analytics.grid, analytics.trend_frame) == (2, 0, 1, 5)
