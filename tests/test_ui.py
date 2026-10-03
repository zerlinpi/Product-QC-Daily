from PySide6.QtCore import Qt


def test_ui_entry_save_and_reopen_without_duplicate(ctx, qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.show()
    window.navigate(1)
    entry = window.pages[1]
    entry.work_order.setText("UI-100")
    entry.inspector.setText("王工")
    entry.inspection_quantity.setValue(100)
    entry.sampling_quantity.setValue(20)
    entry.save_record()
    saved_id = entry.record_id
    assert saved_id
    entry.work_order.setText("UI-101")
    entry.save_record()
    from app.core.schemas import RecordFilter

    assert ctx.inspections.query(RecordFilter())[1] == 1
    assert ctx.inspections.get(saved_id)["work_order"] == "UI-101"
    entry.save_record(new=True)
    assert entry.record_id is None
    assert entry.team.currentText() == "U1"
    assert entry.inspector.text() == "王工"
    assert ctx.inspections.query(RecordFilter())[1] == 1
    # Open again against the same persistent context.
    window.close()
    again = MainWindow(ctx)
    qtbot.addWidget(again)
    again.navigate(2)
    assert again.pages[2].table.rowCount() == 1


def test_navigation_all_pages_empty_database(ctx, qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.show()
    for i in range(7):
        window.navigate(i)
        assert window.stack.currentIndex() == i
        if i == 1:
            assert not window.pages[1].dirty


def test_copy_selection_creates_new_record_and_preserves_original(ctx, payload, qtbot):
    from app.core.schemas import RecordFilter
    from app.ui.main_window import MainWindow

    saved = ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.open_record(saved["id"], copy_record=True)
    entry = window.pages[1]
    assert entry.record_id is None
    entry.work_order.setText("COPY-2")
    entry.save_record()
    assert ctx.inspections.query(RecordFilter())[1] == 2
    assert ctx.inspections.get(saved["id"])["work_order"] == "MO-001"


def test_defect_selector_counts_and_unknown(ctx, qtbot):
    from app.ui.widgets.defect_selector import DefectSelector

    widget = DefectSelector(ctx)
    qtbot.addWidget(widget)
    widget.set_values([{"defect_id": 5, "quantity": 2}, {"defect_id": 7, "quantity": None}])
    values = widget.values()
    assert {(v["defect_id"], v["quantity"]) for v in values} == {(5, 2), (7, None)}


def test_keyboard_save_and_new(ctx, qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.show()
    window.navigate(1)
    entry = window.pages[1]
    entry.work_order.setText("KEYBOARD")
    entry.inspector.setText("工人")
    entry.inspection_quantity.setValue(100)
    entry.sampling_quantity.setValue(20)
    entry.work_order.setFocus()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    qtbot.wait(50)
    qtbot.keyClick(entry.work_order, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(lambda: entry.record_id is not None)
    qtbot.keyClick(entry.work_order, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    assert entry.record_id is None


def test_confirmed_discard_restores_saved_record(ctx, payload, qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from app.ui.main_window import MainWindow

    saved = ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.open_record(saved["id"])
    entry = window.pages[1]
    entry.work_order.setText("ABANDONED")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
    window.navigate(2)
    window.navigate(1)
    assert entry.work_order.text() == "MO-001"
    entry.save_record()
    assert ctx.inspections.get(saved["id"])["work_order"] == "MO-001"


def test_editor_preserves_per_defect_remarks(ctx, payload, qtbot):
    from app.core.schemas import InspectionInput
    from app.ui.main_window import MainWindow

    saved = ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "defect_quantity": 1,
                    "defects": [{"defect_id": 5, "quantity": 1, "remark": "已返修确认"}],
                }
            )
        )
    )
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.open_record(saved["id"])
    window.pages[1].defects.reload()
    window.pages[1].save_record()
    assert ctx.inspections.get(saved["id"])["defects"][0]["remark"] == "已返修确认"


def test_required_popup_names_every_missing_field_in_chinese(ctx, qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from app.core.schemas import RecordFilter
    from app.ui.main_window import MainWindow

    window = MainWindow(ctx)
    qtbot.addWidget(window, before_close_func=lambda w: setattr(w.pages[1], "dirty", False))
    window.navigate(1)
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: messages.append(text))
    entry = window.pages[1]
    entry.team.setCurrentIndex(-1)
    entry.work_order.setText("  ")
    entry.inspector.clear()
    entry.inspection_quantity.setValue(0)
    entry.sampling_quantity.setValue(0)
    entry.save_record()
    assert len(messages) == 1
    for name in ("组别", "加工单号", "检验员", "检验数量", "抽检数量"):
        assert name in messages[0]
    assert "大于 0" in messages[0]
    assert "String should" not in messages[0]
    assert "Input should" not in messages[0]
    assert ctx.inspections.query(RecordFilter())[1] == 0


def test_record_source_cells_use_chinese(ctx, payload, qtbot):
    from app.core.schemas import InspectionInput
    from app.ui.main_window import MainWindow

    for source in ("manual", "excel", "demo"):
        ctx.inspections.save(InspectionInput(**(payload.model_dump() | {"source": source})))
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[2]
    page.source.setCurrentIndex(2)
    page.refresh()
    assert {page.table.item(r, 9).text() for r in range(3)} == {"手动录入", "表格导入", "演示数据"}


def test_record_export_defaults_to_original_layout(ctx, payload, qtbot, monkeypatch, tmp_path):
    from openpyxl import load_workbook
    from PySide6.QtWidgets import QFileDialog

    from app.ui.main_window import MainWindow

    ctx.inspections.save(payload)
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    page = window.pages[2]
    page.refresh()
    output = tmp_path / "ui-export.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    monkeypatch.setattr(window, "run_job", lambda title, work, done: done(work()))
    page.export()
    wb = load_workbook(output)
    assert "成品日检表" in wb.sheetnames
    assert "数据分析表" in wb.sheetnames
    wb.close()
