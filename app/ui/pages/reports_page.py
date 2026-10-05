from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QFileDialog, QGridLayout

from app.core.labels import import_status_label
from app.core.schemas import RecordFilter
from app.services.statistics_service import PRESETS, date_range
from app.ui.common import Page, button, card, guarded, label
from app.ui.dialogs import file_dialogs
from app.ui.dialogs.import_dialog import ImportDialog


class ReportsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "报表中心", "导入前先检查内容；导出时选择日期范围和报表格式"
        )
        panel, layout = card()
        layout.addWidget(label("导入历史日检表", "section"))
        layout.addWidget(
            label(
                "支持原始成品日检表与本软件导出的明细报表。自动识别记录工作表，拆分不良编码，并导出异常清单。源文件不会被修改。",
                "muted",
                True,
            )
        )
        layout.addWidget(button("选择表格并预览", self.import_file, primary=True))
        self.import_status = label("尚未选择文件", "muted", True)
        layout.addWidget(self.import_status)
        self.layout.addWidget(panel)
        panel, layout = card()
        layout.addWidget(label("导出质量报表", "section"))
        filters = QGridLayout()
        filters.setHorizontalSpacing(12)
        filters.setVerticalSpacing(6)
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
        for col, (title, widget) in enumerate(controls):
            filters.addWidget(label(title, "fieldLabel"), 0, col)
            filters.addWidget(widget, 1, col)
        layout.addLayout(filters)
        self.export_scope = label("", "muted", True)
        layout.addWidget(self.export_scope)
        self.preset.currentTextChanged.connect(self.set_range)
        self.source.currentIndexChanged.connect(self.update_scope_text)
        self.start.dateChanged.connect(self.update_scope_text)
        self.end.dateChanged.connect(self.update_scope_text)
        self.set_range("本月")
        layout.addWidget(
            label(
                "日报选“今天”、周报选“本周”、月报选“本月”。筛选记录和选中记录可在检验记录页导出。",
                "muted",
                True,
            )
        )
        layout.addWidget(
            button(
                "按原表导出 · 保留表格与图表布局", lambda: self.export(True), primary=True
            )
        )
        layout.addWidget(
            button("导出明细报表 · 保留检验员与逐项件数", lambda: self.export(False))
        )
        layout.addWidget(
            label(
                "需要原有表格样式，请选“按原表导出”；需要完整检验员、备注和逐项件数，请选“导出明细报表”。用电子表格软件打开文件后，统计公式会自动重新计算。",
                "muted",
                True,
            )
        )
        self.layout.addWidget(panel)
        self.layout.addStretch()

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
        self.export_scope.setText(
            f"将导出：{self.start.date().toPython()} 至 {self.end.date().toPython()} · {self.source.currentText()}"
        )

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择成品日检表", "", "电子表格 (*.xlsx)")
        if path:
            self.import_status.setText(path)
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
        self.window.notify(f"成功导入 {count} 条记录；历史日期数据可在检验记录页查询")

    @guarded
    def export(self, legacy):
        self.sync_preset_range()
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
