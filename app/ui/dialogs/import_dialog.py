from pathlib import Path

from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QHBoxLayout, QVBoxLayout

from app.ui.common import button, label, populate, table

STATUS = {
    "valid": "正常",
    "duplicate": "重复",
    "conflict": "ID冲突",
    "invalid": "异常",
    "unrecognized": "无法识别",
}


class ImportDialog(QDialog):
    def __init__(self, ctx, window, preview):
        super().__init__(window)
        self.ctx, self.window, self.preview = ctx, window, preview
        self.page = 1
        self.setWindowTitle("Excel 导入预览")
        self.resize(1040, 680)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(label("检查导入内容", "title"))
        layout.addWidget(label(f"工作表：{preview.sheet} · 总记录：{len(preview.rows)}", "muted"))
        layout.addWidget(
            label(
                "   ".join(f"{STATUS[key]} {value}" for key, value in preview.counts.items()),
                "section",
            )
        )
        layout.addWidget(
            label("只导入正常记录；重复和异常不会覆盖数据库。旧表逐项件数保持未知。", "muted", True)
        )
        self.filter = QComboBox()
        self.filter.addItem("全部状态", "")
        for key, value in STATUS.items():
            self.filter.addItem(value, key)
        self.filter.currentIndexChanged.connect(self.reset_page)
        layout.addWidget(self.filter)
        self.table = table(["Excel行", "填写ID", "状态", "说明 / 异常原因"])
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 245)
        self.table.setColumnWidth(2, 100)
        layout.addWidget(self.table, 1)
        pagination = QHBoxLayout()
        self.count = label("", "muted")
        pagination.addWidget(self.count, 1)
        pagination.addWidget(button("上一页", lambda: self.turn(-1)))
        pagination.addWidget(button("下一页", lambda: self.turn(1)))
        layout.addLayout(pagination)
        actions = QHBoxLayout()
        actions.addWidget(button("导出异常报告", self.report))
        actions.addStretch()
        actions.addWidget(button("取消", self.reject))
        accept = button(f"导入 {preview.counts['valid']} 条正常记录", self.accept, primary=True)
        accept.setEnabled(preview.counts["valid"] > 0)
        actions.addWidget(accept)
        layout.addLayout(actions)
        self.refresh()

    def filtered(self):
        key = self.filter.currentData()
        return [r for r in self.preview.rows if not key or r.status == key]

    def reset_page(self):
        self.page = 1
        self.refresh()

    def turn(self, delta):
        self.page = min(max(1, self.page + delta), max(1, (len(self.filtered()) + 199) // 200))
        self.refresh()

    def refresh(self):
        rows = self.filtered()
        populate(
            self.table,
            [
                [
                    r.row_number,
                    r.inspection_no,
                    STATUS[r.status],
                    r.message or "可导入；逐项件数以原表提供内容为准",
                ]
                for r in rows[(self.page - 1) * 200 : self.page * 200]
            ],
        )
        self.count.setText(f"共 {len(rows)} 条 · 第 {self.page} 页 · 每页 200 条")

    def report(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出异常报告",
            str(self.ctx.paths.exports / "导入异常报告.xlsx"),
            "Excel (*.xlsx)",
        )
        if path:
            self.setEnabled(False)
            self.window.run_job(
                "导出异常报告",
                lambda: self.ctx.excel.export_issues(self.preview, Path(path)),
                lambda result: self.window.notify(f"异常报告：{result}"),
                finished=lambda: self.setEnabled(True),
            )
