from sqlalchemy import func, select

from app.database.models import DefectItem, InspectionDefect


class DefectService:
    def __init__(self, db):
        self.db = db

    def list(self, search="", enabled_only=False) -> list[dict]:
        with self.db.session() as session:
            stmt = select(DefectItem).order_by(DefectItem.sort_order, DefectItem.id)
            if enabled_only:
                stmt = stmt.where(DefectItem.enabled.is_(True))
            if search:
                stmt = stmt.where(
                    DefectItem.name.contains(search, autoescape=True)
                    | DefectItem.code.contains(search, autoescape=True)
                )
            return [
                {c.name: getattr(row, c.name) for c in DefectItem.__table__.columns}
                for row in session.scalars(stmt)
            ]

    def save(self, values: dict, defect_id: int | None = None) -> None:
        code, name = (
            str(values.get("code", "")).strip().lower(),
            str(values.get("name", "")).strip(),
        )
        if not code or not name or len(code) > 30 or len(name) > 150:
            raise ValueError("请输入有效编码和项目名称")
        with self.db.session() as session:
            row = session.get(DefectItem, defect_id) if defect_id else DefectItem()
            if row is None:
                raise ValueError("不良项目不存在")
            if (
                defect_id
                and row.code != code
                and session.scalar(
                    select(func.count())
                    .select_from(InspectionDefect)
                    .where(InspectionDefect.defect_id == defect_id)
                )
            ):
                raise ValueError("已有历史记录的编码不能修改；可以更改名称或停用")
            row.code, row.name = code, name
            for key in ("category", "description", "enabled", "sort_order"):
                if key in values:
                    setattr(row, key, values[key])
            session.add(row)

    def disable(self, defect_id: int) -> None:
        with self.db.session() as session:
            row = session.get(DefectItem, defect_id)
            if row:
                row.enabled = False
