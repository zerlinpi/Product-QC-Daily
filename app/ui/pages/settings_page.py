from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QLineEdit,
    QSpinBox,
    QStyle,
    QWidget,
)

from app.ui.common import (
    FORM_DIALOG_MIN_WIDTH,
    Page,
    align_table_columns,
    button,
    confirm,
    control_metrics,
    dialog_button_box,
    dialog_layout,
    form_grid,
    form_layout,
    form_row,
    friendly_error,
    guarded,
    label,
    native_group,
    page_scroll,
    populate,
    show_information,
    stack_layout,
    table,
    table_minimum_rows,
    toolbar_layout,
)
from app.ui.dialogs.demo_dialog import DemoDialog


class SettingsPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "系统设置", "管理工厂信息、组别与本地数据 · 升级程序不会覆盖用户数据"
        )
        scroll = page_scroll()
        content = QWidget()
        body = stack_layout(content)
        frame, layout = native_group("基础设置")
        form = form_layout()
        self.fields = {}
        for key, title in [
            ("company", "公司名称"),
            ("factory", "工厂名称"),
            ("default_inspector", "默认检验员"),
            ("default_team", "默认组别"),
        ]:
            field = QComboBox() if key == "default_team" else QLineEdit()
            if isinstance(field, QComboBox):
                field.setPlaceholderText("请选择组别")
            else:
                field.setPlaceholderText(
                    "录入时自动填写，可再修改" if key == "default_inspector" else "选填"
                )
            self.fields[key] = field
            control_metrics(field)
            form_row(form, title, field)
        self.theme = QComboBox()
        self.theme.addItems(["浅色", "深色", "跟随系统"])
        control_metrics(self.theme)
        form_row(form, "界面主题", self.theme)
        for key, title in [
            ("template_path", "原表模板"),
            ("export_directory", "导出目录"),
            ("backup_directory", "备份目录"),
        ]:
            row = toolbar_layout()
            field = QLineEdit()
            field.setPlaceholderText(
                "留空使用内置原表模板" if key == "template_path" else "留空使用默认文件夹"
            )
            self.fields[key] = field
            control_metrics(field)
            row.addWidget(field, 1)
            browse = button(
                "选择文件" if key == "template_path" else "选择文件夹",
                lambda _, k=key: self.choose_path(k),
                icon=QStyle.StandardPixmap.SP_DialogOpenButton,
            )
            row.addWidget(browse)
            form_row(form, title, row, buddy=field)
        self.auto_backup = QCheckBox("每天第一次启动自动备份")
        control_metrics(self.auto_backup)
        form_row(form, "自动备份", self.auto_backup)
        self.retention = QSpinBox()
        self.retention.setRange(1, 3650)
        self.retention.setSuffix(" 天")
        control_metrics(self.retention)
        form_row(form, "自动备份保留", self.retention)
        layout.addLayout(form)
        layout.addWidget(
            label(
                "到期只清理自动备份。手动备份和恢复前备份会保留；完整备份同时保存检验记录、签名与设置。",
                "muted",
                True,
            )
        )
        save_row = toolbar_layout()
        save_row.addStretch()
        self.save_button = button(
            "保存设置",
            self.save,
            primary=True,
            icon=QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        save_row.addWidget(self.save_button)
        layout.addLayout(save_row)
        body.addWidget(frame)
        frame, layout = native_group("组别管理")
        toolbar = toolbar_layout()
        self.team_count = label("", "summary")
        toolbar.addWidget(self.team_count)
        toolbar.addStretch()
        toolbar.addWidget(button("新增组别", lambda: self.edit_team(False)))
        self.edit_team_button = button("编辑所选组别", lambda: self.edit_team(True))
        self.edit_team_button.setEnabled(False)
        toolbar.addWidget(self.edit_team_button)
        layout.addLayout(toolbar)
        self.teams = table(["名称", "状态", "排序"])
        self.teams.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.teams.itemSelectionChanged.connect(
            lambda: self.edit_team_button.setEnabled(bool(self.teams.selectedItems()))
        )
        table_minimum_rows(self.teams, 7)
        self.teams.horizontalHeader().setStretchLastSection(False)
        self.teams.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.teams.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.teams.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        align_table_columns(self.teams, right=(2,), center=(1,))
        self.teams.cellDoubleClicked.connect(lambda *_: self.edit_team(True))
        layout.addWidget(self.teams)
        body.addWidget(frame)
        frame, layout = native_group("数据维护")
        self.location = label("本地数据位置：" + str(ctx.paths.root), "muted", True)
        self.location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.location.setToolTip(str(ctx.paths.root))
        layout.addWidget(self.location)
        maintenance = form_grid()

        backup_actions = toolbar_layout()
        backup_button = button(
            "立即备份全部数据",
            self.backup,
            icon=QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        restore_button = button(
            "恢复备份",
            self.restore,
            icon=QStyle.StandardPixmap.SP_DialogOpenButton,
        )
        backup_actions.addWidget(backup_button)
        backup_actions.addWidget(restore_button)
        backup_actions.addStretch()
        maintenance.addWidget(label("备份与恢复", "fieldLabel"), 0, 0)
        maintenance.addLayout(backup_actions, 0, 1)

        local_actions = toolbar_layout()
        local_actions.addWidget(button("检查数据是否正常", self.health))
        folder_button = button(
            "打开数据文件夹",
            self.open_folder,
            icon=QStyle.StandardPixmap.SP_DirOpenIcon,
        )
        local_actions.addWidget(folder_button)
        local_actions.addWidget(button("前往报表导入", lambda: self.window.navigate(5)))
        local_actions.addStretch()
        maintenance.addWidget(label("本地数据", "fieldLabel"), 1, 0)
        maintenance.addLayout(local_actions, 1, 1)

        demo_actions = toolbar_layout()
        demo_actions.addWidget(button("生成演示数据", self.demo))
        demo_actions.addWidget(button("删除全部演示数据", self.clear_demo, danger=True))
        demo_actions.addStretch()
        maintenance.addWidget(label("演示数据", "fieldLabel"), 2, 0)
        maintenance.addLayout(demo_actions, 2, 1)
        maintenance.setColumnStretch(1, 1)
        layout.addLayout(maintenance)
        body.addWidget(frame)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)

    @guarded
    def refresh(self):
        values = self.ctx.settings.all()
        for key, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                widget.clear()
                widget.addItems([r["name"] for r in self.ctx.settings.teams(True)])
                widget.setCurrentIndex(widget.findText(str(values.get(key, ""))))
            else:
                widget.setText(str(values.get(key, "")))
        self.theme.setCurrentIndex(["light", "dark", "system"].index(values["theme"]))
        self.auto_backup.setChecked(values["auto_backup"])
        self.retention.setValue(values["backup_retention_days"])
        self.team_rows = self.ctx.settings.teams()
        enabled_count = sum(row["enabled"] for row in self.team_rows)
        self.team_count.setText(f"共 {len(self.team_rows)} 个组别 · 启用 {enabled_count} 个")
        populate(
            self.teams,
            [
                [r["name"], "启用" if r["enabled"] else "停用", r["sort_order"]]
                for r in self.team_rows
            ],
        )

    @guarded
    def save(self):
        values = {
            key: (widget.currentText() if isinstance(widget, QComboBox) else widget.text()).strip()
            for key, widget in self.fields.items()
        }
        if values["default_team"] not in {r["name"] for r in self.ctx.settings.teams(True)}:
            raise ValueError("默认组别必须是启用的组别")
        if values["template_path"]:
            template = Path(values["template_path"]).expanduser()
            if template.suffix.lower() != ".xlsx" or not template.is_file():
                raise ValueError("原表模板必须是存在的 .xlsx 文件")
            values["template_path"] = str(template.resolve())
        for key, title in (
            ("export_directory", "导出目录"),
            ("backup_directory", "备份目录"),
        ):
            if not values[key]:
                continue
            directory = Path(values[key]).expanduser()
            if directory.exists() and not directory.is_dir():
                raise ValueError(f"{title}必须是文件夹，当前路径指向文件")
            directory.mkdir(parents=True, exist_ok=True)
            values[key] = str(directory.resolve())
        values.update(
            theme=["light", "dark", "system"][self.theme.currentIndex()],
            auto_backup=self.auto_backup.isChecked(),
            backup_retention_days=self.retention.value(),
        )
        self.ctx.settings.update(values)
        self.window.refresh_theme()
        self.window.update_company()
        self.window.notify("设置已保存")

    def choose_path(self, key):
        if key == "template_path":
            path, _ = QFileDialog.getOpenFileName(self, "选择原表模板", "", "电子表格 (*.xlsx)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self.fields[key].setText(path)

    def edit_team(self, existing):
        row = self.teams.currentRow()
        item = self.team_rows[row] if existing and 0 <= row < len(self.team_rows) else None
        if existing and item is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑组别" if item else "新增组别")
        dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        dialog.setMinimumWidth(FORM_DIALOG_MIN_WIDTH)
        layout, form = dialog_layout(dialog), form_layout()
        layout.addWidget(
            label("名称为必填项；停用组别后不会影响已有检验记录。", "muted", True)
        )
        name = QLineEdit(item["name"] if item else "")
        name.setPlaceholderText("请输入组别名称")
        enabled = QCheckBox("启用此组别")
        enabled.setChecked(item["enabled"] if item else True)
        control_metrics(enabled)
        order = QSpinBox()
        order.setRange(0, 10000)
        order.setValue(item["sort_order"] if item else 9)
        control_metrics(name, order)
        for title, widget in [("名称", name), ("状态", enabled), ("排序", order)]:
            form_row(form, title, widget)
        layout.addLayout(form)
        buttons = dialog_button_box(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            default=QDialogButtonBox.StandardButton.Save,
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
            lambda path: show_information(self, "备份完成", f"完整备份已保存：\n{path}"),
        )

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份", str(self.ctx.paths.backups), "备份 (*.zip *.db)"
        )
        if path and confirm(
            self,
            "确认恢复",
            "将用所选备份替换本机现有数据。继续前，软件会自动备份当前数据。",
            action="恢复备份",
            danger=True,
        ):
            self.window.run_job(
                "校验并恢复备份", lambda: self.ctx.backup.restore(Path(path)), self.restored
            )

    def restored(self, before):
        self.window.pages[1].reset()
        self.window.pages[1].refresh()
        self.refresh()
        self.window.refresh_theme()
        self.window.update_company()
        show_information(self, "恢复完成", f"数据库已恢复。恢复前备份：\n{before}")

    def health(self):
        self.window.run_job(
            "检查数据库",
            self.ctx.db.health_check,
            lambda _: show_information(
                self, "检查完成", "数据检查通过，记录与关联信息正常。"
            ),
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
                lambda count, start=options["start"], end=options["end"]: self.window.show_demo_data(
                    count, start, end
                ),
            )

    def clear_demo(self):
        if confirm(
            self,
            "清理演示数据",
            "永久删除所有演示数据记录（包括回收站）。正式记录不受影响。确定继续？",
            action="删除演示数据",
            danger=True,
        ):
            self.window.run_job(
                "清理演示数据",
                self.ctx.demo.clear,
                lambda count: self.window.notify(f"已清理 {count} 条演示记录"),
            )
