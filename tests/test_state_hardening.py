from datetime import date

import pytest
from openpyxl import Workbook

from app.ui.main_window import MainWindow

HEADERS = [
    "填写ID",
    "时间",
    "组别",
    "加工单号",
    "检验数量",
    "抽检数",
    "不良数",
    "不良项目",
    "判定",
    "检验员",
]


def test_import_prefers_visible_record_sheet_over_hidden_named_legacy_sheet(ctx, tmp_path):
    from datetime import datetime

    path = tmp_path / "mixed-sheets.xlsx"
    wb = Workbook()
    hidden = wb.active
    hidden.title = "成品日检表"
    hidden.append(HEADERS)
    hidden.append(["HIDDEN-OLD", datetime(2026, 1, 5), "U1", "OLD", 100, 20, 0, "", "合格", "旧"])
    hidden.sheet_state = "hidden"
    visible = wb.create_sheet("检验记录")
    visible.append(HEADERS)
    visible.append(["VISIBLE-NEW", datetime(2026, 1, 5), "U1", "NEW", 100, 20, 0, "", "合格", "新"])
    wb.active = visible
    wb.save(path)
    wb.close()

    preview = ctx.excel.preview(path)
    assert preview.sheet == "检验记录"
    assert preview.counts["valid"] == 1
    assert preview.rows[0].inspection_no == "VISIBLE-NEW"


def test_dashboard_refresh_updates_displayed_calendar_date(ctx, qtbot, monkeypatch):
    import app.ui.pages.dashboard_page as module

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[0]

    class NextDay(date):
        @classmethod
        def today(cls):
            return cls(2031, 2, 3)

    monkeypatch.setattr(module, "date", NextDay)
    page.today_label.setText("旧日期")
    page.refresh()
    assert page.today_label.text() == "2031 年 02 月 03 日"


def test_analytics_marks_results_stale_when_filters_change(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(3)
    page = window.pages[3]

    assert page.scope.text().startswith("当前范围：")
    page.source.setCurrentIndex(1)
    assert "筛选条件已更改" in page.scope.text()
    page.refresh()
    assert page.scope.text().startswith("当前范围：")
    assert "演示数据" in page.scope.text()
    page.metric_choice.setCurrentIndex(1)
    assert "筛选条件已更改" in page.scope.text()


def test_settings_create_and_normalize_directories_and_reject_file_path(
    ctx, qtbot, monkeypatch, tmp_path
):
    import app.ui.common as common

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(6)
    page = window.pages[6]

    export_dir = tmp_path / "新目录" / "导出"
    backup_dir = tmp_path / "新目录" / "备份"
    page.fields["export_directory"].setText(str(export_dir))
    page.fields["backup_directory"].setText(str(backup_dir))
    page.save()

    assert export_dir.is_dir() and backup_dir.is_dir()
    assert ctx.settings.get("export_directory") == str(export_dir.resolve())
    assert ctx.settings.get("backup_directory") == str(backup_dir.resolve())

    not_a_directory = tmp_path / "这是文件"
    not_a_directory.write_text("x", encoding="utf-8")
    page.fields["export_directory"].setText(str(not_a_directory))
    errors = []
    monkeypatch.setattr(common, "friendly_error", lambda parent, error: errors.append(str(error)))
    page.save()

    assert errors == ["导出目录必须是文件夹，当前路径指向文件"]
    assert ctx.settings.get("export_directory") == str(export_dir.resolve())



def test_default_team_cannot_be_disabled_until_another_default_is_selected(ctx):
    team = next(item for item in ctx.settings.teams() if item["name"] == "U1")

    with pytest.raises(ValueError, match="默认组别不能停用"):
        ctx.settings.save_team(
            team["name"], team["id"], enabled=False, sort_order=team["sort_order"]
        )

    current = next(item for item in ctx.settings.teams() if item["id"] == team["id"])
    assert current["enabled"]
    assert ctx.settings.get("default_team") == "U1"

    ctx.settings.update({"default_team": "U2"})
    ctx.settings.save_team(
        team["name"], team["id"], enabled=False, sort_order=team["sort_order"]
    )
    current = next(item for item in ctx.settings.teams() if item["id"] == team["id"])
    assert not current["enabled"]



def test_analytics_resyncs_relative_range_on_refresh(ctx, qtbot, monkeypatch):
    from PySide6.QtCore import QDate

    import app.ui.pages.analytics_page as module

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[3]
    page.preset.setCurrentText("本月")
    page.start.setDate(QDate(2026, 1, 1))
    page.end.setDate(QDate(2026, 1, 31))
    monkeypatch.setattr(
        module,
        "date_range",
        lambda preset: (date(2031, 2, 1), date(2031, 2, 28)),
    )

    page.refresh()

    assert page.start.date().toPython() == date(2031, 2, 1)
    assert page.end.date().toPython() == date(2031, 2, 28)


def test_reports_resync_selected_year_on_refresh(ctx, qtbot):
    from PySide6.QtCore import QDate

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]
    page.preset.setCurrentText("全年")
    page.year.setValue(2031)
    page.start.setDate(QDate(2026, 1, 1))
    page.end.setDate(QDate(2026, 1, 31))

    page.refresh()

    assert page.start.date().toPython() == date(2031, 1, 1)
    assert page.end.date().toPython() == date(2031, 12, 31)



def test_analytics_invalid_custom_range_blocks_refresh_until_fixed(ctx, qtbot, monkeypatch):
    from PySide6.QtCore import QDate

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(3)
    page = window.pages[3]
    page.preset.setCurrentText("自定义")
    page.start.setDate(QDate(2026, 10, 2))
    page.end.setDate(QDate(2026, 10, 1))

    assert page.scope.text() == "日期范围无效：开始日期不能晚于结束日期"
    assert not page.analyze_button.isEnabled()

    called = []
    monkeypatch.setattr(
        ctx.statistics,
        "comparison",
        lambda *_: called.append(True) or pytest.fail("无效日期不应执行统计查询"),
    )
    page.refresh()
    assert not called
    assert page.scope.text() == "日期范围无效：开始日期不能晚于结束日期"

    page.end.setDate(QDate(2026, 10, 2))
    assert page.analyze_button.isEnabled()
    assert "筛选条件已更改" in page.scope.text()


def test_records_invalid_date_range_preserves_last_results_without_query(
    ctx, payload, qtbot, monkeypatch
):
    from PySide6.QtCore import QDate

    ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.navigate(2)
    page = window.pages[2]
    assert page.table.rowCount() == 1

    page.range_enabled.setChecked(True)
    page.start.setDate(QDate(2026, 10, 2))
    page.end.setDate(QDate(2026, 10, 1))
    assert not page.query_button.isEnabled()
    assert "日期范围无效" in page.count.text()
    assert "上一次查询结果" in page.count.text()

    called = []
    monkeypatch.setattr(
        ctx.inspections,
        "query",
        lambda *_: called.append(True) or pytest.fail("无效日期不应执行记录查询"),
    )
    page.refresh()
    assert not called
    assert page.table.rowCount() == 1

    page.end.setDate(QDate(2026, 10, 2))
    assert page.query_button.isEnabled()
    assert "点击“查询”应用" in page.count.text()
