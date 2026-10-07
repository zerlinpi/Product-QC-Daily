from datetime import date
from threading import Event

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QGroupBox

from app.core.schemas import RecordFilter
from app.services.demo_service import demo_workdays, suggested_demo_count
from app.ui.dialogs.demo_dialog import DemoDialog
from app.ui.main_window import MainWindow


def test_demo_completion_switches_dashboard_to_demo_and_refreshes(ctx, qtbot):
    count = ctx.demo.generate(
        8,
        date.today(),
        date.today(),
        ["U1"],
        rework_rate=0.1,
        defect_rate=0.02,
        seed=7,
    )
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(6)

    window.show_demo_data(count)

    dashboard = window.pages[0]
    assert window.stack.currentIndex() == 0
    assert dashboard.source.currentText() == "演示数据"
    assert dashboard.cards[0][0].value_label.text() == "8"
    assert "已生成 8 条演示记录" in window.statusBar().currentMessage()


def test_demo_generation_uses_window_modal_progress(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.show()
    started, release = Event(), Event()

    def work():
        started.set()
        assert release.wait(5)
        return 1

    try:
        window.run_job("生成演示数据", work)
        qtbot.waitUntil(started.is_set, timeout=5000)
        assert window._job_dialog is not None
        assert window._job_dialog.windowTitle() == "正在生成演示数据"
        assert window._job_dialog.isModal()
        assert not bool(window._job_dialog.windowFlags() & Qt.WindowType.WindowCloseButtonHint)
    finally:
        release.set()
        qtbot.waitUntil(lambda: window._job is None, timeout=10000)


def test_demo_dialog_uses_desktop_sections_and_clear_primary_action(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    dialog = DemoDialog(ctx, window)
    qtbot.addWidget(dialog)

    assert {group.title() for group in dialog.findChildren(QGroupBox)} == {
        "生成范围",
        "参与组别",
        "不良项目出现频率",
    }
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons.button(QDialogButtonBox.StandardButton.Ok).text() == "生成并查看"
    assert not bool(dialog.windowFlags() & Qt.WindowType.WindowContextHelpButtonHint)
    assert set(dialog.options()["teams"]) == {item["name"] for item in ctx.settings.teams(True)}
    today = date.today()
    assert dialog.start.date().toPython() == date(today.year, 1, 1)
    assert dialog.end.date().toPython() == date(today.year, 12, 31)
    assert dialog.count.value() == suggested_demo_count(
        date(today.year, 1, 1), date(today.year, 12, 31)
    )



def test_full_year_demo_matches_uploaded_form_workday_density(ctx):
    start, end = date(2026, 1, 1), date(2026, 12, 31)
    expected_days = demo_workdays(start, end)
    count = suggested_demo_count(start, end)

    assert count == len(expected_days) * 7
    assert ctx.demo.generate(count, start, end, ["U1"], seed=41) == count

    rows, total = ctx.inspections.query(
        RecordFilter(source="demo", page_size=100_000, descending=False)
    )
    assert total == count
    dates = [date.fromisoformat(row["inspection_date"]) for row in rows]
    assert set(dates) == set(expected_days)
    assert {day.month for day in dates} == set(range(1, 13))
    assert all(day.weekday() < 5 for day in dates)

    per_day = {day: dates.count(day) for day in set(dates)}
    assert set(per_day.values()) == {7}
    assert all(
        row["work_order"].startswith(
            f"DEMO-{date.fromisoformat(row['inspection_date']):%Y%m}-"
        )
        for row in rows
    )


def test_historical_demo_completion_opens_matching_analysis_range(ctx, qtbot):
    start, end = date(2024, 5, 1), date(2024, 5, 7)
    count = ctx.demo.generate(
        12,
        start,
        end,
        ["U1"],
        rework_rate=0.1,
        defect_rate=0.02,
        seed=11,
    )
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    window.show_demo_data(count, start, end)

    analytics = window.pages[3]
    assert window.stack.currentIndex() == 3
    assert analytics.preset.currentText() == "自定义"
    assert analytics.source.currentText() == "演示数据"
    assert analytics.start.date().toPython() == start
    assert analytics.end.date().toPython() == end
    assert f"{start} 至 {end}" in analytics.scope.text()
    assert analytics.teams_table.rowCount() > 0
    assert "已生成 12 条演示记录" in window.statusBar().currentMessage()



def test_demo_range_spanning_current_month_opens_full_analytics_range(ctx, qtbot):
    from datetime import timedelta

    today = date.today()
    start = today.replace(day=1) - timedelta(days=1)
    start = start.replace(day=1)
    end = today
    count = ctx.demo.generate(
        10,
        start,
        end,
        ["U1"],
        rework_rate=0.1,
        defect_rate=0.02,
        seed=17,
    )
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    window.show_demo_data(count, start, end)

    analytics = window.pages[3]
    assert window.stack.currentIndex() == 3
    assert analytics.source.currentText() == "演示数据"
    assert analytics.start.date().toPython() == start
    assert analytics.end.date().toPython() == end


def test_demo_dialog_rejects_invalid_options_before_background_job(
    ctx, qtbot, monkeypatch
):
    from PySide6.QtCore import QDate

    import app.ui.dialogs.demo_dialog as module

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    dialog = DemoDialog(ctx, window)
    qtbot.addWidget(dialog)
    errors = []
    monkeypatch.setattr(module, "friendly_error", lambda parent, error: errors.append(str(error)))

    dialog.start.setDate(QDate(2026, 2, 2))
    dialog.end.setDate(QDate(2026, 2, 1))
    dialog.accept()
    assert errors[-1] == "开始日期不能晚于结束日期"

    dialog.start.setDate(QDate(2026, 2, 1))
    for checkbox in dialog.teams:
        checkbox.setChecked(False)
    dialog.accept()
    assert errors[-1] == "请至少选择一个参与组别"

    dialog.teams[0].setChecked(True)
    for _, weight in dialog.items:
        weight.setValue(0)
    dialog.accept()
    assert errors[-1] == "请至少为一个不良项目设置大于 0 的相对频率"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 6, 1), date(2026, 6, 10)),
        (date(2026, 6, 20), date(2026, 6, 25)),
    ],
)
def test_same_month_demo_range_outside_today_opens_exact_analysis_range(
    ctx, qtbot, monkeypatch, start, end
):
    import app.ui.main_window as main_window_module

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 15)

    monkeypatch.setattr(main_window_module, "date", FixedDate)
    window = MainWindow(ctx)
    qtbot.addWidget(window)

    window.show_demo_data(3, start, end)

    analytics = window.pages[3]
    assert window.stack.currentIndex() == 3
    assert analytics.preset.currentText() == "自定义"
    assert analytics.source.currentText() == "演示数据"
    assert analytics.start.date().toPython() == start
    assert analytics.end.date().toPython() == end
    assert f"{start} 至 {end}" in analytics.scope.text()
