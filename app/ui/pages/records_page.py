from datetime import date
from functools import partial
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
)

from app.core.labels import source_label
from app.core.schemas import RecordFilter
from app.ui.common import Page, button, card, guarded, label, populate, table


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
            ctx, window, "检验记录", "查找、编辑与导出历史检验记录 · 删除的记录可在回收站恢复"
        )
        self.page, self.sort, self.descending, self.rows = 1, "inspection_date", True, []
        filters, box = card()
        grid = QGridLayout()
        self.range_enabled = QCheckBox("日期范围")
        self.start, self.end = (
            QDateEdit(QDate.currentDate().addMonths(-1)),
            QDateEdit(QDate.currentDate()),
        )
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
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
        self.trash = QCheckBox("回收站")
        grid.addWidget(self.range_enabled, 0, 0)
        grid.addWidget(self.start, 0, 1)
        grid.addWidget(self.end, 0, 2)
        grid.addWidget(self.team, 0, 3)
        grid.addWidget(self.judgment, 0, 4)
        grid.addWidget(self.search, 1, 0, 1, 2)
        grid.addWidget(self.work_order, 1, 2)
        grid.addWidget(self.inspector, 1, 3)
        grid.addWidget(self.source, 1, 4)
        grid.addWidget(self.defect, 2, 0, 1, 2)
        grid.addWidget(self.has_defects, 2, 2)
        grid.addWidget(self.trash, 2, 3)
        grid.addWidget(button("查询", self.search_records, primary=True), 2, 4)
        box.addLayout(grid)
        self.layout.addWidget(filters)
        actions = QHBoxLayout()
        for text, callback in [
            ("查看 / 编辑", self.edit),
            ("复制选中", self.copy),
            ("批量改组别", self.change_team),
            ("批量改检验员", self.change_inspector),
            ("删除", self.delete),
            ("恢复", self.restore),
            ("导出", self.export),
        ]:
            actions.addWidget(button(text, callback, danger=text == "删除"))
        actions.addStretch()
        self.layout.addLayout(actions)
        self.table = table(
            [
                "填写 ID",
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
        self.layout.addWidget(self.table, 1)
        footer = QHBoxLayout()
        self.count = label("暂无记录", "muted")
        footer.addWidget(self.count, 1)
        footer.addWidget(button("上一页", lambda: self.turn(-1)))
        footer.addWidget(button("下一页", lambda: self.turn(1)))
        self.layout.addLayout(footer)

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
        self.rows, total = self.ctx.inspections.query(self.filters())
        if not self.rows and total and self.page > 1:
            self.page = max(1, (total + 49) // 50)
            self.rows, total = self.ctx.inspections.query(self.filters())
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
        self.count.setText(
            f"共 {total:,} 条 · 第 {self.page} / {max(1, (total + 49) // 50)} 页 · 每页 50 条"
            + (" · 回收站" if self.trash.isChecked() else "")
        )
        self.total = total

    def selected_ids(self):
        return [
            self.rows[index.row()]["id"] for index in self.table.selectionModel().selectedRows()
        ]

    def search_records(self):
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
        if len(ids) == 1 and not self.trash.isChecked():
            self.window.open_record(ids[0])
        else:
            self.window.notify("请选择一条正式列表记录；回收站记录请先恢复")

    @guarded
    def copy(self):
        ids = self.selected_ids()
        if len(ids) == 1:
            self.window.open_record(ids[0], copy_record=True)

    @guarded
    def delete(self):
        ids = self.selected_ids()
        if (
            ids
            and QMessageBox.question(
                self,
                "删除记录",
                f"将 {len(ids)} 条记录移至回收站？可随时恢复。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.ctx.inspections.delete(ids)
            self.load_rows()

    @guarded
    def restore(self):
        ids = self.selected_ids()
        if ids and self.trash.isChecked():
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
        filters = self.filters()
        ids = self.selected_ids()
        if ids:
            filters = filters.model_copy(update={"ids": ids})
        path, selected_format = QFileDialog.getSaveFileName(
            self,
            "导出选中或全部筛选记录",
            str(self.ctx.paths.exports / f"检验记录_{date.today()}.xlsx"),
            "原表格式 (*.xlsx);;标准报表 (*.xlsx)",
        )
        if path:
            self.window.run_job(
                "导出检验记录",
                partial(
                    self.ctx.excel.export,
                    Path(path),
                    filters,
                    legacy=not selected_format.startswith("标准报表"),
                ),
                lambda result: self.window.notify(f"已导出：{result}"),
            )

    def context_menu(self, position):
        menu = QMenu(self)
        for title, callback in [
            ("查看 / 编辑", self.edit),
            ("复制", self.copy),
            ("删除", self.delete),
            ("恢复", self.restore),
            ("导出选中", self.export),
        ]:
            menu.addAction(title, callback)
        menu.exec(self.table.viewport().mapToGlobal(position))
