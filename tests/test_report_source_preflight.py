"""报表中心数据来源预检：全年不意味着自动包含全年演示记录。"""

from datetime import date

import pytest

from app.ui.dialogs import file_dialogs
from app.ui.main_window import MainWindow


@pytest.mark.parametrize("choice,expected_source", [("switch", "demo"), ("keep", "production")])
def test_annual_export_confirms_sparse_source_and_never_mixes_records(
    ctx, payload, qtbot, monkeypatch, tmp_path, choice, expected_source
):
    ctx.inspections.save(payload.model_copy(update={"inspection_date": date(2026, 10, 3)}))
    ctx.demo.generate(60, date(2026, 1, 1), date(2026, 12, 31), ["U1"], seed=42)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]
    page.year.setValue(2026)
    assert page.source.currentText() == "正式数据"
    assert "实际可导出 1 条" in page.export_counts.text()
    assert "正式数据 1 条 / 演示数据 60 条" in page.export_counts.text()

    confirmations = []
    monkeypatch.setattr(
        page, "_confirm_source_mismatch",
        lambda *args: confirmations.append(args) or choice,
    )
    target = tmp_path / "result.xlsx"
    monkeypatch.setattr(file_dialogs, "save_excel", lambda *args, **kwargs: (str(target), ""))
    captured = {}

    def fake_export(path, filters, legacy=False):
        captured["filters"] = filters
        return path

    monkeypatch.setattr(ctx.excel, "export", fake_export)
    monkeypatch.setattr(window, "run_job", lambda title, work, done: done(work()))
    page.export(False)
    assert confirmations == [("production", 1, 60)]
    assert captured["filters"].source == expected_source
    assert page.source.currentText() == ("演示数据" if choice == "switch" else "正式数据")
    assert (
        "实际可导出 60 条" if choice == "switch" else "实际可导出 1 条"
    ) in page.export_counts.text()


def test_annual_export_cancel_before_save_dialog_on_source_mismatch(
    ctx, payload, qtbot, monkeypatch
):
    ctx.demo.generate(40, date(2026, 1, 1), date(2026, 12, 31), ["U1"], seed=21)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]
    page.year.setValue(2026)
    assert "正式数据 0 条 / 演示数据 40 条" in page.export_counts.text()
    monkeypatch.setattr(page, "_confirm_source_mismatch", lambda *args: "cancel")
    monkeypatch.setattr(
        file_dialogs,
        "save_excel",
        lambda *args, **kwargs: pytest.fail("取消来源核对后不应创建或选择导出文件"),
    )
    page.export(True)


def test_report_count_feedback_refreshes_and_empty_range_can_still_export(
    ctx, payload, qtbot, monkeypatch, tmp_path
):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]
    page.year.setValue(2026)
    assert "正式数据 0 条 / 演示数据 0 条" in page.export_counts.text()
    assert page.original_export.isEnabled()
    ctx.inspections.save(payload.model_copy(update={"inspection_date": date(2026, 1, 5)}))
    page.refresh()
    assert "正式数据 1 条 / 演示数据 0 条" in page.export_counts.text()

    called = []
    monkeypatch.setattr(
        page, "_confirm_source_mismatch",
        lambda *args: pytest.fail("没有另一数据来源时不应提示切换"),
    )
    monkeypatch.setattr(
        file_dialogs, "save_excel", lambda *args, **kwargs: (str(tmp_path / "report.xlsx"), "")
    )
    monkeypatch.setattr(ctx.excel, "export", lambda path, filters, legacy=False: called.append(filters.source) or path)
    monkeypatch.setattr(window, "run_job", lambda title, work, done: done(work()))
    page.export(False)
    assert called == ["production"]
