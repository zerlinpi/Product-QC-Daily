from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QSpinBox,
    QVBoxLayout,
)

from app.ui.common import label, table


class DemoDialog(QDialog):
    def __init__(self, ctx, parent):
        super().__init__(parent)
        self.setWindowTitle("生成演示数据")
        self.resize(650, 720)
        layout = QVBoxLayout(self)
        layout.addWidget(
            label(
                "模拟数据始终标记为 demo，与正式统计分开。比率是生成目标，实际样本有随机波动。",
                "muted",
                True,
            )
        )
        form = QFormLayout()
        self.count = QSpinBox()
        self.count.setRange(1, 100_000)
        self.count.setValue(1000)
        self.start, self.end = (
            QDateEdit(QDate.currentDate().addDays(-29)),
            QDateEdit(QDate.currentDate()),
        )
        for widget in (self.start, self.end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
        self.rework, self.defect = QDoubleSpinBox(), QDoubleSpinBox()
        for widget in (self.rework, self.defect):
            widget.setRange(0, 100)
            widget.setSuffix(" %")
        self.rework.setValue(8)
        self.defect.setValue(2)
        self.pass_rate = label("合格率目标：92%", "muted")
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
            form.addRow(title, widget)
        form.addRow("判定", self.pass_rate)
        layout.addLayout(form)
        group_grid = QGridLayout()
        self.teams = []
        for i, team in enumerate(ctx.settings.teams(True)):
            checkbox = QCheckBox(team["name"])
            checkbox.setChecked(True)
            self.teams.append(checkbox)
            group_grid.addWidget(checkbox, i // 8, i % 8)
        layout.addLayout(group_grid)
        layout.addWidget(label("不良项目相对权重（0 表示不生成该项）", "section"))
        self.table = table(["不良项目", "权重"])
        self.table.setColumnWidth(0, 400)
        self.items = []
        defects = ctx.defects.list(enabled_only=True)
        self.table.setRowCount(len(defects))
        for row, item in enumerate(defects):
            self.table.setCellWidget(row, 0, label(item["name"]))
            value = QSpinBox()
            value.setRange(0, 1000)
            value.setValue(4 if item["code"] in ("d", "e", "g") else 1)
            self.table.setCellWidget(row, 1, value)
            self.items.append((item["id"], value))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
