from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QListView,
    QMessageBox,
)

from app.ui.dialogs import file_dialogs
from app.ui.main_window import MainWindow


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_file_picker_sidebar_remains_legible_in_each_theme(ctx, qtbot, mode):
    ctx.settings.update({"theme": mode})
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    picker = QFileDialog(window)
    qtbot.addWidget(picker)
    picker.show()
    QApplication.processEvents()
    sidebar = picker.findChild(QListView, "sidebar")
    # The app navigation colour used to leak into Qt's equally named sidebar.
    assert sidebar.palette().color(QPalette.ColorRole.Base) == QApplication.palette().color(
        QPalette.ColorRole.Base
    )
    assert sidebar.palette().color(QPalette.ColorRole.Text) != sidebar.palette().color(
        QPalette.ColorRole.Base
    )


@pytest.mark.parametrize("page_index", [2, 5])
def test_export_dialog_uses_missing_configured_directory_and_cancel_does_not_export(
    ctx, payload, qtbot, monkeypatch, tmp_path, page_index
):
    target = tmp_path / "新导出目录" / "十月"
    ctx.settings.update({"export_directory": str(target)})
    ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[page_index]
    page.refresh()
    jobs = []
    monkeypatch.setattr(window, "run_job", lambda *args: jobs.append(args))
    observed = {}

    def cancel():
        picker = QApplication.activeModalWidget()
        observed["directory"] = Path(picker.directory().absolutePath())
        observed["sidebar_width"] = picker.findChild(QListView, "sidebar").width()
        observed["default_suffix"] = picker.defaultSuffix()
        buttons = picker.findChild(QDialogButtonBox)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).click()

    QTimer.singleShot(100, cancel)
    if page_index == 2:
        page.export()
    else:
        page.export(True)
    assert observed["directory"] == target
    assert observed["sidebar_width"] >= 128
    assert observed["default_suffix"] == "xlsx"
    assert jobs == []
    assert not list(target.glob("*.xlsx"))


@pytest.mark.parametrize("detailed", [False, True])
def test_real_export_dialog_navigates_and_saves_chinese_filename_with_suffix(
    ctx, payload, qtbot, monkeypatch, tmp_path, detailed
):
    from openpyxl import load_workbook

    target = tmp_path / "十月报表"
    target.mkdir()
    ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[2]
    page.refresh()
    monkeypatch.setattr(window, "run_job", lambda title, work, done: done(work()))
    observed = {}

    def save():
        picker = QApplication.activeModalWidget()
        try:
            entry = picker.findChild(QLineEdit, "fileNameEdit")
            button = picker.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save)
            # Typing a folder and pressing Save must navigate, not export a file.
            entry.setText(str(target))
            button.click()
            observed["directory"] = Path(picker.directory().absolutePath())
            picker.findChild(QComboBox, "fileTypeCombo").setCurrentIndex(int(detailed))
            entry.setText("中文日检报告")
            button.click()
        finally:
            if picker.isVisible():
                picker.reject()

    QTimer.singleShot(100, save)
    page.export()
    assert observed["directory"] == target
    output = target / "中文日检报告.xlsx"
    wb = load_workbook(output)
    title = "检验记录" if detailed else "成品日检表"
    assert wb.active.title == title
    assert wb[title]["D2"].value == payload.work_order
    wb.close()


@pytest.mark.parametrize("replace", [False, True])
def test_save_dialog_confirms_overwrite_after_adding_xlsx_suffix(ctx, qtbot, tmp_path, replace):
    output = tmp_path / "已有报告.xlsx"
    output.write_bytes(b"existing report must remain until an explicit export")
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    observed = []
    attempts = 0
    timer = QTimer()

    def choose():
        nonlocal attempts
        attempts += 1
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QMessageBox):
            observed.append("overwrite")
            dialog.button(
                QMessageBox.StandardButton.Yes if replace else QMessageBox.StandardButton.No
            ).click()
        elif isinstance(dialog, QFileDialog):
            if observed or attempts > 100:
                dialog.reject()
            else:
                dialog.findChild(QLineEdit, "fileNameEdit").setText(output.stem)
                # The click opens a nested confirmation loop before this timer
                # callback returns, so use a separate timer for that dialog.
                QTimer.singleShot(20, choose)
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()

    timer.timeout.connect(choose)
    timer.start(20)
    try:
        path, _ = file_dialogs.save_excel(window, "导出报表", output, "电子表格 (*.xlsx)")
    finally:
        timer.stop()
    assert observed == ["overwrite"]
    assert path == (str(output) if replace else "")
    assert output.read_bytes() == b"existing report must remain until an explicit export"


def test_windows_desktop_save_dialog_prefers_native_picker(monkeypatch):
    monkeypatch.setattr(file_dialogs.sys, "platform", "win32")
    monkeypatch.setenv("QT_QPA_PLATFORM", "windows")
    assert file_dialogs._use_native_windows_dialog()

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    assert not file_dialogs._use_native_windows_dialog()
