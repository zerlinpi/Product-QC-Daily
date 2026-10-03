from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.database.migrations import migrate


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.path.as_posix()}", connect_args={"timeout": 10}
        )

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.health_check()
        migrate(self.engine, self.path)

    @contextmanager
    def session(self):
        with self.sessions.begin() as session:
            yield session

    def health_check(self) -> str:
        with self.engine.connect() as connection:
            result = connection.execute(text("PRAGMA integrity_check")).scalar()
            foreign = connection.execute(text("PRAGMA foreign_key_check")).first()
        if result != "ok" or foreign:
            raise ValueError("数据库完整性检查未通过，请保留文件并恢复备份")
        return "ok"

    def dispose(self) -> None:
        self.engine.dispose()
