"""Desktop entry point; all user data remains outside the installation."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QFileDialog, QMessageBox

from app import __version__
from app.core.context import AppContext
from app.core.logger import setup_logging
from app.core.paths import AppPaths, resource_path
from app.core.schemas import InspectionInput, RecordFilter
from app.ui.common import friendly_error
from app.ui.localization import configure_chinese_ui
from app.ui.main_window import MainWindow


def smoke_test(ctx: AppContext, app: QApplication, report_path: Path | None) -> int:
    """Real packaged-EXE test using an explicitly isolated data directory."""
    if not os.environ.get("QC_DATA_DIR"):
        raise ValueError("自检必须通过 QC_DATA_DIR 指定独立测试目录")
    record = ctx.inspections.save(
        InspectionInput(
            team="U1",
            work_order="PACKAGED-SMOKE",
            inspection_quantity=100,
            sampling_quantity=20,
            inspector="打包自检",
            source="demo",
        )
    )
    ctx.db.dispose()
    reopened = AppContext(ctx.paths.root)
    assert reopened.inspections.get(record["id"])["work_order"] == "PACKAGED-SMOKE"
    window = MainWindow(reopened)
    controls = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, window
    )
    assert "保存" in controls.button(QDialogButtonBox.StandardButton.Save).text()
    assert "取消" in controls.button(QDialogButtonBox.StandardButton.Cancel).text()
    picker = QFileDialog(window)
    assert "位置" in picker.labelText(QFileDialog.DialogLabel.LookIn)
    controls.deleteLater()
    picker.deleteLater()
    window.show()
    for index in range(7):
        window.navigate(index)
        app.processEvents()
    output = reopened.excel.export(
        ctx.paths.exports / "smoke.xlsx", RecordFilter(source="demo"), legacy=True, prefer_com=False
    )
    assert output.exists()
    backup = reopened.backup.backup()
    reopened.backup.restore(backup)
    window.close()
    reopened.db.dispose()
    result = {
        "ok": True,
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "pages": 7,
        "database_persistence": True,
        "template_export": True,
        "backup_restore": True,
        "chinese_controls": True,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.self_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    configure_chinese_ui(app)
    app.setApplicationName("Product-QC-Daily")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Product-QC-Daily")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setWindowIcon(QIcon(str(resource_path("assets/icons/app.svg"))))
    ctx = None
    try:
        paths = AppPaths()
        setup_logging(paths.logs)
        lock = QLockFile(str(paths.root / "application.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            if args.self_test:
                raise ValueError("同一数据目录已有正在运行的软件实例")
            QMessageBox.information(
                None, "软件已运行", "此数据目录已有日检软件在运行，请返回已打开的窗口。"
            )
            return 1
        ctx = AppContext(paths.root)
        logging.getLogger("qc").info("启动 v%s", __version__)
        if args.self_test:
            return smoke_test(ctx, app, args.report)
        window = MainWindow(ctx)
        sys.excepthook = lambda kind, error, traceback: friendly_error(window, error)
        window.show()
        QTimer.singleShot(
            200,
            lambda: window.run_job(
                "检查每日备份",
                ctx.backup.daily_backup,
                lambda path: window.notify("每日备份已完成" if path else "本地数据库已就绪"),
            ),
        )
        return app.exec()
    except Exception as error:
        if args.self_test:
            logging.getLogger("qc").exception("自检失败")
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(
                    json.dumps({"ok": False, "error": str(error)}), encoding="utf-8"
                )
        else:
            friendly_error(None, error)
        return 1
    finally:
        if ctx:
            ctx.db.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
