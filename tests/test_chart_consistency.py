from datetime import date, timedelta

import pytest
from PySide6.QtCore import QDate

from app.core.schemas import InspectionInput, RecordFilter
from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_theme


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("size", [(1080, 720), (1440, 920), (1920, 1080)])
def test_native_charts_refresh_sources_empty_state_and_resize(ctx, payload, qtbot, theme, size):
    today = date.today()
    for source, count in [("manual", 2), ("demo", 5)]:
        for i in range(count):
            ctx.inspections.save(
                InspectionInput(
                    **(
                        payload.model_dump()
                        | {
                            "inspection_date": today,
                            "source": source,
                            "defect_quantity": 2,
                            "judgment": "返工",
                            "defects": [{"defect_id": 1, "quantity": 1}],
                        }
                    )
                )
            )
    ctx.settings.update({"theme": theme})
    window = MainWindow(ctx)
    qtbot.addWidget(window)
    window.resize(*size)
    window.show()
    dashboard, analytics = window.pages[0], window.pages[3]
    try:
        for source, index in [("production", 0), ("demo", 1), ("production", 0)]:
            dashboard.source.setCurrentIndex(index)
            dashboard.refresh()
            for days, chart in zip((7, 30), dashboard.charts[:2], strict=True):
                trend = ctx.statistics.trend(
                    RecordFilter(start=today - timedelta(days=days - 1), end=today, source=source)
                )
                assert chart._last_draw[1] == [r["defect_rate"] * 100 for r in trend]
                assert list(chart.plot.listDataItems()[0].getData()[1]) == chart._last_draw[1]
            month = RecordFilter(start=today.replace(day=1), end=today, source=source)
            expected = ctx.statistics.summary(month)
            assert dashboard.charts[4]._last_draw[1] == [
                expected["pass_batches"],
                expected["rework_batches"],
            ]
            assert sum(dashboard.charts[5]._last_draw[1]) == expected["inspection_quantity"]
            analytics.preset.setCurrentText("自定义")
            analytics.start.setDate(QDate(today))
            analytics.end.setDate(QDate(today))
            analytics.source.setCurrentIndex(index)
            analytics.refresh()
            assert analytics.trend._last_draw[1] == [expected["defect_rate"] * 100]
            assert analytics.team_chart._last_draw[1] == [expected["defect_rate"] * 100]
            assert analytics.pareto._pareto_rows == ctx.statistics.pareto(
                RecordFilter(start=today, end=today, source=source)
            )
        analytics.start.setDate(QDate(today - timedelta(days=60)))
        analytics.end.setDate(QDate(today - timedelta(days=59)))
        analytics.refresh()
        assert analytics.pareto._pareto_rows == []
        assert analytics.pareto.empty.isVisible() or analytics.pareto.empty.isHidden() is False
        assert analytics.trend._last_draw[1] == [0, 0]
        for page in (dashboard, analytics):
            window.stack.setCurrentWidget(page)
            qtbot.wait(30)
            for chart in (
                dashboard.charts
                if page is dashboard
                else [analytics.pareto, analytics.trend, analytics.team_chart]
            ):
                assert chart.plot.width() > 100 and chart.plot.height() >= 200
                assert chart.rect().contains(chart.plot.geometry())
                chart.refresh_theme()
        assert len(window.pages) == 7
    finally:
        window.close()
        apply_theme("light")
