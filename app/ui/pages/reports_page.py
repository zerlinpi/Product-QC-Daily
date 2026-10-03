from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QFileDialog, QHBoxLayout

from app.core.labels import import_status_label
from app.core.schemas import RecordFilter
from app.services.statistics_service import PRESETS, date_range
from app.ui.common import Page, button, card, guarded, label
from app.ui.dialogs.import_dialog import ImportDialog


class ReportsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "报表中心", "连接原有 Excel 工作方式 · 导入有预览，导出有明确的统计口径"
        )
        panel, layout = card()
        layout.addWidget(label("导入历史日检表", "section"))
        layout.addWidget(
            label(
                "支持原始成品日检表与本软件标准报表。自动识别记录工作表，拆分不良编码，并导出异常清单。源文件不会被修改。",
                "muted",
                True,
            )
        )
        layout.addWidget(button("选择 Excel 并预览", self.import_file, primary=True))
        self.import_status = label("尚未选择文件", "muted", True)
        layout.addWidget(self.import_status)
        self.layout.addWidget(panel)
        panel, layout = card()
        layout.addWidget(label("导出质量报表", "section"))
        filters = QHBoxLayout()
        self.preset, self.source = QComboBox(), QComboBox()
        self.preset.addItems(PRESETS)
        self.preset.setCurrentText("本月")
        self.source.addItems(["正式数据", "演示数据"])
        self.start, self.end = QDateEdit(), QDateEdit()
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        for widget in (self.preset, self.start, self.end, self.source):
            filters.addWidget(widget)
        layout.addLayout(filters)
        self.preset.currentTextChanged.connect(self.set_range)
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
            button("导出标准报表 · 记录 + 不良明细 + 统计", lambda: self.export(False))
        )
        layout.addWidget(
            label(
                "标准报表完整保留逐项已知数量和检验员。兼容报表沿用旧表列布局；WPS 签名转换为普通图片。公式由 Excel / WPS 打开时重算，Windows 安装 Excel 时自动尝试 COM 重算。",
                "muted",
                True,
            )
        )
        self.layout.addWidget(panel)
        self.layout.addStretch()

    def set_range(self, name):
        self.start.setEnabled(name == "自定义")
        self.end.setEnabled(name == "自定义")
        if name != "自定义":
            start, end = date_range(name)
            self.start.setDate(QDate(start))
            self.end.setDate(QDate(end))

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择成品日检表", "", "Excel (*.xlsx)")
        if path:
            self.import_status.setText(path)
            self.window.run_job(
                "分析 Excel 文件", lambda: self.ctx.excel.preview(Path(path)), self.show_preview
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
        filters = RecordFilter(
            start=self.start.date().toPython(),
            end=self.end.date().toPython(),
            source="demo" if self.source.currentIndex() else "production",
        )
        directory = Path(self.ctx.settings.get("export_directory") or self.ctx.paths.exports)
        kind = "兼容日检表" if legacy else "质量报表"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出报表",
            str(directory / f"{kind}_{filters.start}_{filters.end}.xlsx"),
            "Excel (*.xlsx)",
        )
        if path:
            self.window.run_job(
                "生成 Excel 报表",
                lambda: self.ctx.excel.export(Path(path), filters, legacy=legacy),
                lambda result: self.window.notify(f"导出成功：{result}"),
            )
