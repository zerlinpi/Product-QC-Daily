import logging
import random
from datetime import date, time, timedelta

from sqlalchemy import delete, func, select

from app.core.schemas import InspectionInput
from app.database.models import InspectionRecord

DEMO_RECORDS_PER_WORKDAY = 7


def demo_workdays(start: date, end: date) -> list[date]:
    """Return production-like active days, preferring Monday-Friday."""
    days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    workdays = [day for day in days if day.weekday() < 5]
    return workdays or days


def suggested_demo_count(start: date, end: date) -> int:
    """Match the uploaded daily form's roughly seven records per workday density."""
    if end < start:
        return 1
    return min(100_000, max(1, len(demo_workdays(start, end)) * DEMO_RECORDS_PER_WORKDAY))


def balanced_demo_dates(start: date, end: date, count: int, rng: random.Random) -> list[date]:
    """Spread demo records across the full range instead of clustering randomly."""
    days = demo_workdays(start, end)
    if count <= len(days):
        if count == 1:
            return [days[len(days) // 2]]
        last = len(days) - 1
        return [days[round(index * last / (count - 1))] for index in range(count)]

    base, extra = divmod(count, len(days))
    result = [day for day in days for _ in range(base)]
    if extra:
        if extra == 1:
            result.append(days[len(days) // 2])
        else:
            last = len(days) - 1
            result.extend(days[round(index * last / (extra - 1))] for index in range(extra))
    rng.shuffle(result)
    return result


class DemoService:
    def __init__(self, ctx):
        self.ctx = ctx

    def generate(
        self,
        count: int,
        start: date,
        end: date,
        teams: list[str],
        rework_rate=0.08,
        defect_rate=0.02,
        weights: dict[int, float] | None = None,
        seed: int | None = None,
    ) -> int:
        if not 1 <= count <= 100_000 or end < start or not teams:
            raise ValueError("请选择有效日期、组别和 1–100000 条生成数量")
        if not 0 <= rework_rate <= 1 or not 0 <= defect_rate <= 1:
            raise ValueError("比率必须在 0%–100% 之间")
        valid_teams = {t["name"] for t in self.ctx.settings.teams(True)}
        if not set(teams) <= valid_teams:
            raise ValueError("组别不存在或已停用")
        defects = self.ctx.defects.list(enabled_only=True)
        ids = [d["id"] for d in defects if weights is None or weights.get(d["id"], 0) > 0]
        probabilities = [weights[i] if weights else (4 if i in (4, 5, 7) else 1) for i in ids]
        if not ids:
            raise ValueError("请至少启用一个不良项目，并设置正数权重")
        rng = random.Random(seed)
        scheduled_dates = balanced_demo_dates(start, end, count, rng)
        with self.ctx.db.session() as session:
            for i, inspection_date in enumerate(scheduled_dates):
                sampling = rng.choice([20, 40, 60, 80, 100, 120])
                batch_probability = min(1, max(0.2, defect_rate * 10)) if defect_rate else 0
                defective = rng.random() < batch_probability
                quantity = (
                    min(
                        sampling,
                        max(
                            1,
                            round(
                                rng.expovariate(
                                    1
                                    / max(1, sampling * defect_rate / max(batch_probability, 0.01))
                                )
                            ),
                        ),
                    )
                    if defective
                    else 0
                )
                data = InspectionInput(
                    inspection_date=inspection_date,
                    inspection_time=time(rng.randint(8, 20), rng.randrange(60)),
                    team=rng.choice(teams),
                    work_order=f"DEMO-{inspection_date:%Y%m}-{i // 4 + 1:05}",
                    inspection_quantity=max(
                        sampling,
                        rng.choice([300, 400, 480, 600, 700, 800, 900, 1000]),
                    ),
                    sampling_quantity=sampling,
                    defect_quantity=quantity,
                    judgment="返工" if rng.random() < rework_rate else "合格",
                    inspector="演示检验员",
                    source="demo",
                    remark="模拟数据，不用于正式质量结论",
                    defects=[
                        {
                            "defect_id": rng.choices(ids, weights=probabilities)[0],
                            "quantity": quantity,
                        }
                    ]
                    if quantity
                    else [],
                )
                self.ctx.inspections.save_in_session(
                    session,
                    data,
                    validate_references=False,
                    flush=False,
                )
        logging.getLogger("qc.demo").info("生成演示数据 %s", count)
        return count

    def clear(self) -> int:
        with self.ctx.db.session() as session:
            count = session.scalar(
                select(func.count())
                .select_from(InspectionRecord)
                .where(InspectionRecord.source == "demo")
            )
            session.execute(delete(InspectionRecord).where(InspectionRecord.source == "demo"))
        logging.getLogger("qc.demo").info("清理演示数据 %s", count)
        return count
