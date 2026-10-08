"""Synthetic Linux/Qt export measurements; does not access user data."""

import argparse
import gc
import json
import os
import platform
import tempfile
import threading
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from openpyxl.workbook.workbook import Workbook
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sqlalchemy import text

from app.core.context import AppContext
from app.core.schemas import RecordFilter
from app.services import excel_export
from app.ui.main_window import MainWindow


def rss_bytes():
    # Sampling resident memory measures native Qt/openpyxl buffers as well.
    status = Path("/proc/self/status").read_text()
    return (
        int(next(line.split()[1] for line in status.splitlines() if line.startswith("VmRSS:")))
        * 1024
    )


def measure(count, legacy, app):
    with tempfile.TemporaryDirectory(prefix="qc-export-bench-") as directory:
        ctx = AppContext(Path(directory))
        filters = RecordFilter(
            start="2026-01-01", end="2026-12-31", source="demo", descending=False
        )
        ctx.demo.generate(count, filters.start, filters.end, ["U1", "U2", "U3"], seed=45)
        signature = ctx.paths.signatures / "synthetic.png"
        Image.new("RGB", (300, 80), "white").save(signature)
        with ctx.db.session() as session:
            session.execute(
                text(
                    "UPDATE inspection_records SET signature_path='synthetic.png' WHERE id % 100 = 0"
                )
            )
        ctx.settings.update({"auto_backup": False})
        window = MainWindow(ctx)
        window.resize(1080, 720)
        window.show()
        app.processEvents()
        metrics = {
            "count": count,
            "format": "legacy" if legacy else "standard",
            "signature_count": count // 100,
        }
        elapsed = {
            "sqlite_query_seconds": 0.0,
            "chart_seconds": 0.0,
            "style_seconds": 0.0,
            "save_seconds": 0.0,
        }
        original_iter = ctx.inspections.iter_records

        def timed_iter(filters):
            iterator = iter(original_iter(filters))
            try:
                while True:
                    start = perf_counter()
                    try:
                        row = next(iterator)
                    except StopIteration:
                        elapsed["sqlite_query_seconds"] += perf_counter() - start
                        break
                    elapsed["sqlite_query_seconds"] += perf_counter() - start
                    yield row
            finally:
                iterator.close()

        def timed(function, key):
            def wrapped(*args, **kwargs):
                start = perf_counter()
                try:
                    return function(*args, **kwargs)
                finally:
                    elapsed[key] += perf_counter() - start

            return wrapped

        patches = [
            patch.object(ctx.inspections, "iter_records", timed_iter),
            patch.object(
                excel_export, "style_table", timed(excel_export.style_table, "style_seconds")
            ),
            patch.object(Workbook, "save", timed(Workbook.save, "save_seconds")),
        ]
        for name in (
            "add_monthly_analysis",
            "repair_analysis",
            "embed_legacy_analysis_chart_data",
            "label_legacy_chart_scope",
        ):
            patches.append(
                patch.object(
                    excel_export, name, timed(getattr(excel_export, name), "chart_seconds")
                )
            )
        stop = threading.Event()
        memory = [rss_bytes()]

        def sample():
            while not stop.wait(0.02):
                memory[0] = max(memory[0], rss_bytes())

        sampler = threading.Thread(target=sample, daemon=True)
        beats = []
        timer = QTimer()
        timer.setInterval(20)
        timer.timeout.connect(lambda: beats.append(perf_counter()))
        result = []

        def work():
            try:
                return ctx.excel.export(
                    Path(directory) / "report.xlsx",
                    filters,
                    legacy=legacy,
                    prefer_com=False,
                    expected_count=count,
                )
            except Exception as exc:
                return exc

        def done(value):
            result.append(value)
            app.quit()

        try:
            for patcher in patches:
                patcher.start()
            gc.collect()
            start = perf_counter()
            sampler.start()
            timer.start()
            window.run_job("导出性能验收", work, done)
            app.exec()
            end = perf_counter()
            if not result or isinstance(result[0], Exception):
                raise RuntimeError(result)
            boundaries = [start, *beats, end]
            metrics.update(elapsed)
            metrics.update(
                {
                    "total_seconds": end - start,
                    "excel_write_seconds": end
                    - start
                    - elapsed["sqlite_query_seconds"]
                    - elapsed["chart_seconds"],
                    "peak_rss_mib": memory[0] / 1024**2,
                    "file_bytes": result[0].stat().st_size,
                    "ui_timer_events": len(beats),
                    "ui_max_gap_seconds": max(b - a for a, b in zip(boundaries, boundaries[1:])),
                }
            )
            return metrics
        finally:
            timer.stop()
            stop.set()
            sampler.join()
            for patcher in reversed(patches):
                patcher.stop()
            window.close()
            window.deleteLater()
            app.processEvents()
            ctx.db.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "measurement": "shared Linux runner, real Qt worker, 1% synthetic signatures, RSS sampled every 20ms",
        "cases": [],
    }
    for count in (500, 1825, 5000, 10000):
        for legacy in (True, False):
            metric = measure(count, legacy, app)
            result["cases"].append(metric)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(metric), flush=True)
