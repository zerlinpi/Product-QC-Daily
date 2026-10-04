from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLineEdit

from app.ui.common import Page, button, confirm, guarded, populate, table
from app.ui.dialogs.defect_dialog import DefectDialog


class DefectsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx,
            window,
            "不良项目",
            "维护录入时可选的不良项目；停用后不再用于新记录，历史记录仍保留",
        )
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索项目名称或编码")
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(button("新增项目", self.add, primary=True))
        self.edit_button = button("编辑项目", self.edit)
        self.disable_button = button("停用项目", self.disable, danger=True)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.disable_button)
        self.layout.addLayout(toolbar)
        self.table = table(["编码", "名称", "分类", "状态", "排序", "说明"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setColumnWidth(1, 290)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        self.layout.addWidget(self.table, 1)
        self.rows = []
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.update_actions()

    @guarded
    def refresh(self, *_):
        self.table.clearSelection()
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
        self.update_actions()

    def update_actions(self):
        item = self.selected() if self.table.selectedItems() else None
        self.edit_button.setEnabled(item is not None)
        self.disable_button.setEnabled(bool(item and item["enabled"]))

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
            and item["enabled"]
            and confirm(
                self,
                "停用项目",
                f"停用“{item['name']}”？历史记录仍可查询。",
                action="停用项目",
            )
        ):
            self.ctx.defects.disable(item["id"])
            self.refresh()
