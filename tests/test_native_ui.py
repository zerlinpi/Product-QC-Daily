from PySide6.QtCore import QDate, Qt
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
    assert dashboard.grid.count() == 16

    window.navigate(1)
    entry = window.pages[1]
    qtbot.waitUntil(lambda: entry._layout_mode == "narrow")
    assert position(entry.content_grid, entry.left_panel) == (0, 0, 1, 1)
    assert position(entry.content_grid, entry.right_panel) == (1, 0, 1, 1)
    assert entry.content_grid.count() == 2

    window.navigate(2)
    records = window.pages[2]
    qtbot.waitUntil(lambda: records._filter_layout_mode == "narrow")
    assert position(records.filters_grid, records.search_field) == (1, 2, 1, 1)
    assert position(records.filters_grid, records.defect_field) == (3, 0, 1, 2)
    assert records.filters_grid.count() == 13

    window.navigate(3)
    analytics = window.pages[3]
    qtbot.waitUntil(lambda: analytics._layout_mode == "narrow")
    assert position(analytics.filters_grid, analytics.analyze_button) == (3, 2, 1, 1)
    assert position(analytics.grid, analytics.trend_frame) == (4, 0, 1, 10)
    assert analytics.filters_grid.count() == 11
    assert analytics.grid.count() == 10

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
    assert dashboard.grid.count() == 16
    assert entry.content_grid.count() == 2
    assert records.filters_grid.count() == 13
    assert analytics.filters_grid.count() == 11
    assert analytics.grid.count() == 10



def test_reports_settings_and_defects_keep_native_utility_hierarchy(ctx, qtbot):
    from PySide6.QtWidgets import QGroupBox, QHeaderView

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.show()

    def position(layout, widget):
        index = layout.indexOf(widget)
        assert index >= 0
        return layout.getItemPosition(index)

    window.resize(1080, 720)
    window.navigate(5)
    reports = window.pages[5]
    qtbot.waitUntil(lambda: reports._layout_mode == "narrow")
    assert position(reports.filters_grid, reports.preset) == (1, 0, 1, 1)
    assert position(reports.filters_grid, reports.source) == (3, 1, 1, 1)
    assert reports.import_status.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse

    window.resize(1440, 920)
    qtbot.waitUntil(lambda: reports._layout_mode == "wide")
    assert position(reports.filters_grid, reports.source) == (1, 3, 1, 1)

    window.navigate(6)
    settings = window.pages[6]
    groups = {group.title() for group in settings.findChildren(QGroupBox)}
    assert {"基础设置", "组别管理", "数据维护"}.issubset(groups)
    assert settings.team_count.text().startswith("共 ")
    assert settings.location.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    header = settings.teams.horizontalHeader()
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.ResizeToContents
    assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.ResizeToContents

    window.navigate(4)
    defects = window.pages[4]
    assert defects.search.isClearButtonEnabled()
    assert defects.count.text().startswith("共 ")
    if defects.table.rowCount():
        defects.table.selectRow(0)
        assert defects.selection_state.text().startswith("已选择：")


def test_progress_dialog_uses_readable_native_task_metrics(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    dialog = TaskProgressDialog(
        window,
        "正在导出质量报表",
        message="正在生成文件并校验输出内容，请稍候…",
    )
    qtbot.addWidget(dialog)

    assert dialog.minimumWidth() == 400
    labels = dialog.findChildren(type(window.pages[0].title_label))
    assert any(label.wordWrap() for label in labels if "正在生成文件" in label.text())



def test_all_pages_share_one_native_spacing_system(ctx, qtbot):
    from PySide6.QtWidgets import QScrollArea

    from app.ui.common import LAYOUT_SPACING, PAGE_MARGINS

    window = MainWindow(ctx)
    qtbot.addWidget(window)

    for page in window.pages:
        assert page.layout.getContentsMargins() == PAGE_MARGINS
        assert page.layout.spacing() == LAYOUT_SPACING

    embedded_scrolls = [
        scroll
        for page in window.pages
        for scroll in page.findChildren(QScrollArea)
    ]
    assert embedded_scrolls
    assert all(scroll.frameShape() == QFrame.Shape.NoFrame for scroll in embedded_scrolls)
    assert all(
        scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        for scroll in embedded_scrolls
    )


def test_workflow_sections_use_consistent_native_group_boxes(ctx, qtbot):
    from PySide6.QtWidgets import QGroupBox

    window = MainWindow(ctx)
    qtbot.addWidget(window)

    expected = {
        1: {"检验信息", "不良项目"},
        2: {"筛选条件"},
        3: {"分析范围"},
        4: {"项目列表"},
        5: {"导入历史日检表", "导出质量报表"},
        6: {"基础设置", "组别管理", "数据维护"},
    }
    for index, titles in expected.items():
        present = {group.title() for group in window.pages[index].findChildren(QGroupBox)}
        assert titles.issubset(present)


def test_common_buttons_share_native_height_and_action_hierarchy(qtbot):
    from app.ui.common import CONTROL_MIN_HEIGHT, button

    normal = button("普通")
    primary = button("主要", primary=True)
    danger = button("危险", danger=True)
    for widget in (normal, primary, danger):
        qtbot.addWidget(widget)
        assert widget.minimumHeight() == CONTROL_MIN_HEIGHT
        assert not widget.autoDefault()

    assert primary.font().bold()
    assert not danger.icon().isNull()


def test_dynamic_status_labels_use_consistent_tones(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    reports = window.pages[5]
    reports.preset.setCurrentText("自定义")
    reports.start.setDate(QDate(2026, 2, 2))
    reports.end.setDate(QDate(2026, 2, 1))
    assert reports.export_scope.objectName() == "error"
    reports.end.setDate(QDate(2026, 2, 2))
    assert reports.export_scope.objectName() == "status"

    analytics = window.pages[3]
    analytics.preset.setCurrentText("自定义")
    analytics.start.setDate(QDate(2026, 2, 2))
    analytics.end.setDate(QDate(2026, 2, 1))
    assert analytics.scope.objectName() == "error"



def test_dialog_button_box_helper_unifies_native_metrics(qtbot):
    from PySide6.QtWidgets import QDialogButtonBox

    from app.ui.common import CONTROL_MIN_HEIGHT, dialog_button_box

    box = dialog_button_box(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        default=QDialogButtonBox.StandardButton.Save,
    )
    qtbot.addWidget(box)

    save = box.button(QDialogButtonBox.StandardButton.Save)
    cancel = box.button(QDialogButtonBox.StandardButton.Cancel)
    assert save.minimumHeight() == CONTROL_MIN_HEIGHT
    assert cancel.minimumHeight() == CONTROL_MIN_HEIGHT
    assert save.isDefault()
    assert save.autoDefault()
    assert not cancel.autoDefault()


def test_summary_labels_share_one_visual_role(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    assert window.pages[0].refreshed.objectName() == "summary"
    assert window.pages[2].selection_count.objectName() == "summary"
    assert window.pages[2].count.objectName() == "summary"
    assert window.pages[4].count.objectName() == "summary"
    assert window.pages[4].selection_state.objectName() == "summary"
    assert window.pages[5].import_status.objectName() == "summary"
    assert window.pages[6].team_count.objectName() == "summary"
    assert window.pages[1].defects.total.objectName() == "summary"


def test_chart_palette_tracks_application_theme(qtbot):
    from app.ui.common import chart_palette
    from app.ui.widgets.chart_widget import ChartWidget

    chart = ChartWidget("主题测试")
    qtbot.addWidget(chart)
    chart.draw(["A", "B"], [1, 2])

    apply_theme("light")
    chart.refresh_theme()
    light = chart_palette()
    assert light["warning"].name() == "#ca5010"
    assert light["text"].name() == QApplication.palette().windowText().color().name()

    apply_theme("dark")
    chart.refresh_theme()
    dark = chart_palette()
    assert dark["warning"].name() == "#f5a623"
    assert dark["text"].name() == QApplication.palette().windowText().color().name()

    apply_theme("light")



def test_reusable_widgets_share_vertical_rhythm_and_empty_state_role(ctx, qtbot):
    from PySide6.QtWidgets import QWidget

    from app.ui.common import LAYOUT_SPACING, SECTION_MARGINS, stack_layout
    from app.ui.widgets.chart_widget import ChartWidget
    from app.ui.widgets.defect_selector import DefectSelector
    from app.ui.widgets.stat_card import stat_card

    host = QWidget()
    qtbot.addWidget(host)
    layout = stack_layout(host)
    assert layout.getContentsMargins() == (0, 0, 0, 0)
    assert layout.spacing() == LAYOUT_SPACING

    chart = ChartWidget("一致性图表")
    qtbot.addWidget(chart)
    assert chart.layout().getContentsMargins() == (0, 0, 0, 0)
    assert chart.layout().spacing() == LAYOUT_SPACING
    assert chart.empty.objectName() == "empty"

    selector = DefectSelector(ctx)
    qtbot.addWidget(selector)
    assert selector.layout().getContentsMargins() == (0, 0, 0, 0)
    assert selector.layout().spacing() == LAYOUT_SPACING

    metric = stat_card("一致性指标")
    qtbot.addWidget(metric)
    assert metric.layout().getContentsMargins() == SECTION_MARGINS
    assert metric.layout().spacing() == 4


def test_table_headers_follow_numeric_and_status_alignment(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    records = window.pages[2].table
    assert records.horizontalHeaderItem(4).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert records.horizontalHeaderItem(7).textAlignment() & Qt.AlignmentFlag.AlignHCenter

    analytics = window.pages[3]
    assert analytics.ranking.horizontalHeaderItem(5).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert analytics.teams_table.horizontalHeaderItem(7).textAlignment() & Qt.AlignmentFlag.AlignRight

    defects = window.pages[4].table
    assert defects.horizontalHeaderItem(4).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert defects.horizontalHeaderItem(3).textAlignment() & Qt.AlignmentFlag.AlignHCenter

    settings = window.pages[6].teams
    assert settings.horizontalHeaderItem(2).textAlignment() & Qt.AlignmentFlag.AlignRight
    assert settings.horizontalHeaderItem(1).textAlignment() & Qt.AlignmentFlag.AlignHCenter


def test_normal_summary_and_empty_states_use_distinct_visual_roles(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    records = window.pages[2]
    records.refresh()
    assert records.count.objectName() == "summary"

    analytics = window.pages[3]
    analytics.refresh()
    if analytics.pareto._pareto_rows:
        assert analytics.top80.objectName() == "summary"
    else:
        assert analytics.top80.objectName() == "empty"

    assert window.pages[0].charts[0].empty.objectName() == "empty"
