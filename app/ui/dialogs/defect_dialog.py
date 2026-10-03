from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.ui.common import friendly_error


class DefectDialog(QDialog):
    def __init__(self, ctx, parent, item=None):
        super().__init__(parent)
        self.ctx, self.item = ctx, item
        self.setWindowTitle("编辑不良项目" if item else "新增不良项目")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.fields = {}
        for key, title in [
            ("code", "编码"),
            ("name", "名称"),
            ("category", "分类"),
            ("description", "说明"),
        ]:
            widget = QLineEdit(str((item or {}).get(key, "")))
            self.fields[key] = widget
            form.addRow(title, widget)
        self.enabled = QCheckBox("启用")
        self.enabled.setChecked((item or {}).get("enabled", True))
        self.order = QSpinBox()
        self.order.setRange(0, 10000)
        self.order.setValue((item or {}).get("sort_order", 25))
        form.addRow("排序", self.order)
        form.addRow("状态", self.enabled)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        try:
            values = {key: widget.text() for key, widget in self.fields.items()}
            values.update(enabled=self.enabled.isChecked(), sort_order=self.order.value())
            self.ctx.defects.save(values, self.item["id"] if self.item else None)
            self.accept()
        except Exception as exc:
            friendly_error(self, exc)
