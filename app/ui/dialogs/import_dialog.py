from pathlib import Path

from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QHBoxLayout, QVBoxLayout

from app.core.labels import IMPORT_STATUS_LABELS, import_status_label
from app.ui.common import button, label, populate, table


class ImportDialog(QDialog):
    def __init__(self, ctx, window, preview):
        super().__init__(window)
        self.ctx, self.window, self.preview = ctx, window, preview
        self.page = 1
        self.setWindowTitle("表格导入预览")
        self.resize(1040, 680)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(label("检查导入内容", "title"))
        layout.addWidget(label(f"工作表：{preview.sheet} · 总记录：{len(preview.rows)}", "muted"))
        layout.addWidget(
            label(
                "   ".join(
                    f"{import_status_label(key)} {value}" for key, value in preview.counts.items()
                ),
                "section",
            )
        )
        layout.addWidget(
            label(
                "检查完成后再点击导入。只保存正常记录，重复与异常记录会跳过；原表未提供的逐项件数保持未知。",
                "muted",
                True,
            )
        )
        self.filter = QComboBox()
        self.filter.addItem("全部状态", "")
        for key, value in IMPORT_STATUS_LABELS.items():
            self.filter.addItem(value, key)
        self.filter.currentIndexChanged.connect(self.reset_page)
        layout.addWidget(self.filter)
        self.table = table(["表格行号", "记录编号", "状态", "说明 / 异常原因"])
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 245)
        self.table.setColumnWidth(2, 100)
        layout.addWidget(self.table, 1)
        pagination = QHBoxLayout()
        self.count = label("", "muted")
        pagination.addWidget(self.count, 1)
        self.previous_button = button("上一页", lambda: self.turn(-1))
        self.next_button = button("下一页", lambda: self.turn(1))
        pagination.addWidget(self.previous_button)
        pagination.addWidget(self.next_button)
        layout.addLayout(pagination)
        actions = QHBoxLayout()
        report_button = button("导出异常报告", self.report)
        report_button.setEnabled(
            any(key != "valid" and count for key, count in preview.counts.items())
        )
        report_button.setToolTip("将重复、冲突和异常记录另存为表格，便于核对")
        actions.addWidget(report_button)
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
                    import_status_label(r.status),
                    r.message or "可导入；逐项件数以原表提供内容为准",
                ]
                for r in rows[(self.page - 1) * 200 : self.page * 200]
            ],
        )
        pages = max(1, (len(rows) + 199) // 200)
        self.count.setText(f"共 {len(rows)} 条 · 第 {self.page} / {pages} 页 · 每页 200 条")
        self.previous_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < pages)

    def report(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出异常报告",
            str(self.ctx.paths.exports / "导入异常报告.xlsx"),
            "电子表格 (*.xlsx)",
        )
        if path:
            self.setEnabled(False)
            self.window.run_job(
                "导出异常报告",
                lambda: self.ctx.excel.export_issues(self.preview, Path(path)),
                lambda result: self.window.notify(f"异常报告：{result}"),
                finished=lambda: self.setEnabled(True),
            )
