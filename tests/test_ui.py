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
