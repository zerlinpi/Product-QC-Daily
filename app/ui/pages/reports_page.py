from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QStyle,
)

from app.core.labels import import_status_label
from app.core.schemas import RecordFilter
from app.services.statistics_service import PRESETS, date_range
from app.ui.common import (
    WIDE_LAYOUT_BREAKPOINT,
    FILTER_FIELD_MIN_WIDTH,
    Page,
    button,
    control_metrics,
    form_grid,
    grid_place,
    guarded,
    label,
    native_group,
    set_label_kind,
    toolbar_layout,
)
from app.ui.dialogs import file_dialogs
from app.ui.dialogs.import_dialog import ImportDialog


class ReportsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "报表中心", "导入前先检查内容；导出时选择日期范围和报表格式"
        )
        panel, layout = native_group("导入历史日检表")
        layout.addWidget(
            label(
                "支持原始成品日检表与本软件导出的明细报表。自动识别记录工作表，拆分不良编码，并导出异常清单。源文件不会被修改。",
                "muted",
                True,
            )
        )
        import_actions = toolbar_layout()
        self.import_button = button("选择表格并预览", self.import_file, primary=True)
        self.import_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        import_actions.addWidget(self.import_button)
        import_actions.addStretch()
        layout.addLayout(import_actions)
        self.import_status = label("尚未选择文件", "summary", True)
        self.import_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.import_status)
        self.layout.addWidget(panel)
        panel, layout = native_group("导出质量报表")
        self.filters_grid = form_grid()
        self._layout_mode = None
        self.preset, self.source = QComboBox(), QComboBox()
        self.preset.addItems(PRESETS)
        self.preset.setCurrentText("本月")
        self.source.addItems(["正式数据", "演示数据"])
        self.start, self.end = QDateEdit(), QDateEdit()
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        controls = [
            ("报表周期", self.preset),
            ("开始日期", self.start),
            ("结束日期", self.end),
            ("数据范围", self.source),
        ]
        control_metrics(*[widget for _, widget in controls], min_width=FILTER_FIELD_MIN_WIDTH)
        self.filter_controls = []
        for col, (title, widget) in enumerate(controls):
            caption = label(title, "fieldLabel")
            self.filter_controls.append((caption, widget))
            self.filters_grid.addWidget(caption, 0, col)
            self.filters_grid.addWidget(widget, 1, col)
        layout.addLayout(self.filters_grid)
        self.export_scope = label("", "status", True)
        layout.addWidget(self.export_scope)
        self.preset.currentTextChanged.connect(self.set_range)
        self.source.currentIndexChanged.connect(self.update_scope_text)
        self.start.dateChanged.connect(self.update_scope_text)
        self.end.dateChanged.connect(self.update_scope_text)
        self.set_range("本月")
        layout.addWidget(
            label(
                "日报选“今天”、周报选“本周”、月报选“本月”、年度报表选“本年”。演示数据也可直接导出；明细报表支持按月份筛选。",
                "muted",
                True,
            )
        )
        export_actions = toolbar_layout()
        self.original_export = button("按原表导出", lambda: self.export(True), primary=True)
        self.original_export.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.original_export.setToolTip("保留原始表格、公式和 6 张图表布局")
        self.detailed_export = button("导出明细报表", lambda: self.export(False))
        self.detailed_export.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.detailed_export.setToolTip("适合年度分析：月份筛选、统计摘要、月度统计和趋势图")
        export_actions.addStretch()
        export_actions.addWidget(self.detailed_export)
        export_actions.addWidget(self.original_export)
        layout.addLayout(export_actions)
        layout.addWidget(
            label(
                "需要原有表格样式，请选“按原表导出”；年度分析建议使用“导出明细报表”，其中记录表可按月份筛选，并附月度统计与趋势图。原表模板布局保持不变。",
                "muted",
                True,
            )
        )
        self.layout.addWidget(panel)
        self.update_scope_text()
        self.layout.addStretch()
        self._reflow_filters()

    def _reflow_filters(self):
        mode = "wide" if self.width() >= WIDE_LAYOUT_BREAKPOINT else "narrow"
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        if mode == "wide":
            for col, (caption, widget) in enumerate(self.filter_controls):
                grid_place(self.filters_grid, caption, 0, col)
                grid_place(self.filters_grid, widget, 1, col)
            for col in range(4):
                self.filters_grid.setColumnStretch(col, 1)
        else:
            for index, (caption, widget) in enumerate(self.filter_controls):
                block, col = divmod(index, 2)
                row = block * 2
                grid_place(self.filters_grid, caption, row, col)
                grid_place(self.filters_grid, widget, row + 1, col)
            for col in range(4):
                self.filters_grid.setColumnStretch(col, 1 if col < 2 else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "filters_grid"):
            self._reflow_filters()

    def sync_preset_range(self):
        name = self.preset.currentText()
        if name == "自定义":
            return
        start, end = date_range(name)
        for widget, value in ((self.start, start), (self.end, end)):
            previous = widget.blockSignals(True)
            widget.setDate(QDate(value))
            widget.blockSignals(previous)

    def set_range(self, name):
        self.start.setEnabled(name == "自定义")
        self.end.setEnabled(name == "自定义")
        if name != "自定义":
            self.sync_preset_range()
        self.update_scope_text()

    def refresh(self):
        self.sync_preset_range()
        self.update_scope_text()

    def update_scope_text(self, *_):
        start = self.start.date().toPython()
        end = self.end.date().toPython()
        valid = start <= end
        for name in ("original_export", "detailed_export"):
            control = getattr(self, name, None)
            if control is not None:
                control.setEnabled(valid)
        if valid:
            self.export_scope.setText(f"将导出：{start} 至 {end} · {self.source.currentText()}")
            set_label_kind(self.export_scope, "status")
        else:
            self.export_scope.setText("日期范围无效：开始日期不能晚于结束日期")
            set_label_kind(self.export_scope, "error")

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择成品日检表", "", "电子表格 (*.xlsx)")
        if path:
            self.import_status.setText(f"当前文件：{path}")
            self.import_status.setToolTip(path)
            self.window.run_job(
                "读取表格并检查内容", lambda: self.ctx.excel.preview(Path(path)), self.show_preview
            )

    def show_preview(self, preview):
        if ImportDialog(self.ctx, self.window, preview).exec():
            self.window.run_job(
                "导入正常记录",
                lambda: self.ctx.excel.import_preview(preview),
                lambda count: self.import_done(count, preview),
            )

    def import_done(self, count, preview):
        self.import_status.setText(
            f"已导入 {count} 条 · "
            + " / ".join(
                f"{import_status_label(key)}: {value}" for key, value in preview.counts.items()
            )
        )
        set_label_kind(self.import_status, "success")
        self.window.notify(f"成功导入 {count} 条记录；历史日期数据可在检验记录页查询")

    @guarded
    def export(self, legacy):
        self.sync_preset_range()
        if self.start.date() > self.end.date():
            self.update_scope_text()
            return
        filters = RecordFilter(
            start=self.start.date().toPython(),
            end=self.end.date().toPython(),
            source="demo" if self.source.currentIndex() else "production",
        )
        directory = Path(self.ctx.settings.get("export_directory") or self.ctx.paths.exports)
        kind = "原表日检表" if legacy else "检验明细报表"
        path, _ = file_dialogs.save_excel(
            self,
            "导出报表",
            str(directory / f"{kind}_{filters.start}_{filters.end}.xlsx"),
            "电子表格 (*.xlsx)",
        )
        if path:
            self.window.run_job(
                "导出质量报表",
                lambda: self.ctx.excel.export(Path(path), filters, legacy=legacy),
                self.window.export_completed,
            )
