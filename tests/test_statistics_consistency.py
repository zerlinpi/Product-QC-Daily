from datetime import date

import pytest

from app.core.schemas import InspectionInput, RecordFilter


def test_weighted_statistics_refresh_after_edit_delete_restore(ctx, payload):
    first = ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "inspection_date": "2026-01-01",
                    "sampling_quantity": 10,
                    "defect_quantity": 5,
                    "defects": [{"defect_id": 1}],
                    "judgment": "返工",
                    "source": "excel",
                }
            )
        )
    )
    second = ctx.inspections.save(
        InspectionInput(
            **(
                payload.model_dump()
                | {
                    "inspection_date": "2026-12-31",
                    "sampling_quantity": 100,
                    "defect_quantity": 1,
                    "defects": [{"defect_id": 1, "quantity": 1}],
                    "judgment": "合格",
                }
            )
        )
    )
    ctx.inspections.save(payload.model_copy(update={"source": "demo"}))
    filters = RecordFilter(start="2026-01-01", end="2026-12-31")
    for _ in range(3):
        summary = ctx.statistics.summary(filters)
        assert summary["batches"] == 2
        assert summary["defect_rate"] == pytest.approx(6 / 110)
        assert summary["rework_rate"] == 0.5
        assert ctx.statistics.teams(filters)[0]["defect_rate"] == pytest.approx(6 / 110)
        trend = ctx.statistics.trend(filters)
        assert len(trend) == 365
        assert sum(r["defect_quantity"] for r in trend) == 6
        pareto = ctx.statistics.pareto(filters, "quantity")[0]
        assert (pareto["batches"], pareto["quantity"], pareto["unknown_batches"]) == (2, 1, 1)
        assert ctx.inspections.get(first["id"])["defects"][0]["quantity"] is None
    ctx.inspections.delete([first["id"]])
    assert ctx.statistics.summary(filters)["defect_rate"] == 0.01
    assert ctx.statistics.pareto(filters)[0]["batches"] == 1
    ctx.inspections.restore([first["id"]])
    assert ctx.statistics.summary(filters)["defect_rate"] == pytest.approx(6 / 110)
    ctx.inspections.save(
        payload.model_copy(update={"inspection_date": date(2026, 12, 31)}), second["id"]
    )
    assert ctx.statistics.summary(filters)["defect_rate"] == pytest.approx(5 / 30)
    assert ctx.statistics.pareto(filters)[0]["unknown_batches"] == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"team": "U2"},
        {"judgment": "返工"},
        {"inspector": "乙"},
        {"work_order": "_50%"},
        {"has_defects": True},
        {"has_defects": False},
        {"defect_id": 1},
        {"search": "特殊"},
        {"source": "demo"},
        {"deleted": True},
        {"ids": []},
    ],
)
def test_every_filter_is_shared_by_detail_summary_trend_team_and_pareto(ctx, payload, extra):
    from sqlalchemy import text

    records = []
    for i in range(8):
        records.append(
            ctx.inspections.save(
                InspectionInput(
                    **(
                        payload.model_dump()
                        | {
                            "team": "U2" if i % 2 else "U1",
                            "judgment": "返工" if i % 2 else "合格",
                            "source": "demo" if i == 7 else "excel" if i == 6 else "manual",
                            "inspector": "乙" if i % 2 else "甲",
                            "work_order": "特殊_50%" if i % 2 else "普通X500",
                            "defect_quantity": i % 2,
                            "defects": [{"defect_id": 1, "quantity": 1}] if i % 2 else [],
                        }
                    )
                )
            )
        )
    ctx.inspections.delete([records[0]["id"]])
    with ctx.db.session() as session:
        raw = [
            dict(r) for r in session.execute(text("SELECT * FROM inspection_records")).mappings()
        ]
    filters = RecordFilter(start=payload.inspection_date, end=payload.inspection_date, **extra)
    chosen = []
    for r in raw:
        if bool(r["deleted_at"]) != filters.deleted:
            continue
        if (r["source"] == "demo") != (filters.source == "demo"):
            continue
        if filters.ids == []:
            continue
        if any(getattr(filters, k) and r[k] != getattr(filters, k) for k in ("team", "judgment")):
            continue
        if any(
            getattr(filters, k) and getattr(filters, k) not in r[k]
            for k in ("work_order", "inspector")
        ):
            continue
        if filters.search and not any(
            filters.search in r[k] for k in ("inspection_no", "work_order", "inspector", "remark")
        ):
            continue
        if filters.has_defects is not None and bool(r["defect_quantity"]) != filters.has_defects:
            continue
        if filters.defect_id and not r["defect_quantity"]:
            continue
        chosen.append(r)
    assert {r["id"] for r in ctx.inspections.iter_records(filters)} == {r["id"] for r in chosen}
    for result in [ctx.statistics.summary(filters), ctx.statistics.trend(filters)[0]]:
        assert result["batches"] == len(chosen)
        assert result["inspection_quantity"] == sum(r["inspection_quantity"] for r in chosen)
        assert result["defect_quantity"] == sum(r["defect_quantity"] for r in chosen)
    assert sum(r["batches"] for r in ctx.statistics.teams(filters)) == len(chosen)
    assert sum(r["batches"] for r in ctx.statistics.pareto(filters)) == sum(
        r["defect_quantity"] > 0 for r in chosen
    )
