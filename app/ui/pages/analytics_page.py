from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QGridLayout, QScrollArea, QWidget

from app.core.schemas import RecordFilter
from app.services.statistics_service import PRESETS, date_range
from app.ui.common import Page, button, card, guarded, label, populate, table
from app.ui.widgets.chart_widget import ChartWidget
from app.ui.widgets.pareto_widget import ParetoWidget
from app.ui.widgets.stat_card import stat_card


class AnalyticsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx,
            window,
            "质量分析",
            "选择日期后点击“开始分析”，查看不良趋势、重点项目和与上一周期的变化",
        )
        filter_card, filter_box = card()
        filter_box.addWidget(label("分析范围", "section"))
        filters = QGridLayout()
        filters.setHorizontalSpacing(12)
        filters.setVerticalSpacing(6)
        self.preset, self.source, self.metric_choice = QComboBox(), QComboBox(), QComboBox()
        self.preset.addItems(PRESETS)
        self.preset.setCurrentText("本月")
        self.source.addItems(["正式数据", "演示数据"])
        self.metric_choice.addItems(["按出现批次", "按已填件数"])
        self.metric_choice.setToolTip(
            "出现批次：该项目出现过的检验次数。已填件数：只累计实际填写的件数。"
        )
        self.start, self.end = QDateEdit(), QDateEdit()
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        controls = [
            ("统计周期", self.preset),
            ("开始日期", self.start),
            ("结束日期", self.end),
            ("数据范围", self.source),
            ("排行口径", self.metric_choice),
        ]
        for col, (title, widget) in enumerate(controls):
            filters.addWidget(label(title, "fieldLabel"), 0, col)
            filters.addWidget(widget, 1, col)
        filters.addWidget(button("开始分析", self.refresh, primary=True), 1, len(controls))
        filter_box.addLayout(filters)
        self.scope = label("", "muted")
        filter_box.addWidget(self.scope)
        self.layout.addWidget(filter_card)
        self.preset.currentTextChanged.connect(self.set_range)
        self.source.currentIndexChanged.connect(self.mark_stale)
        self.metric_choice.currentIndexChanged.connect(self.mark_stale)
        self.start.dateChanged.connect(self.mark_stale)
        self.end.dateChanged.connect(self.mark_stale)
        self.set_range("本月")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        self.metrics = []
        definitions = [
            ("检验数量", "inspection_quantity"),
            ("抽检数量", "sampling_quantity"),
            ("不良件数", "defect_quantity"),
            ("不良率", "defect_rate"),
            ("返工率", "rework_rate"),
        ]
        for i, (title, key) in enumerate(definitions):
            widget = stat_card(title)
            grid.addWidget(widget, 0, i * 2, 1, 2)
            self.metrics.append((widget, key))
        frame, layout = card()
        self.pareto = ParetoWidget()
        layout.addWidget(self.pareto)
        self.top80 = label("暂无数据", "muted", True)
        layout.addWidget(self.top80)
        grid.addWidget(frame, 1, 0, 1, 10)
        frame, layout = card()
        self.trend = ChartWidget("不良率趋势")
        layout.addWidget(self.trend)
        grid.addWidget(frame, 2, 0, 1, 5)
        frame, layout = card()
        self.team_chart = ChartWidget("组别不良率")
        layout.addWidget(self.team_chart)
        grid.addWidget(frame, 2, 5, 1, 5)
        self.ranking = table(
            ["编码", "不良项目", "出现批次", "已填件数", "未填件数批次", "累计占比"]
        )
        self.ranking.setMinimumHeight(300)
        self.ranking.setColumnWidth(1, 240)
        grid.addWidget(self.ranking, 3, 0, 1, 10)
        self.teams_table = table(
            ["组别", "检验数", "抽检数", "不良数", "不良率", "合格批次", "返工批次", "返工率"]
        )
        self.teams_table.setMinimumHeight(260)
        grid.addWidget(self.teams_table, 4, 0, 1, 10)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)

    def sync_preset_range(self):
        preset = self.preset.currentText()
        if preset == "自定义":
            return
        start, end = date_range(preset)
        for widget, value in ((self.start, start), (self.end, end)):
            previous = widget.blockSignals(True)
            widget.setDate(QDate(value))
            widget.blockSignals(previous)

    def set_range(self, preset):
        custom = preset == "自定义"
        self.start.setEnabled(custom)
        self.end.setEnabled(custom)
        if not custom:
            self.sync_preset_range()
        self.mark_stale()

    def show_demo_range(self, start, end):
        previous = self.preset.blockSignals(True)
        self.preset.setCurrentText("自定义")
        self.preset.blockSignals(previous)
        self.start.setEnabled(True)
        self.end.setEnabled(True)
        for widget, value in ((self.start, start), (self.end, end)):
            blocked = widget.blockSignals(True)
            widget.setDate(QDate(value))
            widget.blockSignals(blocked)
        blocked = self.source.blockSignals(True)
        self.source.setCurrentIndex(1)
        self.source.blockSignals(blocked)
        self.refresh()

    def mark_stale(self, *_):
        self.scope.setText("筛选条件已更改 · 点击“开始分析”更新结果")

    @guarded
    def refresh(self, *_):
        self.sync_preset_range()
        filters = RecordFilter(
            start=self.start.date().toPython(),
            end=self.end.date().toPython(),
            source="demo" if self.source.currentIndex() else "production",
        )
        self.scope.setText(
            f"当前范围：{filters.start} 至 {filters.end} · {self.source.currentText()} · {self.metric_choice.currentText()}"
        )
        comparison = self.ctx.statistics.comparison(filters)
        for widget, key in self.metrics:
            value, delta = comparison["current"][key], comparison["delta"][key]
            widget.value_label.setText(f"{value:.2%}" if key.endswith("rate") else f"{value:,}")
            widget.delta.setText(
                (f"{delta * 100:+.2f} 个百分点" if key.endswith("rate") else f"{delta:+,}")
                + " · 较上一周期"
            )
        pareto = self.ctx.statistics.pareto(
            filters, "quantity" if self.metric_choice.currentIndex() else "batches"
        )
        self.pareto.show_rows(pareto)
        important = [r["name"] for r in pareto if r["top80"]]
        self.top80.setText(
            "累计达到 80% 的项目：" + "、".join(important) if important else "暂无数据"
        )
        if self.metric_choice.currentIndex():
            self.top80.setText(
                self.top80.text()
                + "\n仅累计已知件数；未知件数不会按零件数推断，请同时查看未知批次。"
            )
        populate(
            self.ranking,
            [
                [
                    r["code"],
                    r["name"],
                    r["batches"],
                    r["quantity"],
                    r["unknown_batches"],
                    f"{r['cumulative']:.1%}",
                ]
                for r in pareto
            ],
        )
        trend = self.ctx.statistics.trend(filters)
        self.trend.draw(
            [r["date"].strftime("%m/%d") for r in trend],
            [r["defect_rate"] * 100 for r in trend],
            percent=True,
        )
        teams = self.ctx.statistics.teams(filters)
        self.team_chart.draw(
            [r["team"] for r in teams],
            [r["defect_rate"] * 100 for r in teams],
            bars=True,
            percent=True,
        )
        populate(
            self.teams_table,
            [
                [
                    r["team"],
                    r["inspection_quantity"],
                    r["sampling_quantity"],
                    r["defect_quantity"],
                    f"{r['defect_rate']:.2%}",
                    r["pass_batches"],
                    r["rework_batches"],
                    f"{r['rework_rate']:.2%}",
                ]
                for r in teams
            ],
        )
