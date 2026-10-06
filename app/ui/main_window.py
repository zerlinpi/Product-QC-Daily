from datetime import date

from PySide6.QtCore import QSize, Qt, QThread, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.ui.common import (
    APP_DEFAULT_SIZE,
    APP_MAX_SIZE,
    APP_MIN_SIZE,
    CONTROL_MIN_HEIGHT,
    SIDEBAR_MARGINS,
    SIDEBAR_WIDTH,
    STATUS_PROGRESS_MAX_WIDTH,
    TOPBAR_MARGINS,
    TOPBAR_MIN_HEIGHT,
    friendly_error,
    guarded,
    label,
    message_box,
    toolbar_layout,
)
from app.ui.dialogs.progress_dialog import TaskProgressDialog
from app.ui.localization import configure_chinese_ui
from app.ui.pages.analytics_page import AnalyticsPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.defects_page import DefectsPage
from app.ui.pages.inspection_page import InspectionPage
from app.ui.pages.records_page import RecordsPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.styles.theme import apply_theme, sync_native_titlebar
from app.ui.widgets.chart_widget import ChartWidget
from app.ui.worker import Worker


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        configure_chinese_ui(QApplication.instance())
        super().__init__()
        self.ctx, self._job = ctx, None
        self._job_dialog = None
        self._export_message = None
        self.setWindowTitle("成品日检管理系统")
        self.resize(*APP_DEFAULT_SIZE)
        self.setMinimumSize(*APP_MIN_SIZE)
        self._dark_theme = apply_theme(ctx.settings.get("theme"))
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("qcSidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(*SIDEBAR_MARGINS)
        nav.setSpacing(2)
        nav.addWidget(label("成品日检", "brand"))
        nav.addWidget(label("质量管理", "muted"))
        nav.addSpacing(4)
        nav_items = [
            ("质量总览", QStyle.StandardPixmap.SP_ComputerIcon),
            ("日检录入", QStyle.StandardPixmap.SP_FileDialogNewFolder),
            ("检验记录", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("质量分析", QStyle.StandardPixmap.SP_FileDialogContentsView),
            ("不良项目", QStyle.StandardPixmap.SP_MessageBoxWarning),
            ("报表中心", QStyle.StandardPixmap.SP_FileIcon),
            ("系统设置", QStyle.StandardPixmap.SP_FileDialogInfoView),
        ]
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFrameShape(QFrame.Shape.NoFrame)
        self.navigation.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation.setUniformItemSizes(True)
        self.navigation.setIconSize(QSize(16, 16))
        self.navigation.setSpacing(0)
        self.nav_items = []
        for i, (title, icon) in enumerate(nav_items):
            item = QListWidgetItem(self.style().standardIcon(icon), title)
            item.setToolTip(f"{title} · Ctrl+{i + 1}")
            item.setSizeHint(QSize(0, CONTROL_MIN_HEIGHT))
            self.navigation.addItem(item)
            self.nav_items.append(item)
        self.navigation.currentRowChanged.connect(self._navigate_from_sidebar)
        nav.addWidget(self.navigation, 1)
        nav.addWidget(label("数据保存在本机", "muted"))
        nav.addWidget(label(f"版本 {__version__} · 离线使用", "muted"))
        root.addWidget(sidebar)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        top = QFrame()
        top.setObjectName("topbar")
        toolbar = toolbar_layout(top)
        toolbar.setContentsMargins(*TOPBAR_MARGINS)
        top.setMinimumHeight(TOPBAR_MIN_HEIGHT)
        self.company = label("成品质量管理", "section")
        toolbar.addWidget(self.company)
        toolbar.addStretch()
        toolbar.addWidget(label("本机 · 离线", "muted"))
        right.addWidget(top)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        root.addLayout(right, 1)
        self.setCentralWidget(central)
        self.pages = [
            cls(ctx, self)
            for cls in (
                DashboardPage,
                InspectionPage,
                RecordsPage,
                AnalyticsPage,
                DefectsPage,
                ReportsPage,
                SettingsPage,
            )
        ]
        for page in self.pages:
            self.stack.addWidget(page)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(STATUS_PROGRESS_MAX_WIDTH)
        self.progress.hide()
        self.statusBar().setSizeGripEnabled(True)
        self.statusBar().addPermanentWidget(self.progress)
        self.shortcuts = []
        for key, action in [
            ("Ctrl+S", self.pages[1].save_record),
            ("Ctrl+N", self.pages[1].new_record),
            ("Ctrl+D", self.pages[1].copy_last),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(
                lambda fn=action: fn() if self.stack.currentIndex() == 1 and not self._job else None
            )
            self.shortcuts.append(shortcut)
        for index in range(7):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(
                lambda page=index: self.navigate(page) if not self._job else None
            )
            self.shortcuts.append(shortcut)
        for key, action in [("Ctrl+F", self.focus_search), ("F5", self.refresh_current_page)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(action)
            self.shortcuts.append(shortcut)
        self.update_company()
        self.navigate(0)
        size = ctx.settings.get("window_size")
        if isinstance(size, list) and len(size) == 2:
            self.resize(
                max(APP_MIN_SIZE[0], min(size[0], APP_MAX_SIZE[0])),
                max(APP_MIN_SIZE[1], min(size[1], APP_MAX_SIZE[1])),
            )
        if ctx.settings.get("window_maximized", False):
            self.setWindowState(Qt.WindowState.WindowMaximized)
        hints = QApplication.instance().styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_color_scheme_changed)
        sync_native_titlebar(self, self._dark_theme)

    def _navigate_from_sidebar(self, index):
        if index < 0 or not hasattr(self, "pages"):
            return
        previous = self.stack.currentIndex()
        self.navigate(index)
        if self.stack.currentIndex() != index:
            blocked = self.navigation.blockSignals(True)
            self.navigation.setCurrentRow(previous)
            self.navigation.blockSignals(blocked)

    def refresh_theme(self):
        self._dark_theme = apply_theme(self.ctx.settings.get("theme"))
        for chart in self.findChildren(ChartWidget):
            chart.refresh_theme()
        sync_native_titlebar(self, self._dark_theme)

    def _system_color_scheme_changed(self, *_):
        if self.ctx.settings.get("theme") == "system":
            self.refresh_theme()

    def update_company(self):
        self.company.setText(
            " · ".join(
                filter(None, [self.ctx.settings.get("company"), self.ctx.settings.get("factory")])
            )
            or "成品质量管理"
        )

    def focus_search(self):
        page = self.pages[self.stack.currentIndex()]
        widget = getattr(page, "search", None)
        if widget is None:
            self.notify("当前页面没有搜索框")
            return
        widget.setFocus()
        if hasattr(widget, "selectAll"):
            widget.selectAll()

    @guarded
    def refresh_current_page(self):
        if self._job:
            self.notify("当前任务执行中，暂不能刷新")
            return
        self.pages[self.stack.currentIndex()].refresh()
        self.notify("当前页面已刷新")

    def notify(self, message):
        self.statusBar().showMessage(message, 15000)

    def show_demo_data(self, count, start=None, end=None):
        today = date.today()
        current_month_only = (
            start is None
            or end is None
            or (
                (start.year, start.month) == (today.year, today.month)
                and (end.year, end.month) == (today.year, today.month)
            )
        )
        includes_today = start is None or end is None or start <= today <= end
        if not current_month_only or not includes_today:
            self.navigate(3)
            self.pages[3].show_demo_range(start, end)
            self.notify(
                f"已生成 {count:,} 条演示记录 · 当前正在查看 {start} 至 {end} 的演示分析"
            )
            return
        dashboard = self.pages[0]
        dashboard.source.blockSignals(True)
        dashboard.source.setCurrentIndex(1)
        dashboard.source.blockSignals(False)
        self.navigate(0)
        self.notify(f"已生成 {count:,} 条演示记录 · 当前正在查看演示数据")

    def export_completed(self, result):
        self.notify("导出完成")
        if self._export_message is not None:
            self._export_message.close()
        box = message_box(
            self,
            "导出完成",
            "导出完成",
            informative_text=f"文件已成功保存到：\n{result}",
        )
        box.setObjectName("exportCompleteDialog")
        box.setWindowModality(Qt.WindowModality.WindowModal)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.finished.connect(lambda *_: setattr(self, "_export_message", None))
        self._export_message = box
        box.open()

    @guarded
    def navigate(self, index):
        current = self.stack.currentIndex()
        if (
            hasattr(self, "pages")
            and current == 1
            and index != 1
            and not self.pages[1].can_discard()
        ):
            return
        if current == 1 and index != 1:
            if self.pages[1].dirty:
                self.pages[1].discard_changes()
        self.stack.setCurrentIndex(index)
        if hasattr(self, "navigation") and self.navigation.currentRow() != index:
            blocked = self.navigation.blockSignals(True)
            self.navigation.setCurrentRow(index)
            self.navigation.blockSignals(blocked)
        if index == 1:
            entry = self.pages[1]
            if entry.record_id and not entry.dirty:
                try:
                    record = self.ctx.inspections.get(entry.record_id)
                except ValueError:
                    record = None
                if record is None or record["deleted_at"]:
                    entry.reset(preserve=False)
                else:
                    entry.load_record(record)
            entry.refresh()
            entry.defects.reload()
        else:
            self.pages[index].refresh()

    @guarded
    def new_inspection(self):
        entry = self.pages[1]
        if entry.can_discard():
            entry.reset()
            self.navigate(1)

    @guarded
    def open_record(self, identifier, copy_record=False):
        if not self.pages[1].can_discard():
            return
        record = self.ctx.inspections.get(identifier)
        self.pages[1].dirty = False
        self.navigate(1)
        self.pages[1].load_record(record, copy_record)

    def run_job(self, name, function, callback=None, finished=None):
        if self._job:
            self.notify("当前任务仍在执行，请稍候")
            return
        thread = QThread(self)
        worker = Worker(function)
        worker.moveToThread(thread)
        self._job = (thread, worker, callback, finished)
        self._job_result = None
        self.centralWidget().setEnabled(False)
        popup_job = name.startswith("导出") or name == "生成演示数据"
        if popup_job:
            self.progress.hide()
            self.statusBar().clearMessage()
            if name == "生成演示数据":
                self._job_dialog = TaskProgressDialog(
                    self,
                    name,
                    window_title="正在生成演示数据",
                    message="正在生成模拟质检记录并写入本地数据库，请稍候…",
                )
            else:
                self._job_dialog = TaskProgressDialog(
                    self,
                    name,
                    window_title="正在导出",
                    message="正在生成文件，请稍候…",
                )
            self._job_dialog.show()
        else:
            self.progress.show()
            self.statusBar().showMessage(name + "…")
        thread.started.connect(worker.run)
        worker.completed.connect(self._job_completed)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(self._job_finished)
        thread.start()

    @Slot(object, object)
    def _job_completed(self, result, error):
        self._job_result = (result, error)

    @Slot()
    def _job_finished(self):
        thread, _, callback, finished = self._job
        result, error = self._job_result
        self._job = None
        thread.deleteLater()
        self.centralWidget().setEnabled(True)
        self.progress.hide()
        self.statusBar().clearMessage()
        if self._job_dialog is not None:
            self._job_dialog.accept()
            self._job_dialog.deleteLater()
            self._job_dialog = None
        if finished:
            finished()
        if error:
            friendly_error(self, error)
        elif callback:
            try:
                callback(result)
            except Exception as exc:
                friendly_error(self, exc)

    def closeEvent(self, event):
        if self._job:
            self.notify("任务正在执行，完成后再关闭软件")
            event.ignore()
            return
        if not self.pages[1].can_discard():
            event.ignore()
            return
        try:
            self.ctx.settings.update(
                {
                    "window_size": [self.normalGeometry().width(), self.normalGeometry().height()],
                    "window_maximized": self.isMaximized(),
                }
            )
        except Exception as exc:
            friendly_error(self, exc)
        event.accept()
