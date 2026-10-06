from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QSpinBox,
)

from app.ui.common import dialog_button_box, dialog_layout, form_layout, friendly_error, label


class DefectDialog(QDialog):
    def __init__(self, ctx, parent, item=None):
        super().__init__(parent)
        self.ctx, self.item = ctx, item
        self.setWindowTitle("编辑不良项目" if item else "新增不良项目")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(FORM_DIALOG_MIN_WIDTH)
        layout = dialog_layout(self)
        layout.addWidget(label("编码和名称为必填项；排序数值越小，显示越靠前。", "muted", True))
        form = form_layout()
        self.fields = {}
        placeholders = {
            "code": "例如 A01",
            "name": "请输入不良项目名称",
            "category": "选填，例如外观、装配",
            "description": "选填，补充识别或判定说明",
        }
        for key, title in [
            ("code", "编码 *"),
            ("name", "名称 *"),
            ("category", "分类"),
            ("description", "说明"),
        ]:
            widget = QLineEdit(str((item or {}).get(key, "")))
            widget.setPlaceholderText(placeholders[key])
            self.fields[key] = widget
            control_metrics(widget)
            form.addRow(title, widget)
        self.enabled = QCheckBox("启用此项目")
        self.enabled.setChecked((item or {}).get("enabled", True))
        self.order = QSpinBox()
        self.order.setRange(0, 10000)
        self.order.setValue((item or {}).get("sort_order", 25))
        control_metrics(self.order)
        form.addRow("排序", self.order)
        form.addRow("状态", self.enabled)
        layout.addLayout(form)
        buttons = dialog_button_box(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            default=QDialogButtonBox.StandardButton.Save,
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.fields["code"].setFocus()

    def save(self):
        try:
            values = {key: widget.text() for key, widget in self.fields.items()}
            values.update(enabled=self.enabled.isChecked(), sort_order=self.order.value())
            self.ctx.defects.save(values, self.item["id"] if self.item else None)
            self.accept()
        except Exception as exc:
            friendly_error(self, exc)
