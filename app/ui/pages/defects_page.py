from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLineEdit

from app.ui.common import (
    Page,
    align_table_columns,
    button,
    confirm,
    guarded,
    label,
    native_group,
    populate,
    table,
    toolbar_layout,
)
from app.ui.dialogs.defect_dialog import DefectDialog


class DefectsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx,
            window,
            "不良项目",
            "维护录入时可选的不良项目；停用后不再用于新记录，历史记录仍保留",
        )
        group, group_layout = native_group("项目列表")
        toolbar = toolbar_layout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索项目名称或编码")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(260)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)
        self.count = label("", "summary")
        toolbar.addWidget(self.count)
        toolbar.addStretch()
        toolbar.addWidget(button("新增项目", self.add, primary=True))
        self.edit_button = button("编辑项目", self.edit)
        self.disable_button = button("停用项目", self.disable, danger=True)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.disable_button)
        group_layout.addLayout(toolbar)
        self.table = table(["编码", "名称", "分类", "状态", "排序", "说明"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 280)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 70)
        align_table_columns(self.table, right=(4,), center=(3,))
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        group_layout.addWidget(self.table, 1)
        footer = toolbar_layout()
        self.selection_state = label("未选择项目", "summary")
        footer.addWidget(self.selection_state, 1)
        footer.addWidget(label("双击项目可直接编辑", "muted"))
        group_layout.addLayout(footer)
        self.layout.addWidget(group, 1)
        self.rows = []
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.update_actions()

    @guarded
    def refresh(self, *_):
        self.table.clearSelection()
        self.rows = self.ctx.defects.list(self.search.text())
        enabled_count = sum(row["enabled"] for row in self.rows)
        self.count.setText(f"共 {len(self.rows)} 项 · 启用 {enabled_count} 项")
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
        self.selection_state.setText(
            f"已选择：{item['code']} · {item['name']}" if item else "未选择项目"
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
