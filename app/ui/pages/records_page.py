from datetime import date
from functools import partial
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLineEdit,
    QMenu,
    QWidget,
)

from app.core.labels import source_label
from app.core.schemas import RecordFilter
from app.ui.common import (
    WIDE_LAYOUT_BREAKPOINT,
    Page,
    align_table_columns,
    button,
    choice_input_dialog,
    confirm,
    control_metrics,
    form_grid,
    grid_place,
    guarded,
    label,
    native_group,
    populate,
    set_label_kind,
    table,
    text_input_dialog,
    toolbar_layout,
)
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
        self.filters_dirty = False
        self.result_summary = "暂无记录"
        filters, box = native_group("筛选条件")
        self.filters_grid = form_grid()
        self._filter_layout_mode = None
        self.range_enabled = QCheckBox("按日期筛选")
        control_metrics(self.range_enabled)
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
            widget.setClearButtonEnabled(True)
            widget.returnPressed.connect(self.search_records)
        control_metrics(
            self.start,
            self.end,
            self.team,
            self.judgment,
            self.source,
            self.defect,
            self.has_defects,
            self.search,
            self.work_order,
            self.inspector,
        )
        self.trash = QCheckBox("查看回收站")
        control_metrics(self.trash)

        def field(title, widget, accessible_name=None):
            container = QWidget()
            row = toolbar_layout(container)
            caption = label(title, "fieldLabel")
            caption.setBuddy(widget)
            row.addWidget(caption)
            row.addWidget(widget, 1)
            widget.setAccessibleName(accessible_name or title)
            return container

        self.start_field = field("从", self.start, "开始日期")
        self.end_field = field("至", self.end, "结束日期")
        self.team_field = field("组别", self.team, "组别")
        self.source_field = field("数据", self.source, "数据范围")
        self.search_field = field("搜索", self.search)
        self.work_order_field = field("工单", self.work_order, "加工单号")
        self.inspector_field = field("检验员", self.inspector)
        self.judgment_field = field("判定", self.judgment)
        self.defect_field = field("不良项目", self.defect)
        self.has_defects.setAccessibleName("不良情况")
        self.filter_actions_widget = QWidget()
        filter_actions = toolbar_layout(self.filter_actions_widget)
        filter_actions.addWidget(button("重置筛选", self.reset_filters))
        self.query_button = button("查询", self.search_records, primary=True)
        filter_actions.addWidget(self.query_button)
        self.filters_grid.addWidget(self.range_enabled, 0, 0)
        self.filters_grid.addWidget(self.start_field, 0, 1)
        self.filters_grid.addWidget(self.end_field, 0, 2)
        self.filters_grid.addWidget(self.team_field, 0, 3)
        self.filters_grid.addWidget(self.source_field, 0, 4)
        self.filters_grid.addWidget(self.search_field, 1, 0, 1, 2)
        self.filters_grid.addWidget(self.work_order_field, 1, 2)
        self.filters_grid.addWidget(self.inspector_field, 1, 3)
        self.filters_grid.addWidget(self.judgment_field, 1, 4)
        self.filters_grid.addWidget(self.defect_field, 2, 0, 1, 2)
        self.filters_grid.addWidget(self.has_defects, 2, 2)
        self.filters_grid.addWidget(self.trash, 2, 3)
        self.filters_grid.addWidget(self.filter_actions_widget, 2, 4)
        box.addLayout(self.filters_grid)
        self.layout.addWidget(filters)
        actions = toolbar_layout()
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
            if key != "export":
                actions.addWidget(control)
        actions.addStretch()
        self.selection_count = label("未选择记录", "summary")
        actions.addWidget(self.selection_count)
        actions.addWidget(self.action_buttons["export"])
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
        align_table_columns(self.table, right=(4, 5, 6), center=(2, 7, 9))
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit())
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.table.itemSelectionChanged.connect(self.update_selection_state)
        self.trash.toggled.connect(self.search_records)
        self.layout.addWidget(self.table, 1)
        footer = toolbar_layout()
        self.count = label("暂无记录", "summary")
        footer.addWidget(self.count, 1)
        self.previous_button = button("上一页", lambda: self.turn(-1))
        self.next_button = button("下一页", lambda: self.turn(1))
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        self.layout.addLayout(footer)
        for widget in (self.team, self.judgment, self.source, self.defect, self.has_defects):
            widget.currentIndexChanged.connect(self.update_filter_state)
        for widget in (self.search, self.work_order, self.inspector):
            widget.textChanged.connect(self.update_filter_state)
        self.start.dateChanged.connect(self.update_filter_state)
        self.end.dateChanged.connect(self.update_filter_state)
        self.update_selection_state()
        self._reflow_filters()

    def _reflow_filters(self):
        mode = "wide" if self.width() >= WIDE_LAYOUT_BREAKPOINT else "narrow"
        if mode == self._filter_layout_mode:
            return
        self._filter_layout_mode = mode
        if mode == "wide":
            grid_place(self.filters_grid, self.range_enabled, 0, 0, 1, 1)
            grid_place(self.filters_grid, self.start_field, 0, 1, 1, 1)
            grid_place(self.filters_grid, self.end_field, 0, 2, 1, 1)
            grid_place(self.filters_grid, self.team_field, 0, 3, 1, 1)
            grid_place(self.filters_grid, self.source_field, 0, 4, 1, 1)
            grid_place(self.filters_grid, self.search_field, 1, 0, 1, 2)
            grid_place(self.filters_grid, self.work_order_field, 1, 2, 1, 1)
            grid_place(self.filters_grid, self.inspector_field, 1, 3, 1, 1)
            grid_place(self.filters_grid, self.judgment_field, 1, 4, 1, 1)
            grid_place(self.filters_grid, self.defect_field, 2, 0, 1, 2)
            grid_place(self.filters_grid, self.has_defects, 2, 2, 1, 1)
            grid_place(self.filters_grid, self.trash, 2, 3, 1, 1)
            grid_place(self.filters_grid, self.filter_actions_widget, 2, 4, 1, 1)
            for col in range(5):
                self.filters_grid.setColumnStretch(col, 1)
        else:
            grid_place(self.filters_grid, self.range_enabled, 0, 0)
            grid_place(self.filters_grid, self.start_field, 0, 1)
            grid_place(self.filters_grid, self.end_field, 0, 2)
            grid_place(self.filters_grid, self.team_field, 1, 0)
            grid_place(self.filters_grid, self.source_field, 1, 1)
            grid_place(self.filters_grid, self.search_field, 1, 2)
            grid_place(self.filters_grid, self.work_order_field, 2, 0)
            grid_place(self.filters_grid, self.inspector_field, 2, 1)
            grid_place(self.filters_grid, self.judgment_field, 2, 2)
            grid_place(self.filters_grid, self.defect_field, 3, 0, 1, 2)
            grid_place(self.filters_grid, self.has_defects, 3, 2)
            grid_place(self.filters_grid, self.trash, 4, 0)
            grid_place(self.filters_grid, self.filter_actions_widget, 4, 2)
            for col in range(5):
                self.filters_grid.setColumnStretch(col, 1 if col < 3 else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "filters_grid"):
            self._reflow_filters()

    def date_range_valid(self):
        return (
            not self.range_enabled.isChecked()
            or self.start.date() <= self.end.date()
        )

    def filter_values_match_applied(self):
        if not self.date_range_valid():
            return False
        exclude = {"page", "page_size", "sort", "descending"}
        return self.filters().model_dump(exclude=exclude) == self.applied_filters.model_dump(
            exclude=exclude
        )

    def update_filter_state(self, *_):
        valid = self.date_range_valid()
        dirty = valid and not self.filter_values_match_applied()
        self.filters_dirty = not valid or dirty
        if hasattr(self, "query_button"):
            self.query_button.setEnabled(valid)
        if hasattr(self, "count"):
            if not valid:
                self.count.setText(
                    "日期范围无效：开始日期不能晚于结束日期 · 当前表格仍为上一次查询结果"
                )
                set_label_kind(self.count, "error")
            elif dirty:
                self.count.setText(
                    "筛选条件已更改 · 当前表格仍为上一次查询结果 · 点击“查询”应用"
                )
                set_label_kind(self.count, "warning")
            else:
                self.count.setText(self.result_summary)
                set_label_kind(self.count, "summary")
        if hasattr(self, "previous_button"):
            self.previous_button.setEnabled(not self.filters_dirty and self.page > 1)
            pages = max(1, (getattr(self, "total", 0) + 49) // 50)
            self.next_button.setEnabled(not self.filters_dirty and self.page < pages)
        if hasattr(self, "action_buttons"):
            self.update_selection_state()
        return valid

    def update_date_range_state(self, *_):
        return self.update_filter_state()

    def set_date_range_enabled(self, enabled):
        self.start.setEnabled(enabled)
        self.end.setEnabled(enabled)
        self.update_filter_state()

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
        if self.filters_dirty:
            export_tip = (
                f"筛选条件尚未应用；仅导出当前表格已选择的 {count} 条记录"
                if count
                else "筛选条件尚未应用；仍按当前表格的上一次查询结果导出全部分页"
            )
        else:
            export_tip = (
                f"仅导出已选择的 {count} 条记录"
                if count
                else "导出当前查询结果的全部记录，包含其他分页"
            )
        self.action_buttons["export"].setToolTip(export_tip)
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
        if not self.date_range_valid():
            self.update_filter_state()
            return
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
        self.result_summary = (
            f"共 {total:,} 条 · 第 {self.page} / {pages} 页 · 每页 50 条"
            + (" · 回收站" if self.trash.isChecked() else "")
            + (" · 可调整条件或重置筛选" if not total else "")
        )
        self.count.setText(self.result_summary)
        set_label_kind(self.count, "summary")
        self.total = total
        self.filters_dirty = False
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
        if self.filters_dirty:
            return
        self.page = max(1, min(self.page + delta, max(1, (getattr(self, "total", 0) + 49) // 50)))
        self.load_rows()

    def sort_by(self, column):
        if self.filters_dirty:
            self.window.notify("筛选条件尚未应用，请先点击“查询”再排序")
            return
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
        value, ok = choice_input_dialog(
            self,
            "批量修改组别",
            f"将修改所选 {len(ids)} 条记录。",
            "组别",
            [t["name"] for t in self.ctx.settings.teams(True)],
        )
        if ok:
            self.ctx.inspections.bulk_update(ids, team=value)
            self.load_rows()

    @guarded
    def change_inspector(self):
        ids = self.selected_ids()
        if not ids:
            return
        value, ok = text_input_dialog(
            self,
            "批量修改检验员",
            f"将修改所选 {len(ids)} 条记录。",
            "检验员",
        )
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
                self.window.export_completed,
            )

    def select_context_row(self, position):
        row = self.table.rowAt(position.y())
        selected_rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if row >= 0 and row not in selected_rows:
            self.table.clearSelection()
            self.table.selectRow(row)
            self.table.setCurrentCell(row, 0)

    def context_menu(self, position):
        self.select_context_row(position)
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
