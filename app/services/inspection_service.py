import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, or_, select, update

from app.core.schemas import InspectionInput, RecordFilter
from app.database.models import DefectItem, InspectionDefect, Team
from app.database.models import InspectionRecord as R

log = logging.getLogger("qc.inspections")


def conditions(filters: RecordFilter) -> list:
    clauses = [R.deleted_at.is_not(None) if filters.deleted else R.deleted_at.is_(None)]
    if filters.source == "production":
        clauses.append(R.source != "demo")
    elif filters.source == "demo":
        clauses.append(R.source == "demo")
    for key, operator in (("start", R.inspection_date.__ge__), ("end", R.inspection_date.__le__)):
        if getattr(filters, key):
            clauses.append(operator(getattr(filters, key)))
    for key in ("team", "judgment"):
        if getattr(filters, key):
            clauses.append(getattr(R, key) == getattr(filters, key))
    for key in ("work_order", "inspector"):
        if getattr(filters, key):
            clauses.append(getattr(R, key).contains(getattr(filters, key), autoescape=True))
    if filters.search:
        clauses.append(
            or_(
                *(
                    getattr(R, key).contains(filters.search, autoescape=True)
                    for key in ("inspection_no", "work_order", "inspector", "remark")
                )
            )
        )
    if filters.has_defects is not None:
        clauses.append(R.defect_quantity > 0 if filters.has_defects else R.defect_quantity == 0)
    if filters.defect_id:
        clauses.append(
            R.id.in_(
                select(InspectionDefect.inspection_id).where(
                    InspectionDefect.defect_id == filters.defect_id
                )
            )
        )
    if filters.ids is not None:
        clauses.append(R.id.in_(filters.ids))
    return clauses


def record_dict(row: R) -> dict:
    values = {column.name: getattr(row, column.name) for column in R.__table__.columns}
    for key in ("inspection_date", "inspection_time", "created_at", "updated_at", "deleted_at"):
        if values[key] is not None:
            values[key] = values[key].isoformat()
    values["defects"] = [
        {
            "defect_id": d.defect_id,
            "code": d.item.code,
            "name": d.item.name,
            "quantity": d.quantity,
            "remark": d.remark,
        }
        for d in row.defects
    ]
    return values


def input_from_record(row: dict) -> InspectionInput:
    values = {key: row[key] for key in InspectionInput.model_fields if key in row}
    values["defects"] = [
        {key: d[key] for key in ("defect_id", "quantity", "remark")} for d in row["defects"]
    ]
    return InspectionInput(**values)


class InspectionService:
    def __init__(self, db, paths, signatures):
        self.db, self.paths, self.signatures = db, paths, signatures

    def save_in_session(
        self, session, data: InspectionInput, record_id=None, inspection_no=None, fingerprint=None
    ) -> R:
        record = session.get(R, record_id) if record_id else R()
        if record is None or (record_id and record.deleted_at):
            raise ValueError("记录已删除或不存在，请刷新")
        team = session.scalar(select(Team).where(Team.name == data.team))
        if not team or (not team.enabled and (not record_id or record.team != data.team)):
            raise ValueError("该组别不存在或已停用，请在设置中检查")
        existing = {d.defect_id for d in record.defects} if record_id else set()
        for d in data.defects:
            item = session.get(DefectItem, d.defect_id)
            if not item or (not item.enabled and d.defect_id not in existing):
                raise ValueError("不良项目不存在或已停用")
        for key, value in data.model_dump(exclude={"defects"}).items():
            setattr(record, key, value)
        if record_id:
            record.defects.clear()
            session.flush()
            record.import_fingerprint = None
        else:
            record.inspection_no = (
                inspection_no or f"QC-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:10]}"
            )
            record.import_fingerprint = fingerprint
        record.updated_at = datetime.now()
        record.defects = [InspectionDefect(**d.model_dump()) for d in data.defects]
        session.add(record)
        session.flush()
        return record

    def save(self, data: InspectionInput, record_id: int | None = None) -> dict:
        copied = None
        try:
            if data.signature_path:
                name, created = self.signatures.store(data.signature_path)
                copied = name if created else None
                data = data.model_copy(update={"signature_path": name})
            with self.db.session() as session:
                record = self.save_in_session(session, data, record_id)
                identifier = record.id
                result = record_dict(record)
        except Exception:
            if copied:
                (self.paths.signatures / copied).unlink(missing_ok=True)
            raise
        log.info("%s record=%s", "更新" if record_id else "保存", identifier)
        return result

    def get(self, record_id: int) -> dict:
        with self.db.session() as session:
            record = session.get(R, record_id)
            if not record:
                raise ValueError("记录不存在")
            return record_dict(record)

    def query(self, filters: RecordFilter | None = None) -> tuple[list[dict], int]:
        filters = filters or RecordFilter()
        allowed = {
            "inspection_date",
            "inspection_time",
            "team",
            "work_order",
            "inspector",
            "judgment",
            "inspection_quantity",
            "sampling_quantity",
            "defect_quantity",
            "created_at",
            "inspection_no",
            "source",
        }
        column = getattr(R, filters.sort if filters.sort in allowed else "inspection_date")
        columns = [column, R.inspection_time] if column is R.inspection_date else [column]
        order = [c.desc() if filters.descending else c.asc() for c in columns]
        with self.db.session() as session:
            total = session.scalar(select(func.count()).select_from(R).where(*conditions(filters)))
            rows = session.scalars(
                select(R)
                .where(*conditions(filters))
                .order_by(*order, R.id.desc())
                .offset((filters.page - 1) * filters.page_size)
                .limit(filters.page_size)
            )
            return [record_dict(row) for row in rows], total

    def iter_records(self, filters: RecordFilter):
        page = 1
        while True:
            rows, total = self.query(filters.model_copy(update={"page": page, "page_size": 500}))
            yield from rows
            if page * 500 >= total:
                break
            page += 1

    def delete(self, ids: list[int]) -> None:
        with self.db.session() as session:
            session.execute(
                update(R)
                .where(R.id.in_(ids), R.deleted_at.is_(None))
                .values(deleted_at=datetime.now(), updated_at=datetime.now())
            )
        log.info("软删除 %s", ids)

    def restore(self, ids: list[int]) -> None:
        with self.db.session() as session:
            session.execute(
                update(R).where(R.id.in_(ids)).values(deleted_at=None, updated_at=datetime.now())
            )
        log.info("恢复记录 %s", ids)

    def bulk_update(
        self, ids: list[int], team: str | None = None, inspector: str | None = None
    ) -> None:
        values = {"updated_at": datetime.now(), "import_fingerprint": None}
        with self.db.session() as session:
            if team:
                if not session.scalar(
                    select(Team).where(Team.name == team, Team.enabled.is_(True))
                ):
                    raise ValueError("组别不存在或已停用")
                values["team"] = team
            if inspector is not None:
                if not inspector.strip() or len(inspector.strip()) > 100:
                    raise ValueError("请输入有效检验员名称")
                values["inspector"] = inspector.strip()
            session.execute(update(R).where(R.id.in_(ids), R.deleted_at.is_(None)).values(**values))
        log.info("批量修改 %s", ids)

    def recent_values(self, field="work_order", limit=100) -> list[str]:
        if field not in ("work_order", "inspector"):
            raise ValueError("字段无效")
        column = getattr(R, field)
        with self.db.session() as session:
            return list(
                session.scalars(
                    select(column)
                    .where(R.deleted_at.is_(None), R.source != "demo")
                    .group_by(column)
                    .order_by(func.max(R.id).desc())
                    .limit(limit)
                )
            )

    def sampling_suggestion(self, work_order: str) -> int | None:
        with self.db.session() as session:
            return session.scalar(
                select(R.sampling_quantity)
                .where(R.work_order == work_order, R.source != "demo", R.deleted_at.is_(None))
                .order_by(R.id.desc())
                .limit(1)
            )
