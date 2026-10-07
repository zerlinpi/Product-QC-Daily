import calendar
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QFileDialog, QSpinBox, QStyle

from app.core.labels import import_status_label
from app.core.schemas import RecordFilter
from app.ui.common import (
    FILTER_FIELD_MIN_WIDTH,
    WIDE_LAYOUT_BREAKPOINT,
    Page,
    button,
    control_metrics,
    field_label,
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

REPORT_SCOPES = ["全年", "单月", "具体日期", "自定义区间"]


class ReportsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "报表中心", "导入前先检查内容；导出时可按全年、单月、具体日期或自定义日期范围选择数据"
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
        self.import_button = button(
            "选择表格并预览",
            self.import_file,
            primary=True,
            icon=QStyle.StandardPixmap.SP_DialogOpenButton,
        )
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

        today = date.today()
        self.preset = QComboBox()
        self.preset.addItems(REPORT_SCOPES)
        self.preset.setCurrentText("全年")

        self.year = QSpinBox()
        self.year.setRange(2000, 2100)
        self.year.setValue(today.year)
        self.year.setSuffix(" 年")

        self.month = QComboBox()
        for month in range(1, 13):
            self.month.addItem(f"{month:02d} 月", month)
        self.month.setCurrentIndex(today.month - 1)

        self.day = QDateEdit(QDate(today))
        self.start = QDateEdit(QDate(today.year, 1, 1))
        self.end = QDateEdit(QDate(today.year, 12, 31))
        for widget in (self.day, self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")

        self.source = QComboBox()
        self.source.addItems(["正式数据", "演示数据"])

        controls = [
            ("导出范围", self.preset),
            ("年份", self.year),
            ("月份", self.month),
            ("具体日期", self.day),
            ("开始日期", self.start),
            ("结束日期", self.end),
            ("数据范围", self.source),
        ]
        control_metrics(*[widget for _, widget in controls], min_width=FILTER_FIELD_MIN_WIDTH)
        self.filter_controls = []
        for title, widget in controls:
            caption = field_label(title, widget)
            self.filter_controls.append((caption, widget))
            self.filters_grid.addWidget(caption, 0, 0)
            self.filters_grid.addWidget(widget, 1, 0)
        layout.addLayout(self.filters_grid)

        self.export_scope = label("", "status", True)
        layout.addWidget(self.export_scope)

        self.preset.currentTextChanged.connect(self.set_range)
        self.year.valueChanged.connect(self._period_changed)
        self.month.currentIndexChanged.connect(self._period_changed)
        self.day.dateChanged.connect(self._period_changed)
        self.source.currentIndexChanged.connect(self.update_scope_text)
        self.start.dateChanged.connect(self.update_scope_text)
        self.end.dateChanged.connect(self.update_scope_text)

        self.set_range("全年")
        layout.addWidget(
            label(
                "全年适合年度归档；单月用于月报；具体日期用于指定某一天；自定义区间用于跨月或临时范围。明细报表导出后还可直接按年份、月份或日期筛选。",
                "muted",
                True,
            )
        )

        export_actions = toolbar_layout()
        self.original_export = button(
            "按原表导出",
            lambda: self.export(True),
            primary=True,
            icon=QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        self.original_export.setToolTip("按所选日期范围写入数据，并完整保留原始表格、公式和 6 张图表布局")
        self.detailed_export = button(
            "导出明细报表",
            lambda: self.export(False),
            icon=QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        self.detailed_export.setToolTip("适合年度分析：Excel 内可按年份、月份、具体日期继续筛选")
        export_actions.addStretch()
        export_actions.addWidget(self.detailed_export)
        export_actions.addWidget(self.original_export)
        layout.addLayout(export_actions)
        layout.addWidget(
            label(
                "需要与你上传的成品日检表一致的版式，请选“按原表导出”；需要全年后再筛月份或具体日期，请选“导出明细报表”。",
                "muted",
                True,
            )
        )
        self.layout.addWidget(panel)
        self.layout.addStretch()
        self._reflow_filters(force=True)

    def _active_filter_widgets(self):
        mode = self.preset.currentText()
        active = [self.preset]
        if mode in {"全年", "单月", "具体日期"}:
            active.append(self.year)
        if mode == "单月":
            active.append(self.month)
        elif mode == "具体日期":
            active.append(self.day)
        elif mode == "自定义区间":
            active.extend([self.start, self.end])
        active.append(self.source)
        return set(active)

    def _update_filter_visibility(self):
        active = self._active_filter_widgets()
        for caption, widget in self.filter_controls:
            visible = widget in active
            caption.setVisible(visible)
            widget.setVisible(visible)

    def _reflow_filters(self, force=False):
        mode = "wide" if self.width() >= WIDE_LAYOUT_BREAKPOINT else "narrow"
        if mode == self._layout_mode and not force:
            return
        self._layout_mode = mode
        active = [
            (caption, widget)
            for caption, widget in self.filter_controls
            if not widget.isHidden()
        ]
        for caption, widget in self.filter_controls:
            self.filters_grid.removeWidget(caption)
            self.filters_grid.removeWidget(widget)
        for col in range(len(self.filter_controls)):
            self.filters_grid.setColumnStretch(col, 0)
        if mode == "wide":
            for col, (caption, widget) in enumerate(active):
                grid_place(self.filters_grid, caption, 0, col)
                grid_place(self.filters_grid, widget, 1, col)
                self.filters_grid.setColumnStretch(col, 1)
        else:
            for index, (caption, widget) in enumerate(active):
                block, col = divmod(index, 2)
                row = block * 2
                grid_place(self.filters_grid, caption, row, col)
                grid_place(self.filters_grid, widget, row + 1, col)
                self.filters_grid.setColumnStretch(col, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "filters_grid"):
            self._reflow_filters()

    def selected_range(self):
        mode = self.preset.currentText()
        if mode == "全年":
            year = self.year.value()
            return date(year, 1, 1), date(year, 12, 31)
        if mode == "单月":
            year, month = self.year.value(), int(self.month.currentData())
            return date(year, month, 1), date(
                year, month, calendar.monthrange(year, month)[1]
            )
        if mode == "具体日期":
            chosen = self.day.date().toPython()
            year = self.year.value()
            day = min(chosen.day, calendar.monthrange(year, chosen.month)[1])
            chosen = date(year, chosen.month, day)
            return chosen, chosen
        return self.start.date().toPython(), self.end.date().toPython()

    def sync_preset_range(self):
        if self.preset.currentText() == "自定义区间":
            return
        start, end = self.selected_range()
        for widget, value in ((self.start, start), (self.end, end)):
            previous = widget.blockSignals(True)
            widget.setDate(QDate(value))
            widget.blockSignals(previous)

    def _sync_day_to_year(self):
        year = self.year.value()
        current = self.day.date().toPython()
        selected = date(
            year,
            current.month,
            min(current.day, calendar.monthrange(year, current.month)[1]),
        )
        blocked = self.day.blockSignals(True)
        self.day.setMinimumDate(QDate(year, 1, 1))
        self.day.setMaximumDate(QDate(year, 12, 31))
        self.day.setDate(QDate(selected))
        self.day.blockSignals(blocked)

    def _period_changed(self, *_):
        self._sync_day_to_year()
        self.sync_preset_range()
        self.update_scope_text()

    def set_range(self, _name):
        self._sync_day_to_year()
        self._update_filter_visibility()
        self.sync_preset_range()
        self.update_scope_text()
        if hasattr(self, "filters_grid"):
            self._reflow_filters(force=True)

    def refresh(self):
        self.sync_preset_range()
        self.update_scope_text()

    def scope_description(self, start, end):
        mode = self.preset.currentText()
        if mode == "全年":
            return f"{start.year} 全年"
        if mode == "单月":
            return f"{start.year} 年 {start.month:02d} 月"
        if mode == "具体日期":
            return str(start)
        return f"{start} 至 {end}"

    def update_scope_text(self, *_):
        self.sync_preset_range()
        start, end = self.selected_range()
        valid = start <= end
        for name in ("original_export", "detailed_export"):
            control = getattr(self, name, None)
            if control is not None:
                control.setEnabled(valid)
        if valid:
            self.export_scope.setText(
                f"将导出：{self.scope_description(start, end)} · "
                f"{start} 至 {end} · {self.source.currentText()}"
            )
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
        start, end = self.selected_range()
        if start > end:
            self.update_scope_text()
            return
        filters = RecordFilter(
            start=start,
            end=end,
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
