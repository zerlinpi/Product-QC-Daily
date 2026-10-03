import calendar
from datetime import date, timedelta

from sqlalchemy import case, func, select

from app.core.schemas import RecordFilter
from app.database.models import DefectItem, InspectionDefect
from app.database.models import InspectionRecord as R
from app.services.inspection_service import conditions

PRESETS = ["今天", "昨天", "本周", "上周", "本月", "上月", "本季度", "本年", "自定义"]


def date_range(preset: str, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if preset in ("今天", "昨天"):
        day = today - timedelta(days=preset == "昨天")
        return day, day
    if preset in ("本周", "上周"):
        start = today - timedelta(days=today.weekday() + (7 if preset == "上周" else 0))
        return start, start + timedelta(days=6)
    if preset == "上月":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if preset == "本年":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    if preset == "本季度":
        month = (today.month - 1) // 3 * 3 + 1
        return date(today.year, month, 1), date(
            today.year, month + 2, calendar.monthrange(today.year, month + 2)[1]
        )
    return today.replace(day=1), today.replace(day=calendar.monthrange(today.year, today.month)[1])


def previous_range(start: date, end: date) -> tuple[date, date]:
    return start - timedelta(days=(end - start).days + 1), start - timedelta(days=1)


def aggregates():
    return [
        func.count(R.id).label("batches"),
        func.coalesce(func.sum(R.inspection_quantity), 0).label("inspection_quantity"),
        func.coalesce(func.sum(R.sampling_quantity), 0).label("sampling_quantity"),
        func.coalesce(func.sum(R.defect_quantity), 0).label("defect_quantity"),
        func.coalesce(func.sum(case((R.judgment == "合格", 1), else_=0)), 0).label("pass_batches"),
        func.coalesce(func.sum(case((R.judgment == "返工", 1), else_=0)), 0).label(
            "rework_batches"
        ),
    ]


def rates(values: dict) -> dict:
    values["defect_rate"] = (
        values["defect_quantity"] / values["sampling_quantity"]
        if values["sampling_quantity"]
        else 0
    )
    values["pass_rate"] = values["pass_batches"] / values["batches"] if values["batches"] else 0
    values["rework_rate"] = values["rework_batches"] / values["batches"] if values["batches"] else 0
    return values


class StatisticsService:
    def __init__(self, db):
        self.db = db

    def summary(self, filters: RecordFilter | None = None) -> dict:
        with self.db.session() as session:
            row = (
                session.execute(select(*aggregates()).where(*conditions(filters or RecordFilter())))
                .mappings()
                .one()
            )
            return rates(dict(row))

    def comparison(self, filters: RecordFilter) -> dict:
        if not filters.start or not filters.end:
            raise ValueError("请选择完整日期范围")
        start, end = previous_range(filters.start, filters.end)
        previous = self.summary(filters.model_copy(update={"start": start, "end": end}))
        current = self.summary(filters)
        return {
            "current": current,
            "previous": previous,
            "delta": {key: current[key] - previous[key] for key in current},
        }

    def trend(self, filters: RecordFilter) -> list[dict]:
        if not filters.start or not filters.end:
            raise ValueError("趋势图需要完整日期范围")
        if (filters.end - filters.start).days > 3660:
            raise ValueError("趋势图请选择 10 年以内的范围")
        with self.db.session() as session:
            rows = session.execute(
                select(R.inspection_date.label("date"), *aggregates())
                .where(*conditions(filters))
                .group_by(R.inspection_date)
            ).mappings()
            lookup = {row["date"]: rates(dict(row)) for row in rows}
        result, day = [], filters.start
        while day <= filters.end:
            result.append(
                lookup.get(
                    day,
                    rates(
                        {
                            "date": day,
                            "batches": 0,
                            "inspection_quantity": 0,
                            "sampling_quantity": 0,
                            "defect_quantity": 0,
                            "pass_batches": 0,
                            "rework_batches": 0,
                        }
                    ),
                )
            )
            day += timedelta(days=1)
        return result

    def teams(self, filters: RecordFilter) -> list[dict]:
        with self.db.session() as session:
            rows = session.execute(
                select(R.team, *aggregates())
                .where(*conditions(filters))
                .group_by(R.team)
                .order_by(R.team)
            ).mappings()
            return [rates(dict(row)) for row in rows]

    def pareto(self, filters: RecordFilter, metric="batches") -> list[dict]:
        if metric not in ("batches", "quantity"):
            raise ValueError("统计口径无效")
        with self.db.session() as session:
            stmt = (
                select(
                    DefectItem.code,
                    DefectItem.name,
                    func.count(InspectionDefect.id).label("batches"),
                    func.coalesce(func.sum(InspectionDefect.quantity), 0).label("quantity"),
                    func.sum(case((InspectionDefect.quantity.is_(None), 1), else_=0)).label(
                        "unknown_batches"
                    ),
                )
                .select_from(InspectionDefect)
                .join(R)
                .join(DefectItem)
                .where(*conditions(filters))
                .group_by(DefectItem.id)
            )
            rows = [dict(row) for row in session.execute(stmt).mappings()]
        rows.sort(key=lambda row: (-row[metric], row["code"]))
        total = sum(row[metric] for row in rows)
        cumulative = 0
        for row in rows:
            row["value"] = row[metric]
            row["top80"] = cumulative < total * 0.8 and row[metric] > 0
            cumulative += row[metric]
            row["cumulative"] = cumulative / total if total else 0
        return rows
