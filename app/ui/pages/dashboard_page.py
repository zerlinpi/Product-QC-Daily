from datetime import date, timedelta

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QScrollArea, QWidget

from app.core.schemas import RecordFilter
from app.services.statistics_service import date_range
from app.ui.common import Page, button, card, guarded, label
from app.ui.widgets.chart_widget import ChartWidget
from app.ui.widgets.stat_card import stat_card


class DashboardPage(Page):
    def __init__(self, ctx, window):
        super().__init__(ctx, window, "质量工作台", "从每天的检验中，及时发现质量变化")
        toolbar = QHBoxLayout()
        toolbar.addWidget(label(date.today().strftime("%Y 年 %m 月 %d 日"), "muted"))
        toolbar.addStretch()
        self.source = QComboBox()
        self.source.addItems(["正式数据", "演示数据"])
        self.source.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.source)
        toolbar.addWidget(button("刷新", self.refresh))
        toolbar.addWidget(button("+ 新建检验", lambda: self.window.navigate(1), primary=True))
        self.layout.addLayout(toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        self.cards = []
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
            grid.addWidget(widget, i // 5, i % 5 * 2, 1, 2)
            self.cards.append((widget, key, monthly))
        self.charts = []
        for i, title in enumerate(
            [
                "近 7 天 · 不良率",
                "近 30 天 · 不良率",
                "组别质量对比 · 本月不良率",
                "Top 10 不良项目 · 本月出现批次",
                "合格 / 返工 · 本月批次",
                "每日检验量 · 近 30 天",
            ]
        ):
            frame, layout = card()
            chart = ChartWidget(title)
            layout.addWidget(chart)
            grid.addWidget(frame, 2 + i // 2, i % 2 * 5, 1, 5)
            self.charts.append(chart)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)

    @guarded
    def refresh(self, *_):
        if not hasattr(self, "cards"):
            return
        today = date.today()
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
