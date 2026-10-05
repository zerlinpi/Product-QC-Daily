from datetime import date
from threading import Event

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QGroupBox

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
