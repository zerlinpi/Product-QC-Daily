from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.common import label, table, toolbar_layout


class DefectSelector(QWidget):
    changed = Signal()

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._remarks = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        filters = toolbar_layout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索不良项目…")
        self.search.setClearButtonEnabled(True)
        self.category = QComboBox()
        self.category.setMinimumWidth(120)
        self.category.setAccessibleName("不良项目分类")
        filters.addWidget(self.search, 2)
        filters.addWidget(self.category, 1)
        layout.addLayout(filters)
        self.table = table(["选择", "不良项目", "件数"])
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 105)
        self.table.setMinimumHeight(280)
        layout.addWidget(self.table, 1)
        self.total = label("已选 0 项 · 已知件数合计 0", "muted", True)
        layout.addWidget(self.total)
        layout.addWidget(
            label(
                "件数不清楚时选择“未知”。同一件可有多个不良项目，逐项合计可能高于不良总件数。",
                "muted",
                True,
            )
        )
        self.search.textChanged.connect(self.filter_rows)
        self.category.currentTextChanged.connect(self.filter_rows)
        self.entries = []
        self.reload()

    def reload(self):
        previous_signal_state = self.blockSignals(True)
        values = self.values() if self.entries else []
        items = self.ctx.defects.list()
        category = self.category.currentText()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItems(["全部分类"] + sorted({d["category"] for d in items}))
        self.category.setCurrentIndex(max(0, self.category.findText(category)))
        self.category.blockSignals(False)
        self.entries = []
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            check = QCheckBox()
            check.setEnabled(item["enabled"])
            qty = QSpinBox()
            qty.setRange(0, 100_000_000)
            qty.setSpecialValueText("未知")
            qty.setValue(1)
            qty.setEnabled(False)
            self.table.setCellWidget(row, 0, check)
            text = QTableWidgetItem(item["name"] + ("（停用）" if not item["enabled"] else ""))
            text.setToolTip(f"{item['code']} · {item['category']}\n{item['description']}")
            self.table.setItem(row, 1, text)
            self.table.setCellWidget(row, 2, qty)
            self.entries.append((item, check, qty))
            check.toggled.connect(qty.setEnabled)
            check.toggled.connect(self.update_total)
            qty.valueChanged.connect(self.update_total)
        self.set_values(values)
        self.filter_rows()
        self.blockSignals(previous_signal_state)

    def values(self):
        return [
            {
                "defect_id": item["id"],
                "quantity": qty.value() or None,
                "remark": self._remarks.get(item["id"], ""),
            }
            for item, check, qty in self.entries
            if check.isChecked()
        ]

    def set_values(self, values):
        self._remarks = {d["defect_id"]: d.get("remark", "") for d in values}
        selected = {d["defect_id"]: d.get("quantity") for d in values}
        for item, check, qty in self.entries:
            check.setEnabled(item["enabled"] or item["id"] in selected)
            check.setChecked(item["id"] in selected)
            qty.setValue((selected[item["id"]] or 0) if item["id"] in selected else 1)
        self.update_total()

    def filter_rows(self, *_):
        for row, (item, _, _) in enumerate(self.entries):
            hidden = self.search.text().lower() not in (
                item["name"] + item["code"]
            ).lower() or self.category.currentText() not in ("全部分类", item["category"])
            self.table.setRowHidden(row, hidden)

    def update_total(self, *_):
        values = self.values()
        self.total.setText(
            f"已选 {len(values)} 项 · 已知件数合计 {sum(v['quantity'] or 0 for v in values)} · {sum(v['quantity'] is None for v in values)} 项未知"
        )
        self.changed.emit()
