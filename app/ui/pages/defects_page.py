from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMessageBox

from app.ui.common import Page, button, guarded, populate, table
from app.ui.dialogs.defect_dialog import DefectDialog


class DefectsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx,
            window,
            "不良项目",
            "统一维护检验字典 · 已有历史记录的项目可以停用，历史数据继续保留",
        )
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索项目名称或编码")
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(button("新增项目", self.add, primary=True))
        toolbar.addWidget(button("编辑", self.edit))
        toolbar.addWidget(button("停用", self.disable, danger=True))
        self.layout.addLayout(toolbar)
        self.table = table(["编码", "名称", "分类", "状态", "排序", "说明"])
        self.table.setColumnWidth(1, 290)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        self.layout.addWidget(self.table, 1)
        self.rows = []

    @guarded
    def refresh(self, *_):
        self.rows = self.ctx.defects.list(self.search.text())
        populate(
            self.table,
            [
                [
                    r["code"],
                    r["name"],
                    r["category"],
                    "启用" if r["enabled"] else "停用",
                    r["sort_order"],
                    r["description"],
                ]
                for r in self.rows
            ],
        )

    def selected(self):
        row = self.table.currentRow()
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def add(self):
        if DefectDialog(self.ctx, self).exec():
            self.refresh()

    def edit(self):
        item = self.selected()
        if item and DefectDialog(self.ctx, self, item).exec():
            self.refresh()

    @guarded
    def disable(self):
        item = self.selected()
        if (
            item
            and QMessageBox.question(
                self,
                "停用项目",
                f"停用“{item['name']}”？历史记录仍可查询。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.ctx.defects.disable(item["id"])
            self.refresh()
