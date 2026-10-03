from datetime import date
from zipfile import ZipFile

import pytest


def test_live_backup_restore_includes_signatures_and_pre_restore_snapshot(ctx, payload, tmp_path):
    from PIL import Image

    from app.core.schemas import InspectionInput, RecordFilter

    signature = tmp_path / "sig.png"
    Image.new("RGB", (50, 20), "white").save(signature)
    saved = ctx.inspections.save(
        InspectionInput(**(payload.model_dump() | {"signature_path": str(signature)}))
    )
    backup = ctx.backup.backup()
    with ZipFile(backup) as z:
        assert f"signatures/{saved['signature_path']}" in z.namelist()
    ctx.inspections.save(payload)
    (ctx.paths.signatures / saved["signature_path"]).unlink()
    # Current data has missing media: preservation backup still keeps the current DB and reports it.
    pre_restore = ctx.backup.restore(backup)
    assert pre_restore.exists() and pre_restore != backup
    assert ctx.inspections.query(RecordFilter())[1] == 1
    assert (ctx.paths.signatures / saved["signature_path"]).exists()
    assert ctx.db.health_check() == "ok"


def test_corrupt_backup_cannot_replace_database(ctx, payload, tmp_path):
    from app.core.schemas import RecordFilter

    ctx.inspections.save(payload)
    corrupt = tmp_path / "invalid.zip"
    corrupt.write_bytes(b"broken")
    with pytest.raises(ValueError):
        ctx.backup.restore(corrupt)
    assert ctx.inspections.query(RecordFilter())[1] == 1


def test_daily_backup_once_and_retention_never_deletes_manual(ctx, payload):
    ctx.inspections.save(payload)
    first = ctx.backup.daily_backup()
    assert first and first.exists()
    assert ctx.backup.daily_backup() is None
    manual = ctx.backup.backup()
    ctx.backup.cleanup(retention_days=1)
    assert manual.exists()


def test_demo_is_labeled_valid_weighted_and_clear_preserves_production(ctx, payload):
    from app.core.schemas import RecordFilter

    ctx.inspections.save(payload)
    count = ctx.demo.generate(
        100,
        date(2026, 1, 1),
        date(2026, 1, 7),
        ["U2"],
        rework_rate=0.1,
        defect_rate=0.02,
        weights={24: 1},
    )
    assert count == 100
    assert ctx.inspections.query(RecordFilter())[1] == 1
    rows, total = ctx.inspections.query(RecordFilter(source="demo", page_size=100))
    assert total == 100 and {r["team"] for r in rows} == {"U2"}
    assert all(
        r["defect_quantity"] <= r["sampling_quantity"] <= r["inspection_quantity"] for r in rows
    )
    assert all(d["defect_id"] == 24 for r in rows for d in r["defects"])
    assert ctx.demo.clear() == 100
    assert ctx.inspections.query(RecordFilter(source="all"))[1] == 1


def test_future_schema_database_rejected_without_mutation(ctx, tmp_path):
    import sqlite3

    from app.database.db import Database

    target = tmp_path / "future.db"
    with sqlite3.connect(target) as c:
        c.executescript(
            "CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at TEXT); INSERT INTO schema_version VALUES (999,'2026-01-01');"
        )
    with pytest.raises(ValueError, match="更高版本"):
        Database(target)
    with sqlite3.connect(target) as c:
        assert c.execute("SELECT version FROM schema_version").fetchone()[0] == 999


def test_backup_restore_closes_owned_sqlite_handles(ctx, payload, monkeypatch):
    import sqlite3

    import app.services.backup_service as module

    ctx.inspections.save(payload)
    original = sqlite3.connect
    opened = []

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def close(self):
            super().close()
            self.closed = True

    def connect(*args, **kwargs):
        kwargs["factory"] = TrackedConnection
        connection = original(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(module.sqlite3, "connect", connect)
    try:
        path = ctx.backup.backup()
        assert all(connection.closed for connection in opened)
        ctx.backup.restore(path)
        assert all(connection.closed for connection in opened)
    finally:
        for connection in opened:
            connection.close()
