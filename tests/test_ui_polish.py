import pytest
from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import QDialogButtonBox, QFileDialog, QPushButton

from app.ui.dialogs import file_dialogs
from app.ui.main_window import MainWindow


def test_standard_controls_are_chinese_even_on_english_system(ctx, qtbot):
    QLocale.setDefault(QLocale("en_US"))
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, window
    )
    assert "保存" in buttons.button(QDialogButtonBox.StandardButton.Save).text()
    assert "取消" in buttons.button(QDialogButtonBox.StandardButton.Cancel).text()
    picker = QFileDialog(window)
    assert "文件" in picker.labelText(QFileDialog.DialogLabel.FileName)
    assert "位置" in picker.labelText(QFileDialog.DialogLabel.LookIn)
    assert "类型" in picker.labelText(QFileDialog.DialogLabel.FileType)
    assert window.pages[1].inspection_date.locale().language() == QLocale.Language.Chinese


def test_custom_report_dates_update_visible_export_scope(ctx, qtbot):
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[5]
    page.preset.setCurrentText("自定义")
    page.start.setDate(QDate(2025, 12, 30))
    page.end.setDate(QDate(2026, 1, 3))
    assert "2025-12-30 至 2026-01-03" in page.export_scope.text()


@pytest.mark.parametrize("detailed", [False, True])
def test_export_selection_uses_displayed_rows_not_unapplied_filters(
    ctx, payload, qtbot, monkeypatch, tmp_path, detailed
):
    from openpyxl import load_workbook

    ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[2]
    page.refresh()
    page.table.selectRow(0)
    page.source.setCurrentText("演示数据")
    output = tmp_path / "selected.xlsx"
    monkeypatch.setattr(
        file_dialogs,
        "save_excel",
        lambda *args: (str(output), "明细报表 (*.xlsx)" if detailed else "原表格式 (*.xlsx)"),
    )
    monkeypatch.setattr(window, "run_job", lambda title, work, done: done(work()))
    page.export()
    wb = load_workbook(output)
    sheet = wb["检验记录" if detailed else "成品日检表"]
    assert "MO-001" in [cell.value for cell in sheet[2]]
    assert ("不良明细" in wb.sheetnames) is detailed
    wb.close()


def test_recycle_bin_switch_refreshes_rows_and_available_actions(ctx, payload, qtbot):
    from app.core.schemas import InspectionInput

    ctx.inspections.save(payload)
    deleted = ctx.inspections.save(
        InspectionInput(**(payload.model_dump() | {"work_order": "DELETED"}))
    )
    ctx.inspections.delete([deleted["id"]])
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[2]
    page.refresh()
    page.table.selectRow(0)
    page.trash.setChecked(True)
    assert [r["work_order"] for r in page.rows] == ["DELETED"]
    assert not page.selected_ids()
    page.table.selectRow(0)
    assert page.action_buttons["restore"].isEnabled()
    assert not page.action_buttons["edit"].isEnabled()
    assert not page.action_buttons["copy"].isEnabled()


def test_dashboard_new_inspection_does_not_reopen_previous_saved_record(ctx, payload, qtbot):
    saved = ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window, before_close_func=lambda w: setattr(w.pages[1], "dirty", False))
    window.open_record(saved["id"])
    window.navigate(0)
    control = next(b for b in window.pages[0].findChildren(QPushButton) if "新建检验" in b.text())
    qtbot.mouseClick(control, Qt.MouseButton.LeftButton)
    assert window.stack.currentIndex() == 1
    assert window.pages[1].record_id is None
    assert ctx.inspections.get(saved["id"])["work_order"] == "MO-001"


@pytest.mark.parametrize("accept", [False, True])
def test_confirmation_defaults_to_cancel_and_requires_explicit_acceptance(qtbot, accept):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from app.ui.common import confirm

    seen = {}

    def choose():
        dialog = QApplication.activeModalWidget()
        seen["default"] = dialog.defaultButton().text()
        chosen = next(
            b
            for b in dialog.buttons()
            if dialog.buttonRole(b)
            == (QMessageBox.ButtonRole.AcceptRole if accept else QMessageBox.ButtonRole.RejectRole)
        )
        chosen.click()

    QTimer.singleShot(0, choose)
    assert confirm(None, "移入回收站", "将所选记录移入回收站？", action="移入回收站") is accept
    assert seen["default"] == "取消"


def test_import_preview_pagination_matches_available_rows(ctx, qtbot, tmp_path):
    from datetime import datetime

    from openpyxl import Workbook

    from app.ui.dialogs.import_dialog import ImportDialog

    path = tmp_path / "preview.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "成品日检表"
    ws.append(
        ["填写ID", "时间", "组别", "加工单号", "检验数量", "抽检数", "不良数", "不良项目", "判定"]
    )
    for i in range(201):
        ws.append([f"PREVIEW-{i}", datetime(2026, 1, 5), "U1", "MO-001", 100, 20, 0, "", "合格"])
    wb.save(path)
    wb.close()
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    dialog = ImportDialog(ctx, window, ctx.excel.preview(path))
    qtbot.addWidget(dialog)
    assert not dialog.previous_button.isEnabled()
    assert dialog.next_button.isEnabled()
    dialog.next_button.click()
    assert dialog.table.rowCount() == 1
    assert dialog.previous_button.isEnabled()
    assert not dialog.next_button.isEnabled()
    dialog.filter.setCurrentText("异常")
    assert dialog.table.rowCount() == 0
    assert not dialog.previous_button.isEnabled()
    assert not dialog.next_button.isEnabled()


def test_entry_footer_tracks_saved_modified_copied_and_new_records(ctx, payload, qtbot):
    saved = ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window, before_close_func=lambda w: setattr(w.pages[1], "dirty", False))
    page = window.pages[1]
    page.load_record(saved)
    assert "已保存" in page.saved_note.text()
    page.remark.setPlainText("修改后的备注")
    assert "修改尚未保存" in page.saved_note.text()
    page.refresh()
    assert "修改尚未保存" in page.saved_note.text()
    page.discard_changes()
    assert "已保存" in page.saved_note.text()
    page.load_record(saved, copy_record=True)
    assert "尚未保存" in page.saved_note.text()
    page.save_record()
    assert "保存成功" in page.saved_note.text()
    page.refresh()
    assert "保存成功" in page.saved_note.text()
    page.reset()
    assert "本条尚未保存" in page.saved_note.text()
