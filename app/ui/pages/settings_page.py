from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.ui.common import Page, button, card, friendly_error, guarded, label, populate, table
from app.ui.dialogs.demo_dialog import DemoDialog
from app.ui.styles.theme import apply_theme


class SettingsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "系统设置", "管理工厂信息、组别与本地数据 · 升级程序不会覆盖用户数据"
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)
        frame, layout = card()
        layout.addWidget(label("基础设置", "section"))
        form = QFormLayout()
        form.setSpacing(12)
        self.fields = {}
        for key, title in [
            ("company", "公司名称"),
            ("factory", "工厂名称"),
            ("default_inspector", "默认检验员"),
            ("default_team", "默认组别"),
        ]:
            field = QLineEdit()
            self.fields[key] = field
            form.addRow(title, field)
        self.theme = QComboBox()
        self.theme.addItems(["浅色", "深色", "跟随系统"])
        form.addRow("界面主题", self.theme)
        for key, title in [
            ("template_path", "Excel 模板"),
            ("export_directory", "导出目录"),
            ("backup_directory", "备份目录"),
        ]:
            row = QHBoxLayout()
            field = QLineEdit()
            self.fields[key] = field
            row.addWidget(field, 1)
            row.addWidget(button("浏览", lambda _, k=key: self.choose_path(k)))
            form.addRow(title, row)
        self.auto_backup = QCheckBox("每天第一次启动自动备份")
        form.addRow("自动备份", self.auto_backup)
        self.retention = QSpinBox()
        self.retention.setRange(1, 3650)
        self.retention.setSuffix(" 天")
        form.addRow("自动备份保留", self.retention)
        layout.addLayout(form)
        layout.addWidget(
            label(
                "保留期限仅清理自动备份，手动备份及恢复前备份不会自动删除。ZIP 备份包含数据库、签名和校验信息。",
                "muted",
                True,
            )
        )
        layout.addWidget(button("保存设置", self.save, primary=True))
        body.addWidget(frame)
        frame, layout = card()
        toolbar = QHBoxLayout()
        toolbar.addWidget(label("组别管理", "section"), 1)
        toolbar.addWidget(button("新增组别", lambda: self.edit_team(False)))
        toolbar.addWidget(button("编辑 / 停用", lambda: self.edit_team(True)))
        layout.addLayout(toolbar)
        self.teams = table(["名称", "状态", "排序"])
        self.teams.setMinimumHeight(220)
        self.teams.cellDoubleClicked.connect(lambda *_: self.edit_team(True))
        layout.addWidget(self.teams)
        body.addWidget(frame)
        frame, layout = card()
        layout.addWidget(label("数据维护", "section"))
        self.location = label(str(ctx.paths.root), "muted", True)
        layout.addWidget(self.location)
        for titles in [
            [
                ("手动完整备份 / 导出数据库", self.backup),
                ("恢复备份", self.restore),
                ("数据库健康检查", self.health),
            ],
            [
                ("打开数据目录", self.open_folder),
                ("导入 Excel", lambda: self.window.navigate(5)),
                ("生成演示数据", self.demo),
                ("删除全部演示数据", self.clear_demo),
            ],
        ]:
            row = QHBoxLayout()
            for title, action in titles:
                row.addWidget(button(title, action, danger=title.startswith("删除")))
            layout.addLayout(row)
        body.addWidget(frame)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)

    @guarded
    def refresh(self):
        values = self.ctx.settings.all()
        for key, widget in self.fields.items():
            widget.setText(str(values.get(key, "")))
        self.theme.setCurrentIndex(["light", "dark", "system"].index(values["theme"]))
        self.auto_backup.setChecked(values["auto_backup"])
        self.retention.setValue(values["backup_retention_days"])
        self.team_rows = self.ctx.settings.teams()
        populate(
            self.teams,
            [
                [r["name"], "启用" if r["enabled"] else "停用", r["sort_order"]]
                for r in self.team_rows
            ],
        )

    @guarded
    def save(self):
        values = {key: widget.text().strip() for key, widget in self.fields.items()}
        if values["default_team"] not in {r["name"] for r in self.ctx.settings.teams(True)}:
            raise ValueError("默认组别必须是启用的组别")
        if values["template_path"] and not Path(values["template_path"]).is_file():
            raise ValueError("模板文件不存在")
        values.update(
            theme=["light", "dark", "system"][self.theme.currentIndex()],
            auto_backup=self.auto_backup.isChecked(),
            backup_retention_days=self.retention.value(),
        )
        self.ctx.settings.update(values)
        apply_theme(values["theme"])
        self.window.update_company()
        self.window.notify("设置已保存")

    def choose_path(self, key):
        if key == "template_path":
            path, _ = QFileDialog.getOpenFileName(self, "选择兼容模板", "", "Excel (*.xlsx)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self.fields[key].setText(path)

    def edit_team(self, existing):
        row = self.teams.currentRow()
        item = self.team_rows[row] if existing and 0 <= row < len(self.team_rows) else None
        if existing and item is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑组别" if item else "新增组别")
        layout, form = QVBoxLayout(dialog), QFormLayout()
        name = QLineEdit(item["name"] if item else "")
        enabled = QCheckBox("启用")
        enabled.setChecked(item["enabled"] if item else True)
        order = QSpinBox()
        order.setRange(0, 10000)
        order.setValue(item["sort_order"] if item else 9)
        for title, widget in [("名称", name), ("状态", enabled), ("排序", order)]:
            form.addRow(title, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)
        buttons.rejected.connect(dialog.reject)

        def save():
            try:
                self.ctx.settings.save_team(
                    name.text(), item["id"] if item else None, enabled.isChecked(), order.value()
                )
                dialog.accept()
            except Exception as exc:
                friendly_error(dialog, exc)

        buttons.accepted.connect(save)
        if dialog.exec():
            self.refresh()

    def backup(self):
        self.window.run_job(
            "备份数据库与签名",
            self.ctx.backup.backup,
            lambda path: QMessageBox.information(self, "备份完成", f"完整备份已保存：\n{path}"),
        )

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份", str(self.ctx.paths.backups), "备份 (*.zip *.db)"
        )
        if (
            path
            and QMessageBox.warning(
                self,
                "确认恢复",
                "恢复会用备份内容替换当前数据库。软件将先备份当前数据库。确定继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.window.run_job(
                "校验并恢复备份", lambda: self.ctx.backup.restore(Path(path)), self.restored
            )

    def restored(self, before):
        self.window.pages[1].reset()
        self.window.pages[1].refresh()
        self.refresh()
        apply_theme(self.ctx.settings.get("theme"))
        self.window.update_company()
        QMessageBox.information(self, "恢复完成", f"数据库已恢复。恢复前备份：\n{before}")

    def health(self):
        self.window.run_job(
            "检查数据库",
            self.ctx.db.health_check,
            lambda _: QMessageBox.information(self, "检查完成", "数据库完整性与外键检查通过。"),
        )

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ctx.paths.root)))

    def demo(self):
        dialog = DemoDialog(self.ctx, self)
        if dialog.exec():
            options = dialog.options()
            self.window.run_job(
                "生成演示数据",
                lambda: self.ctx.demo.generate(**options),
                lambda count: self.window.notify(
                    f"已生成 {count} 条演示记录，请在仪表盘或记录页切换至演示数据"
                ),
            )

    def clear_demo(self):
        if (
            QMessageBox.warning(
                self,
                "清理演示数据",
                "永久删除所有演示数据记录（包括回收站）。正式记录不受影响。确定继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.window.run_job(
                "清理演示数据",
                self.ctx.demo.clear,
                lambda count: self.window.notify(f"已清理 {count} 条演示记录"),
            )
