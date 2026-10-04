from PySide6.QtCore import QDate, QEvent, Qt, QTime
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QWidget,
)

from app.core.schemas import InspectionInput, RecordFilter
from app.ui.common import Page, button, card, confirm, guarded, label
from app.ui.widgets.defect_selector import DefectSelector


class InspectionPage(Page):
    def __init__(self, ctx, window):
        super().__init__(
            ctx, window, "日检录入", "快速记录每一次检验 · 支持键盘连续填写与扫码枪输入"
        )
        self.record_id, self.signature_path, self.source = None, None, "manual"
        self.dirty = False
        toolbar = QHBoxLayout()
        self.mode = label("新建检验记录", "section")
        toolbar.addWidget(self.mode)
        toolbar.addStretch()
        copy_button = button("复制上一条", self.copy_last)
        copy_button.setToolTip("复制最近一条正式记录作为新记录（Ctrl+D）")
        toolbar.addWidget(copy_button)
        new_button = button("新建记录", self.new_record)
        new_button.setToolTip("开始填写下一条记录（Ctrl+N）")
        toolbar.addWidget(new_button)
        self.layout.addLayout(toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(18)
        left, left_layout = card()
        left_layout.addWidget(label("检验信息", "section"))
        fields = QGridLayout()
        fields.setHorizontalSpacing(18)
        fields.setVerticalSpacing(7)
        self.inspection_date = QDateEdit(QDate.currentDate())
        self.inspection_date.setCalendarPopup(True)
        self.inspection_date.setDisplayFormat("yyyy-MM-dd")
        self.inspection_time = QTimeEdit(QTime.currentTime())
        self.inspection_time.setDisplayFormat("HH:mm:ss")
        self.team = QComboBox()
        self.work_order = QLineEdit()
        self.work_order.setPlaceholderText("输入或扫描加工单号")
        self.inspector = QLineEdit()
        self.inspector.setPlaceholderText("检验员姓名")
        self.judgment = QComboBox()
        self.judgment.addItems(["合格", "返工"])
        for name in ("inspection_quantity", "sampling_quantity", "defect_quantity"):
            widget = QSpinBox()
            widget.setRange(0, 100_000_000)
            widget.setGroupSeparatorShown(True)
            if name != "defect_quantity":
                widget.setSpecialValueText("请填写")
            widget.setToolTip("单位：件")
            setattr(self, name, widget)
        names = [
            ("检验日期", self.inspection_date),
            ("检验时间", self.inspection_time),
            ("组别 *", self.team),
            ("加工单号 *", self.work_order),
            ("检验数量 *", self.inspection_quantity),
            ("抽检数量 *", self.sampling_quantity),
            ("不良件数", self.defect_quantity),
            ("检验判定", self.judgment),
            ("检验员 *", self.inspector),
        ]
        for index, (title, widget) in enumerate(names):
            row, col = (index // 2) * 2, index % 2
            fields.addWidget(label(title, "muted"), row, col)
            fields.addWidget(widget, row + 1, col)
            widget.installEventFilter(self)
            for child in widget.findChildren(QLineEdit):
                child.installEventFilter(self)
        left_layout.addLayout(fields)
        self.auto_time = QCheckBox("新建记录保存时使用当前时间")
        self.auto_time.setChecked(True)
        left_layout.addWidget(self.auto_time)
        self.suggestion = label("历史抽样仅供参考，不代表正式检验标准。", "muted", True)
        left_layout.addWidget(self.suggestion)
        helpers = QHBoxLayout()
        helpers.addWidget(button("上一条加工单", self.previous_order))
        helpers.addWidget(button("采用历史抽样建议", self.use_sampling))
        left_layout.addLayout(helpers)
        self.judgment_hint = label("判定由检验员确认，系统建议仅供参考。", "muted", True)
        left_layout.addWidget(self.judgment_hint)
        left_layout.addWidget(label("备注", "muted"))
        self.remark = QTextEdit()
        self.remark.setPlaceholderText("检验说明、异常原因或处理结果")
        self.remark.setMaximumHeight(90)
        left_layout.addWidget(self.remark)
        signature_row = QHBoxLayout()
        self.signature_label = label("尚未选择签名", "muted")
        self.signature_label.setMinimumHeight(44)
        signature_row.addWidget(self.signature_label, 1)
        signature_row.addWidget(button("选择签名图片", self.choose_signature))
        signature_row.addWidget(button("清除签名", self.clear_signature))
        left_layout.addLayout(signature_row)
        right, right_layout = card()
        right_layout.addWidget(label("不良项目", "section"))
        right_layout.addWidget(label("勾选发现的不良项目，再填写各项件数", "muted", True))
        self.defects = DefectSelector(ctx)
        right_layout.addWidget(self.defects, 1)
        grid.addWidget(left, 0, 0)
        grid.addWidget(right, 0, 1)
        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 5)
        scroll.setWidget(content)
        self.layout.addWidget(scroll, 1)
        keep_row = QHBoxLayout()
        keep_row.addWidget(label("下一条沿用", "muted"))
        self.keep = {}
        settings = ctx.settings.all()
        for key, title in [
            ("team", "组别"),
            ("work_order", "加工单号"),
            ("inspection_quantity", "检验数量"),
            ("sampling_quantity", "抽检数量"),
            ("inspector", "检验员"),
        ]:
            checkbox = QCheckBox(title)
            checkbox.setChecked(key in settings["keep_fields"])
            self.keep[key] = checkbox
            keep_row.addWidget(checkbox)
        keep_row.addStretch()
        self.layout.addLayout(keep_row)
        footer = QHBoxLayout()
        self.saved_note = label("* 为必填项 · 回车跳到下一项", "muted")
        footer.addWidget(self.saved_note, 1)
        save_button = button("保存本条", lambda: self.save_record())
        save_button.setToolTip("保存当前记录并留在本页（Ctrl+S）")
        footer.addWidget(save_button)
        footer.addWidget(button("保存并新建", lambda: self.save_record(new=True), primary=True))
        self.layout.addLayout(footer)
        self.refresh()
        self.reset()
        for widget in [self.work_order, self.inspector]:
            widget.textChanged.connect(self.mark_dirty)
        for widget in [self.inspection_quantity, self.sampling_quantity, self.defect_quantity]:
            widget.valueChanged.connect(self.mark_dirty)
        for widget in (self.team, self.judgment):
            widget.currentIndexChanged.connect(self.mark_dirty)
        self.inspection_date.dateChanged.connect(self.mark_dirty)
        self.inspection_time.timeChanged.connect(self.mark_dirty)
        self.remark.textChanged.connect(self.mark_dirty)
        self.defects.changed.connect(self.mark_dirty)
        self.work_order.editingFinished.connect(self.show_suggestion)
        self.defect_quantity.valueChanged.connect(
            lambda value: self.judgment_hint.setText(
                "建议复核不良项目并确认是否返工；可保留实际判定。"
                if value
                else "未发现不良，建议合格；最终判定由检验员确认。"
            )
        )

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self.focusNextChild()
            return True
        return super().eventFilter(watched, event)

    def mark_dirty(self, *_):
        self.dirty = True

    def can_discard(self):
        return (
            not self.dirty
            or confirm(
                self,
                "未保存的录入",
                "当前内容尚未保存。放弃修改后，这次填写的内容不会保留。",
                action="放弃修改",
                cancel="继续填写",
            )
        )

    def refresh(self):
        was_dirty = self.dirty
        previous = self.team.currentText()
        self.team.clear()
        self.team.addItems([t["name"] for t in self.ctx.settings.teams(True)])
        if previous and self.team.findText(previous) < 0:
            self.team.addItem(previous)
        self.team.setCurrentText(previous or self.ctx.settings.get("default_team"))
        for key in ("work_order", "inspector"):
            completer = QCompleter(self.ctx.inspections.recent_values(key), self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            getattr(self, key).setCompleter(completer)
        self.dirty = was_dirty

    def reset(self, preserve=True):
        self.record_id, self.signature_path, self.source = None, None, "manual"
        self.inspection_date.setDate(QDate.currentDate())
        self.inspection_time.setTime(QTime.currentTime())
        self.defect_quantity.setValue(0)
        self.defects.set_values([])
        self.judgment.setCurrentText("合格")
        self.remark.clear()
        for key, check in self.keep.items():
            if not preserve or not check.isChecked():
                widget = getattr(self, key)
                if isinstance(widget, QSpinBox):
                    widget.setValue(0)
                elif isinstance(widget, QLineEdit):
                    widget.clear()
                else:
                    widget.setCurrentText(self.ctx.settings.get("default_team"))
        if not self.inspector.text():
            self.inspector.setText(self.ctx.settings.get("default_inspector"))
        self.signature_label.clear()
        self.signature_label.setText("尚未选择签名")
        self.mode.setText("新建检验记录")
        self.saved_note.setText("本条尚未保存 · * 为必填项")
        self.dirty = False
        self.work_order.setFocus()

    def new_record(self):
        if self.can_discard():
            self.reset()

    def discard_changes(self):
        if self.record_id:
            self.load_record(self.ctx.inspections.get(self.record_id))
        else:
            self.reset(preserve=False)

    def load_record(self, record, copy_record=False):
        self.refresh()
        self.defects.reload()
        self.record_id = None if copy_record else record["id"]
        self.source = record["source"]
        self.signature_path = record["signature_path"]
        self.inspection_date.setDate(
            QDate.currentDate()
            if copy_record
            else QDate.fromString(record["inspection_date"], "yyyy-MM-dd")
        )
        self.inspection_time.setTime(
            QTime.currentTime()
            if copy_record
            else QTime.fromString(record["inspection_time"][:8], "HH:mm:ss")
        )
        if self.team.findText(record["team"]) < 0:
            self.team.addItem(record["team"])
        self.team.setCurrentText(record["team"])
        for name in ("inspection_quantity", "sampling_quantity", "defect_quantity"):
            getattr(self, name).setValue(record[name])
        self.work_order.setText(record["work_order"])
        self.inspector.setText(record["inspector"])
        self.judgment.setCurrentText(record["judgment"])
        self.remark.setPlainText(record["remark"])
        self.defects.set_values(record["defects"])
        self.show_signature()
        self.mode.setText(
            ("复制为新记录" if copy_record else "编辑 · " + record["inspection_no"])
            + ("  [演示数据]" if self.source == "demo" else "")
        )
        self.dirty = copy_record

    @guarded
    def save_record(self, new=False):
        if self.auto_time.isChecked() and not self.record_id:
            self.inspection_time.setTime(QTime.currentTime())
        data = InspectionInput(
            inspection_date=self.inspection_date.date().toPython(),
            inspection_time=self.inspection_time.time().toPython(),
            team=self.team.currentText(),
            work_order=self.work_order.text(),
            inspector=self.inspector.text(),
            inspection_quantity=self.inspection_quantity.value(),
            sampling_quantity=self.sampling_quantity.value(),
            defect_quantity=self.defect_quantity.value(),
            judgment=self.judgment.currentText(),
            signature_path=self.signature_path,
            remark=self.remark.toPlainText(),
            source=self.source,
            defects=self.defects.values(),
        )
        result = self.ctx.inspections.save(data, self.record_id)
        self.record_id, self.signature_path = result["id"], result["signature_path"]
        self.ctx.settings.update(
            {"keep_fields": [key for key, check in self.keep.items() if check.isChecked()]}
        )
        self.dirty = False
        self.mode.setText("已保存 · " + result["inspection_no"])
        self.saved_note.setText("保存成功 · " + result["inspection_no"])
        self.window.notify("检验记录已保存")
        if new:
            self.reset()

    @guarded
    def copy_last(self):
        if not self.can_discard():
            return
        rows, _ = self.ctx.inspections.query(RecordFilter(page_size=1, sort="created_at"))
        if rows:
            self.load_record(rows[0], True)
        else:
            self.window.notify("暂无可复制记录")

    @guarded
    def previous_order(self):
        values = self.ctx.inspections.recent_values(limit=1)
        if values:
            self.work_order.setText(values[0])

    @guarded
    def show_suggestion(self):
        value = self.ctx.inspections.sampling_suggestion(self.work_order.text())
        self.suggestion.setText(
            f"最近同工单抽检 {value} 件，仅供参考，不代表正式抽样标准。"
            if value
            else "暂无同工单抽样历史；请按工厂质量标准填写。"
        )

    @guarded
    def use_sampling(self):
        value = self.ctx.inspections.sampling_suggestion(self.work_order.text())
        if value:
            self.sampling_quantity.setValue(value)
        self.show_suggestion()

    def choose_signature(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择签名图片", "", "图片 (*.png *.jpg *.jpeg)")
        if path:
            self.signature_path = path
            self.show_signature()
            self.dirty = True

    def clear_signature(self):
        self.signature_path = None
        self.show_signature()
        self.dirty = True

    def show_signature(self):
        from pathlib import Path

        self.signature_label.clear()
        if self.signature_path:
            path = Path(self.signature_path)
            if not path.is_absolute():
                path = self.ctx.paths.signatures / path
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.signature_label.setPixmap(
                    pixmap.scaled(
                        160,
                        50,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.signature_label.setText(
            "尚未选择签名" if not self.signature_path else "签名图片丢失，请重新选择"
        )
