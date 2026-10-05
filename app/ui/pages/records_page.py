from datetime import date
from functools import partial
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QWidget,
)

from app.core.labels import source_label
from app.core.schemas import RecordFilter
from app.ui.common import Page, button, card, confirm, guarded, label, populate, table
from app.ui.dialogs import file_dialogs


class RecordsPage(Page):
    columns = [
        "inspection_no",
        "inspection_date",
        "team",
        "work_order",
        "inspection_quantity",
        "sampling_quantity",
        "defect_quantity",
        "judgment",
        "inspector",
        "source",
    ]

    def __init__(self, ctx, window):
        super().__init__(
            ctx,
            window,
            "检验记录",
            "设置条件后点击“查询”；可编辑记录、导出列表，或在回收站恢复记录",
        )
        self.page, self.sort, self.descending, self.rows = 1, "inspection_date", True, []
        self.applied_filters = RecordFilter()
        filters, box = card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.range_enabled = QCheckBox("按日期筛选")
        self.start, self.end = (
            QDateEdit(QDate.currentDate().addMonths(-1)),
            QDateEdit(QDate.currentDate()),
        )
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setEnabled(False)
        self.range_enabled.toggled.connect(self.set_date_range_enabled)
        self.team, self.judgment, self.source, self.defect, self.has_defects = [
            QComboBox() for _ in range(5)
        ]
        self.judgment.addItems(["全部判定", "合格", "返工"])
        self.source.addItems(["正式数据", "演示数据", "全部数据"])
        self.has_defects.addItems(["全部不良情况", "存在不良", "无不良"])
        self.search, self.work_order, self.inspector = QLineEdit(), QLineEdit(), QLineEdit()
        for widget, placeholder in [
            (self.search, "编号、工单、备注搜索"),
            (self.work_order, "加工单号"),
            (self.inspector, "检验员"),
        ]:
            widget.setPlaceholderText(placeholder)
            widget.returnPressed.connect(self.search_records)
        self.trash = QCheckBox("查看回收站")

        def field(title, widget, accessible_name=None):
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            caption = label(title, "fieldLabel")
            caption.setBuddy(widget)
            row.addWidget(caption)
            row.addWidget(widget, 1)
            widget.setAccessibleName(accessible_name or title)
            return container

        grid.addWidget(self.range_enabled, 0, 0)
        for col, title, widget, name in [
            (1, "从", self.start, "开始日期"),
            (2, "至", self.end, "结束日期"),
            (3, "组别", self.team, "组别"),
            (4, "数据", self.source, "数据范围"),
        ]:
            grid.addWidget(field(title, widget, name), 0, col)
        grid.addWidget(field("搜索", self.search), 1, 0, 1, 2)
        grid.addWidget(field("工单", self.work_order, "加工单号"), 1, 2)
        grid.addWidget(field("检验员", self.inspector), 1, 3)
        grid.addWidget(field("判定", self.judgment), 1, 4)
        grid.addWidget(field("不良项目", self.defect), 2, 0, 1, 2)
        grid.addWidget(self.has_defects, 2, 2)
        self.has_defects.setAccessibleName("不良情况")
        grid.addWidget(self.trash, 2, 3)
        filter_actions = QHBoxLayout()
        filter_actions.addWidget(button("重置筛选", self.reset_filters))
        filter_actions.addWidget(button("查询", self.search_records, primary=True))
        grid.addLayout(filter_actions, 2, 4)
        box.addLayout(grid)
        self.layout.addWidget(filters)
        actions = QHBoxLayout()
        self.action_buttons = {}
        for key, text, callback in [
            ("edit", "编辑记录", self.edit),
            ("copy", "复制记录", self.copy),
            ("team", "修改组别", self.change_team),
            ("inspector", "修改检验员", self.change_inspector),
            ("delete", "移入回收站", self.delete),
            ("restore", "恢复记录", self.restore),
            ("export", "导出列表", self.export),
        ]:
            control = button(text, callback, primary=key == "export", danger=key == "delete")
            self.action_buttons[key] = control
            actions.addWidget(control)
        actions.addStretch()
        self.selection_count = label("未选择记录", "muted")
        actions.addWidget(self.selection_count)
        self.layout.addLayout(actions)
        self.table = table(
            [
                "记录编号",
                "日期 / 时间",
                "组别",
                "加工单号",
                "检验数",
                "抽检数",
                "不良数",
                "判定",
                "检验员",
                "来源",
            ]
        )
        for col, width in enumerate([215, 165, 75, 200, 85, 85, 85, 90, 120, 85]):
            self.table.setColumnWidth(col, width)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.table.itemSelectionChanged.connect(self.update_selection_state)
        self.trash.toggled.connect(self.search_records)
        self.layout.addWidget(self.table, 1)
        footer = QHBoxLayout()
        self.count = label("暂无记录", "muted")
        footer.addWidget(self.count, 1)
        self.previous_button = button("上一页", lambda: self.turn(-1))
        self.next_button = button("下一页", lambda: self.turn(1))
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        self.layout.addLayout(footer)
        self.update_selection_state()

    def set_date_range_enabled(self, enabled):
        self.start.setEnabled(enabled)
        self.end.setEnabled(enabled)

    def reset_filters(self):
        self.range_enabled.setChecked(False)
        self.start.setDate(QDate.currentDate().addMonths(-1))
        self.end.setDate(QDate.currentDate())
        for widget in (self.team, self.judgment, self.source, self.defect, self.has_defects):
            if widget.count():
                widget.setCurrentIndex(0)
        self.search.clear()
        self.work_order.clear()
        self.inspector.clear()
        self.trash.setChecked(False)
        self.table.clearSelection()
        self.page = 1
        self.load_rows()

    def update_selection_state(self):
        ids = self.selected_ids() if hasattr(self, "table") else []
        count = len(ids)
        trash = self.applied_filters.deleted
        self.selection_count.setText(f"已选择 {count} 条" if count else "未选择记录")
        self.action_buttons["edit"].setEnabled(count == 1 and not trash)
        self.action_buttons["copy"].setEnabled(count == 1 and not trash)
        self.action_buttons["team"].setEnabled(count > 0 and not trash)
        self.action_buttons["inspector"].setEnabled(count > 0 and not trash)
        self.action_buttons["delete"].setEnabled(count > 0 and not trash)
        self.action_buttons["restore"].setEnabled(count > 0 and trash)
        self.action_buttons["restore"].setVisible(trash)
        for key in ("edit", "copy", "team", "inspector", "delete"):
            self.action_buttons[key].setVisible(not trash)
        self.action_buttons["export"].setEnabled(bool(self.rows))
        self.action_buttons["export"].setText(f"导出已选 {count} 条" if count else "导出列表")
        self.action_buttons["export"].setToolTip(
            f"仅导出已选择的 {count} 条记录"
            if count
            else "导出当前查询结果的全部记录，包含其他分页"
        )
        for key in ("team", "inspector"):
            self.action_buttons[key].setToolTip("可选中多条记录后一起修改")

    def filters(self):
        return RecordFilter(
            start=self.start.date().toPython() if self.range_enabled.isChecked() else None,
            end=self.end.date().toPython() if self.range_enabled.isChecked() else None,
            team=self.team.currentData() or "",
            judgment=self.judgment.currentText() if self.judgment.currentIndex() else "",
            source=["production", "demo", "all"][self.source.currentIndex()],
            deleted=self.trash.isChecked(),
            search=self.search.text(),
            work_order=self.work_order.text(),
            inspector=self.inspector.text(),
            defect_id=self.defect.currentData(),
            has_defects=[None, True, False][self.has_defects.currentIndex()],
            page=self.page,
            sort=self.sort,
            descending=self.descending,
        )

    @guarded
    def refresh(self):
        selected_team, selected_defect = self.team.currentData(), self.defect.currentData()
        self.team.clear()
        self.team.addItem("全部组别", "")
        for value in self.ctx.settings.teams():
            self.team.addItem(value["name"], value["name"])
        self.team.setCurrentIndex(max(0, self.team.findData(selected_team)))
        self.defect.clear()
        self.defect.addItem("全部不良项目", None)
        for value in self.ctx.defects.list():
            self.defect.addItem(value["name"], value["id"])
        self.defect.setCurrentIndex(max(0, self.defect.findData(selected_defect)))
        self.load_rows()

    @guarded
    def load_rows(self):
        filters = self.filters()
        rows, total = self.ctx.inspections.query(filters)
        if not rows and total and self.page > 1:
            self.page = max(1, (total + 49) // 50)
            filters = self.filters()
            rows, total = self.ctx.inspections.query(filters)
        self.table.clearSelection()
        self.rows, self.applied_filters = rows, filters
        populate(
            self.table,
            [
                [
                    source_label(row[key])
                    if key == "source"
                    else row[key]
                    if key != "inspection_date"
                    else f"{row[key]} {row['inspection_time'][:5]}"
                    for key in self.columns
                ]
                for row in self.rows
            ],
        )
        pages = max(1, (total + 49) // 50)
        self.count.setText(
            f"共 {total:,} 条 · 第 {self.page} / {pages} 页 · 每页 50 条"
            + (" · 回收站" if self.trash.isChecked() else "")
            + (" · 可调整条件或重置筛选" if not total else "")
        )
        self.total = total
        self.previous_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < pages)
        self.update_selection_state()

    def selected_ids(self):
        return [
            self.rows[index.row()]["id"] for index in self.table.selectionModel().selectedRows()
        ]

    def search_records(self, *_):
        self.page = 1
        self.load_rows()

    def turn(self, delta):
        self.page = max(1, min(self.page + delta, max(1, (getattr(self, "total", 0) + 49) // 50)))
        self.load_rows()

    def sort_by(self, column):
        self.descending = not self.descending if self.sort == self.columns[column] else True
        self.sort = self.columns[column]
        self.table.horizontalHeader().setSortIndicator(
            column, Qt.SortOrder.DescendingOrder if self.descending else Qt.SortOrder.AscendingOrder
        )
        self.load_rows()

    @guarded
    def edit(self):
        ids = self.selected_ids()
        if len(ids) == 1 and not self.applied_filters.deleted:
            self.window.open_record(ids[0])
        else:
            self.window.notify("请选择一条记录再编辑；回收站中的记录请先恢复")

    @guarded
    def copy(self):
        ids = self.selected_ids()
        if len(ids) == 1 and not self.applied_filters.deleted:
            self.window.open_record(ids[0], copy_record=True)

    @guarded
    def delete(self):
        ids = self.selected_ids()
        if (
            ids
            and not self.applied_filters.deleted
            and confirm(
                self,
                "移入回收站",
                f"将 {len(ids)} 条记录移至回收站？可随时恢复。",
                action="移入回收站",
                danger=True,
            )
        ):
            self.ctx.inspections.delete(ids)
            self.load_rows()

    @guarded
    def restore(self):
        ids = self.selected_ids()
        if ids and self.applied_filters.deleted:
            self.ctx.inspections.restore(ids)
            self.load_rows()

    @guarded
    def change_team(self):
        ids = self.selected_ids()
        if not ids:
            return
        value, ok = QInputDialog.getItem(
            self,
            "批量修改",
            f"将 {len(ids)} 条记录的组别设为",
            [t["name"] for t in self.ctx.settings.teams(True)],
            editable=False,
        )
        if ok:
            self.ctx.inspections.bulk_update(ids, team=value)
            self.load_rows()

    @guarded
    def change_inspector(self):
        ids = self.selected_ids()
        if not ids:
            return
        value, ok = QInputDialog.getText(self, "批量修改", f"将 {len(ids)} 条记录的检验员设为")
        if ok:
            self.ctx.inspections.bulk_update(ids, inspector=value)
            self.load_rows()

    @guarded
    def export(self):
        filters = self.applied_filters.model_copy()
        ids = self.selected_ids()
        if ids:
            filters = filters.model_copy(update={"ids": ids})
        directory = Path(
            self.ctx.settings.get("export_directory") or self.ctx.paths.exports
        ).expanduser()
        path, selected_format = file_dialogs.save_excel(
            self,
            f"导出已选 {len(ids)} 条记录" if ids else f"导出列表中的全部 {self.total} 条记录",
            str(directory / f"检验记录_{date.today()}.xlsx"),
            "原表格式 (*.xlsx);;明细报表 (*.xlsx)",
        )
        if path:
            self.window.run_job(
                "导出检验记录",
                partial(
                    self.ctx.excel.export,
                    Path(path),
                    filters,
                    legacy=not selected_format.startswith("明细报表"),
                ),
                lambda result: self.window.notify(f"已导出：{result}"),
            )

    def context_menu(self, position):
        menu = QMenu(self)
        for key, callback in [
            ("edit", self.edit),
            ("copy", self.copy),
            ("delete", self.delete),
            ("restore", self.restore),
            ("export", self.export),
        ]:
            control = self.action_buttons[key]
            if not control.isHidden():
                action = menu.addAction(control.text(), callback)
                action.setEnabled(control.isEnabled())
        menu.exec(self.table.viewport().mapToGlobal(position))
