from datetime import date
from pathlib import Path

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
