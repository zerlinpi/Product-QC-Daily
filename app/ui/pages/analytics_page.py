from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QWidget

from app.core.schemas import RecordFilter
from app.services.statistics_service import PRESETS, date_range
from app.ui.common import (
    WIDE_LAYOUT_BREAKPOINT,
    Page,
    align_table_columns,
    button,
    card,
    content_grid,
    control_metrics,
    field_label,
    form_grid,
    grid_place,
    guarded,
    label,
    native_group,
    page_scroll,
    populate,
    set_label_kind,
    table,
    table_minimum_rows,
)
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
        filter_card, filter_box = native_group("分析范围")
        self.filters_grid = form_grid()
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
        control_metrics(*[widget for _, widget in controls])
        self.filter_controls = []
        for col, (title, widget) in enumerate(controls):
            caption = field_label(title, widget)
            self.filter_controls.append((caption, widget))
            self.filters_grid.addWidget(caption, 0, col)
            self.filters_grid.addWidget(widget, 1, col)
        self.analyze_button = button("开始分析", self.refresh, primary=True)
        self.filters_grid.addWidget(self.analyze_button, 1, len(controls))
        filter_box.addLayout(self.filters_grid)
        self.scope = label("", "status")
        filter_box.addWidget(self.scope)
        self.layout.addWidget(filter_card)
        self.preset.currentTextChanged.connect(self.set_range)
        self.source.currentIndexChanged.connect(self.mark_stale)
        self.metric_choice.currentIndexChanged.connect(self.mark_stale)
        self.start.dateChanged.connect(self.mark_stale)
        self.end.dateChanged.connect(self.mark_stale)
        self.set_range("本月")
        scroll = page_scroll()
        content = QWidget()
        self.grid = content_grid(content)
        self.metrics = []
        self._layout_mode = None
        definitions = [
            ("检验数量", "inspection_quantity", ""),
            ("抽检数量", "sampling_quantity", ""),
            ("不良件数", "defect_quantity", "warning"),
            ("不良率", "defect_rate", "warning"),
            ("返工率", "rework_rate", "warning"),
        ]
        for i, (title, key, tone) in enumerate(definitions):
            widget = stat_card(title, tone=tone)
            self.grid.addWidget(widget, 0, i * 2, 1, 2)
            self.metrics.append((widget, key))
        self.pareto_frame, layout = card()
        self.pareto = ParetoWidget()
        layout.addWidget(self.pareto)
        self.top80 = label("暂无数据", "empty", True)
        layout.addWidget(self.top80)
        self.grid.addWidget(self.pareto_frame, 1, 0, 1, 10)
        self.trend_frame, layout = card()
        self.trend = ChartWidget("不良率趋势")
        layout.addWidget(self.trend)
        self.grid.addWidget(self.trend_frame, 2, 0, 1, 5)
        self.team_frame, layout = card()
        self.team_chart = ChartWidget("组别不良率")
        layout.addWidget(self.team_chart)
        self.grid.addWidget(self.team_frame, 2, 5, 1, 5)
        self.ranking = table(
            ["编码", "不良项目", "出现批次", "已填件数", "未填件数批次", "累计占比"]
        )
        table_minimum_rows(self.ranking, 10)
        self.ranking.setColumnWidth(1, 240)
        align_table_columns(self.ranking, right=(2, 3, 4, 5))
        self.grid.addWidget(self.ranking, 3, 0, 1, 10)
        self.teams_table = table(
            ["组别", "检验数", "抽检数", "不良数", "不良率", "合格批次", "返工批次", "返工率"]
        )
        table_minimum_rows(self.teams_table, 8)
        align_table_columns(self.teams_table, right=(1, 2, 3, 4, 5, 6, 7))
        self.grid.addWidget(self.teams_table, 4, 0, 1, 10)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)
        self._reflow_layout()

    def _reflow_layout(self):
        mode = "wide" if self.width() >= WIDE_LAYOUT_BREAKPOINT else "narrow"
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        if mode == "wide":
            for col, (caption, widget) in enumerate(self.filter_controls):
                grid_place(self.filters_grid, caption, 0, col)
                grid_place(self.filters_grid, widget, 1, col)
            grid_place(self.filters_grid, self.analyze_button, 1, 5)
            for col in range(6):
                self.filters_grid.setColumnStretch(col, 1 if col < 5 else 0)
            for i, (widget, _key) in enumerate(self.metrics):
                grid_place(self.grid, widget, 0, i * 2, 1, 2)
            grid_place(self.grid, self.pareto_frame, 1, 0, 1, 10)
            grid_place(self.grid, self.trend_frame, 2, 0, 1, 5)
            grid_place(self.grid, self.team_frame, 2, 5, 1, 5)
            grid_place(self.grid, self.ranking, 3, 0, 1, 10)
            grid_place(self.grid, self.teams_table, 4, 0, 1, 10)
        else:
            for index, (caption, widget) in enumerate(self.filter_controls):
                block, col = divmod(index, 3)
                row = block * 2
                grid_place(self.filters_grid, caption, row, col)
                grid_place(self.filters_grid, widget, row + 1, col)
            grid_place(self.filters_grid, self.analyze_button, 3, 2)
            for col in range(6):
                self.filters_grid.setColumnStretch(col, 1 if col < 3 else 0)
            for i, (widget, _key) in enumerate(self.metrics):
                grid_place(self.grid, widget, i // 2, (i % 2) * 5, 1, 5)
            grid_place(self.grid, self.pareto_frame, 3, 0, 1, 10)
            grid_place(self.grid, self.trend_frame, 4, 0, 1, 10)
            grid_place(self.grid, self.team_frame, 5, 0, 1, 10)
            grid_place(self.grid, self.ranking, 6, 0, 1, 10)
            grid_place(self.grid, self.teams_table, 7, 0, 1, 10)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "grid"):
            self._reflow_layout()

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

    def date_range_valid(self):
        return self.start.date() <= self.end.date()

    def mark_stale(self, *_):
        valid = self.date_range_valid()
        self.analyze_button.setEnabled(valid)
        self.scope.setText(
            "筛选条件已更改 · 点击“开始分析”更新结果"
            if valid
            else "日期范围无效：开始日期不能晚于结束日期"
        )
        set_label_kind(self.scope, "warning" if valid else "error")

    @guarded
    def refresh(self, *_):
        self.sync_preset_range()
        if not self.date_range_valid():
            self.mark_stale()
            return
        filters = RecordFilter(
            start=self.start.date().toPython(),
            end=self.end.date().toPython(),
            source="demo" if self.source.currentIndex() else "production",
        )
        self.scope.setText(
            f"当前范围：{filters.start} 至 {filters.end} · {self.source.currentText()} · {self.metric_choice.currentText()}"
        )
        set_label_kind(self.scope, "status")
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
        set_label_kind(self.top80, "summary" if important else "empty")
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
