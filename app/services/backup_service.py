import hashlib
import json
import logging
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from io import TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from app.database.migrations import SCHEMA_VERSION
from app.database.models import Base

log = logging.getLogger("qc.backup")

CHUNK_SIZE = 1024 * 1024
MAX_BACKUP_SIZE = 2_000_000_000
MAX_MANIFEST_SIZE = 1_000_000


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_checked(archive: ZipFile, info, target: Path, checksum: str) -> None:
    digest = hashlib.sha256()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with archive.open(info) as source, target.open("wb") as output:
            for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
                output.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != checksum:
            raise ValueError("备份校验失败，文件可能损坏")
    except Exception:
        target.unlink(missing_ok=True)
        raise


def verify_database(path: Path) -> list[str]:
    try:
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("备份数据库损坏")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("备份数据库关联数据损坏")
            version = connection.execute("SELECT max(version) FROM schema_version").fetchone()[0]
            if version != SCHEMA_VERSION:
                raise ValueError("备份数据库版本不兼容，请使用相应版本软件")
            if connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('trigger','view')"
            ).fetchone():
                raise ValueError("备份含不支持的数据库对象")
            for table in Base.metadata.sorted_tables:
                columns = {r[1] for r in connection.execute(f'PRAGMA table_info("{table.name}")')}
                if not {c.name for c in table.columns} <= columns:
                    raise ValueError("备份数据库结构不完整")
            names = [
                r[0]
                for r in connection.execute(
                    "SELECT DISTINCT signature_path FROM inspection_records WHERE signature_path IS NOT NULL"
                )
            ]
            if any(Path(name).name != name or not name.endswith(".png") for name in names):
                raise ValueError("备份签名路径无效")
            return names
    except sqlite3.Error as exc:
        raise ValueError("不是有效的日检系统数据库备份") from exc


class BackupService:
    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def directory(self) -> Path:
        path = Path(
            self.ctx.settings.get("backup_directory") or self.ctx.paths.backups
        ).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def backup(self, kind="manual", allow_missing=False) -> Path:
        if kind not in ("manual", "auto", "before_restore"):
            raise ValueError("备份类型无效")
        target = (
            self.directory
            / f"product_qc_{kind}_{datetime.now():%Y-%m-%d_%H%M%S}_{uuid4().hex[:6]}.zip"
        )
        temp = target.with_suffix(".tmp")
        try:
            with TemporaryDirectory(dir=self.ctx.paths.root) as directory:
                db = Path(directory) / "product_qc.db"
                with (
                    closing(sqlite3.connect(self.ctx.db.path)) as source,
                    closing(sqlite3.connect(db)) as output,
                ):
                    source.backup(output)
                names = verify_database(db)
                manifest = {
                    "format": 1,
                    "schema_version": SCHEMA_VERSION,
                    "created_at": datetime.now().isoformat(),
                    "files": {},
                    "missing_signatures": [],
                }
                with ZipFile(temp, "w", ZIP_DEFLATED) as archive:
                    files = {"product_qc.db": db}
                    for name in names:
                        path = self.ctx.paths.signatures / name
                        if path.is_file():
                            files[f"signatures/{name}"] = path
                        else:
                            manifest["missing_signatures"].append(name)
                    if manifest["missing_signatures"] and not allow_missing:
                        raise ValueError("部分签名文件丢失，请补充签名后重试完整备份")
                    for name, path in files.items():
                        manifest["files"][name] = file_sha256(path)
                        archive.write(path, arcname=name)
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
                temp.replace(target)
            log.info("备份 %s", target)
            return target
        finally:
            temp.unlink(missing_ok=True)

    def daily_backup(self) -> Path | None:
        if not self.ctx.settings.get("auto_backup"):
            return None
        today = date.today().isoformat()
        if list(self.directory.glob(f"product_qc_auto_{today}_*.zip")):
            return None
        path = self.backup("auto")
        self.cleanup(int(self.ctx.settings.get("backup_retention_days")))
        return path

    def cleanup(self, retention_days=30):
        cutoff = datetime.now() - timedelta(days=retention_days)
        for path in self.directory.glob("product_qc_auto_*.zip"):
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink()

    def restore(self, source: Path) -> Path:
        source = Path(source).resolve()
        created_signatures = []
        with TemporaryDirectory(dir=self.ctx.paths.root) as directory:
            stage = Path(directory)
            target_db = stage / "product_qc.db"
            try:
                if source.suffix.lower() == ".db":
                    shutil.copy2(source, target_db)
                    names = verify_database(target_db)
                    if names:
                        raise ValueError("该数据库引用签名，请使用包含签名的 ZIP 完整备份恢复")
                else:
                    with ZipFile(source) as archive:
                        infos = archive.infolist()
                        if sum(info.file_size for info in infos) > MAX_BACKUP_SIZE:
                            raise ValueError("备份文件过大")
                        if len({info.filename for info in infos}) != len(infos):
                            raise ValueError("备份文件包含重复条目")
                        entries = {info.filename: info for info in infos}
                        manifest_info = entries.get("manifest.json")
                        if manifest_info is None or manifest_info.file_size > MAX_MANIFEST_SIZE:
                            raise ValueError("备份清单无效")
                        with archive.open(manifest_info) as raw:
                            with TextIOWrapper(raw, encoding="utf-8") as stream:
                                manifest = json.load(stream)
                        if manifest.get("format") != 1 or "product_qc.db" not in manifest.get(
                            "files", {}
                        ):
                            raise ValueError("备份清单无效")
                        for name, checksum in manifest["files"].items():
                            valid = name == "product_qc.db" or (
                                name.startswith("signatures/")
                                and Path(name).name == name.removeprefix("signatures/")
                                and name.endswith(".png")
                            )
                            if not valid:
                                raise ValueError("备份含不安全文件路径")
                            info = entries.get(name)
                            if info is None or info.is_dir():
                                raise KeyError(name)
                            extract_checked(archive, info, stage / name, checksum)
                    names = verify_database(target_db)
                    if any(not (stage / "signatures" / name).is_file() for name in names):
                        raise ValueError("备份缺少签名文件，当前数据库保持不变")
            except (BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
                raise ValueError("无法读取完整备份；当前数据库保持不变") from exc
            # Preserve current database before the first mutation, including a damaged-media state.
            before = self.backup("before_restore", allow_missing=True)
            self.ctx.db.dispose()
            current = self.ctx.db.path
            rollback = stage / "previous.db"
            with closing(sqlite3.connect(current)) as connection:
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            try:
                for name in names:
                    target = self.ctx.paths.signatures / name
                    incoming = stage / "signatures" / name
                    if target.exists():
                        if file_sha256(target) != file_sha256(incoming):
                            raise ValueError("签名文件同名但内容不同，取消恢复")
                    else:
                        shutil.copy2(incoming, target)
                        created_signatures.append(target)
                os.replace(current, rollback)
                for suffix in ("-wal", "-shm"):
                    Path(str(current) + suffix).unlink(missing_ok=True)
                os.replace(target_db, current)
                self.ctx.db.health_check()
            except Exception:
                self.ctx.db.dispose()
                if rollback.exists():
                    for suffix in ("-wal", "-shm"):
                        Path(str(current) + suffix).unlink(missing_ok=True)
                    os.replace(rollback, current)
                for path in created_signatures:
                    path.unlink(missing_ok=True)
                raise
        log.info("恢复 %s；恢复前备份 %s", source, before)
        return before
