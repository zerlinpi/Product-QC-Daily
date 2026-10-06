from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QSpinBox,
)

from app.ui.common import (
    align_table_columns,
    control_metrics,
    dialog_button_box,
    dialog_layout,
    form_grid,
    form_group,
    form_row,
    friendly_error,
    label,
    native_group,
    table,
)


class DemoDialog(QDialog):
    def __init__(self, ctx, parent):
        super().__init__(parent)
        self.setWindowTitle("生成演示数据")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(680, 700)
        self.setMinimumSize(620, 560)

        layout = dialog_layout(self)
        layout.addWidget(
            label(
                "演示记录与正式数据完全分开。默认生成当前完整年度；年度或跨月范围生成后会打开对应日期的质量分析，并可在报表中心选择“演示数据”导出。",
                "muted",
                True,
            )
        )

        range_group, range_form = form_group("生成范围")
        self.count = QSpinBox()
        self.count.setRange(1, 100_000)
        self.count.setValue(1000)
        self.count.setSingleStep(100)
        today = QDate.currentDate()
        self.start, self.end = (
            QDateEdit(QDate(today.year(), 1, 1)),
            QDateEdit(QDate(today.year(), 12, 31)),
        )
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        self.rework, self.defect = QDoubleSpinBox(), QDoubleSpinBox()
        for widget in (self.rework, self.defect):
            widget.setRange(0, 100)
            widget.setSuffix(" %")
            widget.setDecimals(1)
        self.rework.setValue(8)
        self.defect.setValue(2)
        control_metrics(self.count, self.start, self.end, self.rework, self.defect)
        self.pass_rate = label("合格率目标：92.0%", "status")
        self.rework.valueChanged.connect(
            lambda v: self.pass_rate.setText(f"合格率目标：{100 - v:.1f}%")
        )
        for title, widget in [
            ("生成数量", self.count),
            ("开始日期", self.start),
            ("结束日期", self.end),
            ("返工率目标", self.rework),
            ("不良率目标", self.defect),
        ]:
            form_row(range_form, title, widget)
        form_row(range_form, "判定参考", self.pass_rate)
        layout.addWidget(range_group)

        team_group, team_layout = native_group("参与组别")
        team_grid = form_grid()
        team_layout.addLayout(team_grid)
        self.teams = []
        for i, team in enumerate(ctx.settings.teams(True)):
            checkbox = QCheckBox(team["name"])
            checkbox.setChecked(True)
            control_metrics(checkbox)
            self.teams.append(checkbox)
            team_grid.addWidget(checkbox, i // 6, i % 6)
        layout.addWidget(team_group)

        defect_group, defect_layout = native_group("不良项目出现频率")
        defect_layout.addWidget(label("数值越大越常出现；0 表示演示数据中不生成该项目。", "muted", True))
        self.table = table(["不良项目", "相对频率"])
        self.table.setColumnWidth(0, 430)
        self.table.horizontalHeader().setStretchLastSection(True)
        align_table_columns(self.table, right=(1,))
        self.items = []
        defects = ctx.defects.list(enabled_only=True)
        self.table.setRowCount(len(defects))
        for row, item in enumerate(defects):
            name = label(item["name"])
            name.setToolTip(f"{item['code']} · {item['category']}")
            self.table.setCellWidget(row, 0, name)
            value = QSpinBox()
            value.setRange(0, 1000)
            value.setValue(4 if item["code"] in ("d", "e", "g") else 1)
            control_metrics(value)
            self.table.setCellWidget(row, 1, value)
            self.items.append((item["id"], value))
        defect_layout.addWidget(self.table, 1)
        layout.addWidget(defect_group, 1)

        buttons = dialog_button_box(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            default=QDialogButtonBox.StandardButton.Ok,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("生成并查看")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        try:
            start, end = self.start.date().toPython(), self.end.date().toPython()
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
            if not any(item.isChecked() for item in self.teams):
                raise ValueError("请至少选择一个参与组别")
            if not any(widget.value() > 0 for _, widget in self.items):
                raise ValueError("请至少为一个不良项目设置大于 0 的相对频率")
        except Exception as exc:
            friendly_error(self, exc)
            return
        super().accept()

    def options(self):
        return dict(
            count=self.count.value(),
            start=self.start.date().toPython(),
            end=self.end.date().toPython(),
            teams=[c.text() for c in self.teams if c.isChecked()],
            rework_rate=self.rework.value() / 100,
            defect_rate=self.defect.value() / 100,
            weights={key: widget.value() for key, widget in self.items},
        )
