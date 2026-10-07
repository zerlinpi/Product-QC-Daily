import logging
import random
from datetime import date, time, timedelta

from sqlalchemy import delete, func, select

from app.core.schemas import InspectionInput
from app.database.models import InspectionRecord

DEMO_RECORDS_PER_DAY = 5
DEMO_DAILY_VOLUME_VALUES = (1, 2, 3, 4, 5, 6, 7, 8, 9)
DEMO_DAILY_VOLUME_WEIGHTS = (1, 1, 5, 23, 9, 22, 1, 1, 3)
DEMO_SAMPLING_VALUES = (20, 30, 40, 50, 60, 80, 100, 120, 140, 160)
DEMO_SAMPLING_WEIGHTS = (14, 12, 117, 20, 51, 154, 30, 42, 3, 10)
DEMO_INSPECTION_VALUES = (200, 300, 360, 400, 480, 500, 600, 700, 800, 900, 1000, 1200)
DEMO_INSPECTION_WEIGHTS = (10, 91, 7, 21, 3, 28, 151, 8, 22, 23, 16, 15)
DEMO_TEAM_WEIGHTS = {
    "U1": 46,
    "U2": 58,
    "U3": 94,
    "U4": 59,
    "U5": 56,
    "U6": 54,
    "U7": 52,
    "U8": 40,
}


def demo_days(start: date, end: date) -> list[date]:
    """Return every calendar day in the selected range."""
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def suggested_demo_count(start: date, end: date) -> int:
    """Match the uploaded form's overall density: 460 rows across 92 calendar days."""
    if end < start:
        return 1
    return min(100_000, max(1, len(demo_days(start, end)) * DEMO_RECORDS_PER_DAY))


def daily_demo_counts(
    start: date, end: date, count: int, rng: random.Random
) -> list[tuple[date, int]]:
    """Distribute records over the range with sample-derived daily variation."""
    days = demo_days(start, end)
    if not days:
        return []
    if count <= len(days):
        selected = (
            [days[len(days) // 2]]
            if count == 1
            else [
                days[round(index * (len(days) - 1) / (count - 1))]
                for index in range(count)
            ]
        )
        selected_counts = {day: 1 for day in selected}
        return [(day, selected_counts.get(day, 0)) for day in days]

    sampled = rng.choices(
        DEMO_DAILY_VOLUME_VALUES,
        weights=DEMO_DAILY_VOLUME_WEIGHTS,
        k=len(days),
    )
    scale = count / sum(sampled)
    counts = [max(1, round(value * scale)) for value in sampled]

    delta = count - sum(counts)
    order = list(range(len(days)))
    rng.shuffle(order)
    while delta:
        changed = False
        for index in order:
            if delta > 0:
                counts[index] += 1
                delta -= 1
                changed = True
            elif counts[index] > 1:
                counts[index] -= 1
                delta += 1
                changed = True
            if delta == 0:
                break
        if not changed:
            break

    return list(zip(days, counts, strict=True))


def balanced_demo_dates(start: date, end: date, count: int, rng: random.Random) -> list[date]:
    """Spread records across the selected range while keeping realistic daily volume."""
    return [
        day
        for day, daily_count in daily_demo_counts(start, end, count, rng)
        for _ in range(daily_count)
    ]


class DemoService:
    def __init__(self, ctx):
        self.ctx = ctx

    def generate(
        self,
        count: int,
        start: date,
        end: date,
        teams: list[str],
        rework_rate=0.18,
        defect_rate=0.025,
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
        team_weights = [DEMO_TEAM_WEIGHTS.get(team, 50) for team in teams]
        with self.ctx.db.session() as session:
            for i, inspection_date in enumerate(scheduled_dates):
                sampling = rng.choices(
                    DEMO_SAMPLING_VALUES,
                    weights=DEMO_SAMPLING_WEIGHTS,
                )[0]
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
                    team=rng.choices(teams, weights=team_weights)[0],
                    work_order=f"DEMO-{inspection_date:%Y%m}-{i // 4 + 1:05}",
                    inspection_quantity=max(
                        sampling,
                        rng.choices(
                            DEMO_INSPECTION_VALUES,
                            weights=DEMO_INSPECTION_WEIGHTS,
                        )[0],
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
