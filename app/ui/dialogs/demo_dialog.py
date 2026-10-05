from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
)

from app.ui.common import label, table


class DemoDialog(QDialog):
    def __init__(self, ctx, parent):
        super().__init__(parent)
        self.setWindowTitle("生成演示数据")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(680, 700)
        self.setMinimumSize(620, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(
            label(
                "演示记录与正式数据完全分开。生成完成后将自动打开质量总览并切换到“演示数据”。",
                "muted",
                True,
            )
        )

        range_group = QGroupBox("生成范围")
        range_form = QFormLayout(range_group)
        range_form.setHorizontalSpacing(18)
        range_form.setVerticalSpacing(8)
        self.count = QSpinBox()
        self.count.setRange(1, 100_000)
        self.count.setValue(1000)
        self.count.setSingleStep(100)
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
            widget.setDecimals(1)
        self.rework.setValue(8)
        self.defect.setValue(2)
        self.pass_rate = label("合格率目标：92.0%", "muted")
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
            range_form.addRow(title, widget)
        range_form.addRow("判定参考", self.pass_rate)
        layout.addWidget(range_group)

        team_group = QGroupBox("参与组别")
        team_grid = QGridLayout(team_group)
        team_grid.setHorizontalSpacing(18)
        team_grid.setVerticalSpacing(6)
        self.teams = []
        for i, team in enumerate(ctx.settings.teams(True)):
            checkbox = QCheckBox(team["name"])
            checkbox.setChecked(True)
            self.teams.append(checkbox)
            team_grid.addWidget(checkbox, i // 6, i % 6)
        layout.addWidget(team_group)

        defect_group = QGroupBox("不良项目出现频率")
        defect_layout = QVBoxLayout(defect_group)
        defect_layout.setContentsMargins(10, 12, 10, 10)
        defect_layout.setSpacing(8)
        defect_layout.addWidget(label("数值越大越常出现；0 表示演示数据中不生成该项目。", "muted", True))
        self.table = table(["不良项目", "相对频率"])
        self.table.setColumnWidth(0, 430)
        self.table.horizontalHeader().setStretchLastSection(True)
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
            self.table.setCellWidget(row, 1, value)
            self.items.append((item["id"], value))
        defect_layout.addWidget(self.table, 1)
        layout.addWidget(defect_group, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("生成并查看")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
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
