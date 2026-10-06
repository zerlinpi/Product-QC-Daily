from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QStyle, QVBoxLayout

from app.core.labels import IMPORT_STATUS_LABELS, import_status_label
from app.ui.common import button, guarded, label, populate, table
from app.ui.dialogs import file_dialogs


class ImportDialog(QDialog):
    def __init__(self, ctx, window, preview):
        super().__init__(window)
        self.ctx, self.window, self.preview = ctx, window, preview
        self.page = 1
        self.setWindowTitle("表格导入预览")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(1040, 680)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(label("检查导入内容", "title"))
        layout.addWidget(label(f"工作表：{preview.sheet} · 总记录：{len(preview.rows)}", "muted"))
        self.summary = label(
            "   ".join(
                f"{import_status_label(key)} {value}" for key, value in preview.counts.items()
            ),
            "status",
        )
        layout.addWidget(self.summary)
        layout.addWidget(
            label(
                "检查完成后再点击导入。只保存正常记录，重复与异常记录会跳过；原表未提供的逐项件数保持未知。",
                "muted",
                True,
            )
        )
        filter_row = QHBoxLayout()
        filter_row.addWidget(label("显示", "fieldLabel"))
        self.filter = QComboBox()
        self.filter.setAccessibleName("导入状态筛选")
        self.filter.setMinimumWidth(150)
        self.filter.addItem("全部状态", "")
        for key, value in IMPORT_STATUS_LABELS.items():
            self.filter.addItem(value, key)
        self.filter.currentIndexChanged.connect(self.reset_page)
        filter_row.addWidget(self.filter)
        self.visible_status = label("", "muted")
        filter_row.addWidget(self.visible_status)
        filter_row.addStretch()
        layout.addLayout(filter_row)
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
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        report_button = button("导出异常报告", self.report)
        report_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        report_button.setEnabled(any(row.status != "valid" or row.message for row in preview.rows))
        report_button.setToolTip("将重复、冲突、异常和签名警告另存为表格，便于核对")
        actions.addButton(report_button, QDialogButtonBox.ButtonRole.ActionRole)
        accept = actions.addButton(
            f"导入 {preview.counts['valid']} 条正常记录",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        accept.setEnabled(preview.counts["valid"] > 0)
        accept.setDefault(True)
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)
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
        page_rows = rows[(self.page - 1) * 200 : self.page * 200]
        populate(
            self.table,
            [
                [
                    r.row_number,
                    r.inspection_no,
                    import_status_label(r.status),
                    r.message or "可导入；逐项件数以原表提供内容为准",
                ]
                for r in page_rows
            ],
        )
        status_colors = {
            "valid": "#107c10",
            "duplicate": "#ca5010",
            "conflict": "#ca5010",
            "invalid": "#c42b1c",
            "unrecognized": "#c42b1c",
        }
        for index, row in enumerate(page_rows):
            status_item = self.table.item(index, 2)
            status_item.setForeground(QColor(status_colors.get(row.status, "#616161")))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        pages = max(1, (len(rows) + 199) // 200)
        self.visible_status.setText(f"当前显示 {len(rows)} 条")
        self.count.setText(f"共 {len(rows)} 条 · 第 {self.page} / {pages} 页 · 每页 200 条")
        self.previous_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < pages)

    @guarded
    def report(self):
        directory = Path(
            self.ctx.settings.get("export_directory") or self.ctx.paths.exports
        ).expanduser()
        path, _ = file_dialogs.save_excel(
            self,
            "导出异常报告",
            str(directory / "导入异常报告.xlsx"),
            "电子表格 (*.xlsx)",
        )
        if path:
            self.setEnabled(False)
            self.window.run_job(
                "导出异常报告",
                lambda: self.ctx.excel.export_issues(self.preview, Path(path)),
                self.window.export_completed,
                finished=lambda: self.setEnabled(True),
            )
