from datetime import date

import pytest


def add(ctx, payload, day, count=2, code=24, source="manual", judgment="返工"):
    from app.core.schemas import InspectionInput

    return ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "inspection_date": day,
                    "defect_quantity": count,
                    "defects": [{"defect_id": code, "quantity": count}] if count else [],
                    "source": source,
                    "judgment": judgment,
                }
            )
        )
    )


def test_month_does_not_mix_years_and_demo_is_excluded(ctx, payload):
    from app.core.schemas import RecordFilter

    add(ctx, payload, "2025-01-05", 10)
    add(ctx, payload, "2026-01-05", 2)
    add(ctx, payload, "2026-01-06", 0, judgment="合格")
    add(ctx, payload, "2026-01-05", 12, source="demo")
    result = ctx.statistics.summary(RecordFilter(start="2026-01-01", end="2026-01-31"))
    assert result["batches"] == 2
    assert result["defect_quantity"] == 2
    assert result["sampling_quantity"] == 40
    assert result["defect_rate"] == pytest.approx(0.05)
    assert result["rework_rate"] == 0.5 and result["pass_rate"] == 0.5


def test_week_crosses_year_and_previous_period():
    from app.services.statistics_service import date_range, previous_range

    assert date_range("本周", date(2026, 1, 1)) == (date(2025, 12, 29), date(2026, 1, 4))
    assert date_range("上月", date(2026, 1, 8)) == (date(2025, 12, 1), date(2025, 12, 31))
    assert date_range("本季度", date(2026, 1, 8)) == (date(2026, 1, 1), date(2026, 3, 31))
    assert previous_range(date(2026, 1, 1), date(2026, 1, 7)) == (
        date(2025, 12, 25),
        date(2025, 12, 31),
    )


def test_pareto_all_24_and_unknown_counts_separate(ctx, payload):
    from app.core.schemas import InspectionInput, RecordFilter

    for code in range(1, 25):
        add(ctx, payload, "2026-01-05", 1, code=code)
    add(ctx, payload, "2026-01-06", 2, code=24)
    unknown = payload.model_dump() | {"defect_quantity": 2, "defects": [{"defect_id": 24}]}
    ctx.inspections.save(InspectionInput(**unknown))
    rows = ctx.statistics.pareto(RecordFilter(), "batches")
    assert len(rows) == 24 and rows[0]["code"] == "x" and rows[0]["value"] == 3
    assert rows[-1]["cumulative"] == pytest.approx(1)
    rows = ctx.statistics.pareto(RecordFilter(), "quantity")
    assert rows[0]["value"] == 3 and rows[0]["unknown_batches"] == 1


def test_empty_and_deleted_records_are_safe(ctx, payload):
    from app.core.schemas import RecordFilter

    row = add(ctx, payload, "2026-01-05")
    ctx.inspections.delete([row["id"]])
    summary = ctx.statistics.summary(RecordFilter())
    assert summary["defect_rate"] == 0 and summary["batches"] == 0
    trend = ctx.statistics.trend(RecordFilter(start="2026-01-01", end="2026-01-07"))
    assert len(trend) == 7 and sum(day["defect_quantity"] for day in trend) == 0
