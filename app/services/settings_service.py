import json

from sqlalchemy import select

from app.database.models import Setting, Team

DEFAULTS = {
    "company": "",
    "factory": "",
    "default_inspector": "",
    "default_team": "U1",
    "theme": "light",
    "auto_backup": True,
    "backup_retention_days": 30,
    "backup_directory": "",
    "export_directory": "",
    "template_path": "",
    "keep_fields": ["team", "work_order", "inspection_quantity", "sampling_quantity", "inspector"],
}


class SettingsService:
    def __init__(self, db):
        self.db = db

    def all(self) -> dict:
        with self.db.session() as session:
            return DEFAULTS | {
                row.key: json.loads(row.value) for row in session.scalars(select(Setting))
            }

    def get(self, key, default=None):
        return self.all().get(key, default)

    def update(self, values: dict) -> None:
        if (
            "backup_retention_days" in values
            and not 1 <= int(values["backup_retention_days"]) <= 3650
        ):
            raise ValueError("备份保留天数必须为 1–3650")
        if "theme" in values and values["theme"] not in ("light", "dark", "system"):
            raise ValueError("主题无效")
        with self.db.session() as session:
            for key, value in values.items():
                session.merge(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))

    def teams(self, enabled_only=False) -> list[dict]:
        with self.db.session() as session:
            stmt = select(Team).order_by(Team.sort_order, Team.name)
            if enabled_only:
                stmt = stmt.where(Team.enabled.is_(True))
            return [
                {"id": t.id, "name": t.name, "enabled": t.enabled, "sort_order": t.sort_order}
                for t in session.scalars(stmt)
            ]

    def save_team(self, name: str, team_id: int | None = None, enabled=True, sort_order=0):
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("请输入有效组别名称")
        with self.db.session() as session:
            row = session.get(Team, team_id) if team_id else Team()
            if row is None:
                raise ValueError("组别不存在")
            if team_id:
                setting = session.get(Setting, "default_team")
                default_team = json.loads(setting.value) if setting else DEFAULTS["default_team"]
                if default_team == row.name and not enabled:
                    raise ValueError("默认组别不能停用，请先在基础设置中选择其他默认组别")
                if row.name != name and default_team == row.name:
                    session.merge(
                        Setting(key="default_team", value=json.dumps(name, ensure_ascii=False))
                    )
            row.name, row.enabled, row.sort_order = name, enabled, sort_order
            session.add(row)
