from datetime import date, datetime, timedelta

from PySide6.QtWidgets import QComboBox, QWidget

from app.core.schemas import RecordFilter
from app.services.statistics_service import date_range
from app.ui.common import (
    WIDE_LAYOUT_BREAKPOINT,
    COMPACT_FIELD_MIN_WIDTH,
    Page,
    button,
    card,
    content_grid,
    control_metrics,
    field_label,
    grid_place,
    guarded,
    label,
    page_scroll,
    toolbar_layout,
)
from app.ui.widgets.chart_widget import ChartWidget
from app.ui.widgets.stat_card import stat_card


class DashboardPage(Page):
    def __init__(self, ctx, window):
        super().__init__(ctx, window, "质量总览", "查看今日与本月检验情况，及时发现质量变化")
        toolbar = toolbar_layout()
        self.today_label = label(date.today().strftime("%Y 年 %m 月 %d 日"), "muted")
        toolbar.addWidget(self.today_label)
        toolbar.addStretch()
        self.source = QComboBox()
        self.source.addItems(["正式数据", "演示数据"])
        toolbar.addWidget(field_label("数据范围", self.source))
        control_metrics(self.source, min_width=COMPACT_FIELD_MIN_WIDTH)
        self.source.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.source)
        self.refreshed = label("", "summary")
        toolbar.addWidget(self.refreshed)
        toolbar.addWidget(button("刷新", self.refresh))
        toolbar.addWidget(button("新建检验", self.window.new_inspection, primary=True))
        self.layout.addLayout(toolbar)
        scroll = page_scroll()
        content = QWidget()
        self.grid = content_grid(content)
        self.cards = []
        self._layout_mode = None
        definitions = [
            ("今日检验批次", "batches", False),
            ("今日检验数量", "inspection_quantity", False),
            ("今日抽检数量", "sampling_quantity", False),
            ("今日不良件数", "defect_quantity", False),
            ("今日不良率", "defect_rate", False),
            ("今日返工批次", "rework_batches", False),
            ("今日合格率", "pass_rate", False),
            ("本月检验批次", "batches", True),
            ("本月不良率", "defect_rate", True),
            ("本月返工率", "rework_rate", True),
        ]
        for i, (title, key, monthly) in enumerate(definitions):
            widget = stat_card(title)
            self.grid.addWidget(widget, i // 5, i % 5 * 2, 1, 2)
            self.cards.append((widget, key, monthly))
        self.charts = []
        self.chart_frames = []
        for i, title in enumerate(
            [
                "近 7 天 · 不良率",
                "近 30 天 · 不良率",
                "组别质量对比 · 本月不良率",
                "前十项不良 · 本月出现批次",
                "合格 / 返工 · 本月批次",
                "每日检验量 · 近 30 天",
            ]
        ):
            frame, layout = card()
            chart = ChartWidget(title)
            layout.addWidget(chart)
            self.grid.addWidget(frame, 2 + i // 2, i % 2 * 5, 1, 5)
            self.charts.append(chart)
            self.chart_frames.append(frame)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)
        self._reflow_content()

    def _reflow_content(self):
        mode = "wide" if self.width() >= WIDE_LAYOUT_BREAKPOINT else "narrow"
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        if mode == "wide":
            for i, (widget, *_rest) in enumerate(self.cards):
                grid_place(self.grid, widget, i // 5, (i % 5) * 2, 1, 2)
            chart_start = 2
            for i, frame in enumerate(self.chart_frames):
                grid_place(self.grid, frame, chart_start + i // 2, (i % 2) * 5, 1, 5)
        else:
            for i, (widget, *_rest) in enumerate(self.cards):
                grid_place(self.grid, widget, i // 2, (i % 2) * 5, 1, 5)
            chart_start = 5
            for i, frame in enumerate(self.chart_frames):
                grid_place(self.grid, frame, chart_start + i, 0, 1, 10)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "grid"):
            self._reflow_content()

    @guarded
    def refresh(self, *_):
        if not hasattr(self, "cards"):
            return
        today = date.today()
        self.today_label.setText(today.strftime("%Y 年 %m 月 %d 日"))
        source = "production" if self.source.currentIndex() == 0 else "demo"
        daily_filter = RecordFilter(start=today, end=today, source=source)
        month_start, month_end = date_range("本月", today)
        monthly_filter = RecordFilter(start=month_start, end=month_end, source=source)
        comparisons = [
            self.ctx.statistics.comparison(daily_filter),
            self.ctx.statistics.comparison(monthly_filter),
        ]
        for widget, key, monthly in self.cards:
            values = comparisons[int(monthly)]
            value, delta = values["current"][key], values["delta"][key]
            widget.value_label.setText(f"{value:.2%}" if key.endswith("rate") else f"{value:,}")
            difference = f"{delta * 100:+.2f} 个百分点" if key.endswith("rate") else f"{delta:+,}"
            widget.delta.setText(difference + (" · 较上一周期" if monthly else " · 较昨日"))
        for days, chart in zip((7, 30), self.charts[:2]):
            trend = self.ctx.statistics.trend(
                RecordFilter(start=today - timedelta(days=days - 1), end=today, source=source)
            )
            chart.draw(
                [r["date"].strftime("%m/%d") for r in trend],
                [r["defect_rate"] * 100 for r in trend],
                percent=True,
            )
        teams = self.ctx.statistics.teams(monthly_filter)
        self.charts[2].draw(
            [r["team"] for r in teams],
            [r["defect_rate"] * 100 for r in teams],
            bars=True,
            percent=True,
        )
        pareto = self.ctx.statistics.pareto(monthly_filter)[:10]
        self.charts[3].draw([r["code"] for r in pareto], [r["value"] for r in pareto], bars=True)
        self.charts[3].empty.setText(
            " · ".join(f"{r['code']} {r['name']}" for r in pareto[:3]) if pareto else "暂无数据"
        )
        self.charts[3].empty.setVisible(True)
        current = comparisons[1]["current"]
        self.charts[4].draw(
            ["合格", "返工"], [current["pass_batches"], current["rework_batches"]], bars=True
        )
        trend = self.ctx.statistics.trend(
            RecordFilter(start=today - timedelta(days=29), end=today, source=source)
        )
        self.charts[5].draw(
            [r["date"].strftime("%m/%d") for r in trend], [r["inspection_quantity"] for r in trend]
        )
        self.refreshed.setText(f"更新于 {datetime.now():%H:%M:%S}")
