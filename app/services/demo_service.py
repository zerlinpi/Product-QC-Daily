import logging
import random
from datetime import date, time, timedelta

from sqlalchemy import delete, func, select

from app.core.schemas import InspectionInput
from app.database.models import InspectionRecord


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
        with self.ctx.db.session() as session:
            for i in range(count):
                sampling = rng.choice([20, 32, 50, 80])
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
                    inspection_date=start + timedelta(days=rng.randrange((end - start).days + 1)),
                    inspection_time=time(rng.randint(8, 20), rng.randrange(60)),
                    team=rng.choice(teams),
                    work_order=f"DEMO-{start:%Y%m}-{i // 4 + 1:05}",
                    inspection_quantity=sampling * rng.choice([5, 8, 10]),
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
                self.ctx.inspections.save_in_session(session, data)
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
