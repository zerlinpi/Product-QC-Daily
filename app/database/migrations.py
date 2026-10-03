import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.database.models import Base, DefectItem, SchemaVersion, Team

SCHEMA_VERSION = 1
DEFECT_NAMES = [
    "端子包角不良",
    "走线槽漏扎带",
    "漏锁片",
    "漏扣卡扣",
    "漏剪扎带",
    "插入不足",
    "漏胶",
    "组付漏扎带",
    "漏海绵",
    "组付尺寸不良",
    "走线槽尺寸不良",
    "热缩管不良",
    "端子反插",
    "端子变形",
    "漏装塑壳",
    "标签贴错",
    "塑壳用错（国产与进口混用或用相似塑壳）",
    "护套用错",
    "扎带松",
    "线剪断",
    "防水塞未装到位",
    "塑壳坏",
    "端子浅压",
    "端子深压",
]


def migrate(engine, path: Path) -> None:
    tables = inspect(engine).get_table_names()
    with Session(engine) as session:
        current = (
            session.scalar(select(SchemaVersion.version).order_by(SchemaVersion.version.desc()))
            if "schema_version" in tables
            else 0
        )
    current = current or 0
    if current > SCHEMA_VERSION:
        raise ValueError("数据库来自更高版本，请使用新版软件打开")
    if tables and not current:
        raise ValueError("数据库结构无法识别；请恢复有效备份，不会自动覆盖现有数据")
    if current == SCHEMA_VERSION:
        return
    if tables:
        backup = path.with_name(f"migration_{datetime.now():%Y%m%d_%H%M%S}.db")
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
    # Future migrations are explicit, ordered transactions. Never drop existing tables.
    if current == 0:
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
            with Session(bind=connection) as session:
                session.add(SchemaVersion(version=1))
                session.add_all(Team(name=f"U{i}", sort_order=i) for i in range(1, 9))
                session.add_all(
                    DefectItem(code=chr(97 + i), name=name, sort_order=i + 1)
                    for i, name in enumerate(DEFECT_NAMES)
                )
                session.flush()
        logging.getLogger("qc.database").info("数据库初始化 schema=%s", SCHEMA_VERSION)
