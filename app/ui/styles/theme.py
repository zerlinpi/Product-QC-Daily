import ctypes
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory


def preferred_style_name(platform: str, available) -> str | None:
    """Use Fusion as the cross-platform canvas for the custom desktop design system."""
    names = {name.lower(): name for name in available}
    if "fusion" in names:
        return names["fusion"]
    if platform == "win32":
        for candidate in ("windowsvista", "windows"):
            if candidate in names:
                return names[candidate]
    return next(iter(available), None)


def configure_platform_style(app: QApplication) -> str | None:
    """Use one predictable base style so the app no longer inherits legacy Win7 visuals."""
    style = preferred_style_name(sys.platform, QStyleFactory.keys())
    if style:
        app.setStyle(style)
    return style


def sync_native_titlebar(widget, dark: bool) -> None:
    """Keep the Windows title bar aligned with the selected light/dark theme."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        enabled = ctypes.c_int(1 if dark else 0)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE, old fallback
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
            if result == 0:
                break
    except Exception:
        return


def apply_theme(mode="light"):
    app = QApplication.instance()
    dark = mode == "dark" or (
        mode == "system" and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    )
    if dark:
        bg = "#111318"
        panel = "#181b21"
        sidebar = "#15181d"
        text = "#f3f4f6"
        muted = "#9ca3af"
        border = "#2d323b"
        subtle = "#20242b"
        alternate = "#1d2128"
        hover = "#252a33"
        pressed = "#2b313b"
        input_bg = "#171a20"
        accent = "#3b82f6"
        accent_hover = "#60a5fa"
        accent_soft = "#172554"
        accent_text = "#dbeafe"
        disabled = "#6b7280"
        disabled_bg = "#20242a"
        success = "#4ade80"
        warning = "#f59e0b"
        error = "#fb7185"
        danger_soft = "#3a1d24"
    else:
        bg = "#f5f7fa"
        panel = "#ffffff"
        sidebar = "#ffffff"
        text = "#111827"
        muted = "#6b7280"
        border = "#e5e7eb"
        subtle = "#f8fafc"
        alternate = "#fbfcfd"
        hover = "#f3f4f6"
        pressed = "#e5e7eb"
        input_bg = "#ffffff"
        accent = "#2563eb"
        accent_hover = "#1d4ed8"
        accent_soft = "#eff6ff"
        accent_text = "#1d4ed8"
        disabled = "#9ca3af"
        disabled_bg = "#f3f4f6"
        success = "#16a34a"
        warning = "#d97706"
        error = "#dc2626"
        danger_soft = "#fef2f2"

    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, bg),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, panel),
        (QPalette.ColorRole.AlternateBase, alternate),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, panel),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.ToolTipBase, panel),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.Highlight, accent),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
        (QPalette.ColorRole.PlaceholderText, muted),
        (QPalette.ColorRole.Link, accent),
        (QPalette.ColorRole.Mid, border),
    ]:
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(disabled))
    app.setPalette(palette)

    app.setStyleSheet(
        f"""
        QMainWindow, QWidget#page {{
            background: {bg};
            color: {text};
        }}
        QWidget#pageHeader {{
            background: transparent;
        }}
        QLabel#title {{
            color: {text};
            font-size: 16pt;
            font-weight: 700;
        }}
        QLabel#subtitle, QLabel#muted, QLabel#empty {{
            color: {muted};
        }}
        QLabel#summary {{
            color: {muted};
            font-weight: 600;
        }}
        QLabel#section {{
            color: {text};
            font-size: 10pt;
            font-weight: 600;
        }}
        QLabel#status {{
            color: {text};
            font-weight: 600;
        }}
        QLabel#success {{
            color: {success};
            font-weight: 600;
        }}
        QLabel#warning {{
            color: {warning};
            font-weight: 600;
        }}
        QLabel#error {{
            color: {error};
            font-weight: 600;
        }}
        QLabel#fieldLabel {{
            color: {muted};
            font-weight: 600;
        }}
        QLabel#metric {{
            color: {text};
            font-size: 19pt;
            font-weight: 700;
        }}
        QLabel#metricWarning {{
            color: {warning};
            font-size: 19pt;
            font-weight: 700;
        }}
        QLabel#metricSuccess {{
            color: {success};
            font-size: 19pt;
            font-weight: 700;
        }}

        QFrame#qcSidebar {{
            background: {sidebar};
            border: none;
            border-right: 1px solid {border};
        }}
        QFrame#qcSidebar QLabel#muted {{
            color: {muted};
        }}
        QLabel#brand {{
            color: {text};
            font-size: 13pt;
            font-weight: 700;
        }}
        QListWidget#navigation {{
            background: transparent;
            border: none;
            outline: none;
            padding: 0;
        }}
        QListWidget#navigation::item {{
            color: {muted};
            border: none;
            border-radius: 8px;
            margin: 2px 0;
            padding: 0 10px;
        }}
        QListWidget#navigation::item:hover {{
            color: {text};
            background: {hover};
        }}
        QListWidget#navigation::item:selected {{
            color: {accent_text};
            background: {accent_soft};
            font-weight: 600;
        }}

        QFrame#topbar {{
            background: {panel};
            border: none;
            border-bottom: 1px solid {border};
        }}
        QFrame#pageHeaderSeparator,
        QFrame#sidebarTopSeparator,
        QFrame#sidebarBottomSeparator {{
            background: {border};
            border: none;
            min-height: 1px;
            max-height: 1px;
        }}

        QGroupBox {{
            color: {text};
            background: {panel};
            border: 1px solid {border};
            border-radius: 10px;
            margin-top: 10px;
            padding: 12px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 5px;
            color: {text};
            background: {panel};
        }}
        QFrame#card {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 10px;
        }}

        QPushButton {{
            color: {text};
            background: {panel};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 12px;
        }}
        QPushButton:hover {{
            background: {hover};
            border-color: {muted};
        }}
        QPushButton:pressed {{
            background: {pressed};
        }}
        QPushButton:focus {{
            border-color: {accent};
        }}
        QPushButton:disabled {{
            color: {disabled};
            background: {disabled_bg};
            border-color: {border};
        }}
        QPushButton#primary {{
            color: #ffffff;
            background: {accent};
            border-color: {accent};
            font-weight: 600;
        }}
        QPushButton#primary:hover {{
            background: {accent_hover};
            border-color: {accent_hover};
        }}
        QPushButton#primary:pressed {{
            background: {accent_hover};
        }}
        QPushButton#danger {{
            color: {error};
            background: {panel};
            border-color: {error};
        }}
        QPushButton#danger:hover {{
            background: {danger_soft};
        }}

        QLineEdit,
        QComboBox,
        QDateEdit,
        QTimeEdit,
        QSpinBox,
        QDoubleSpinBox,
        QTextEdit {{
            color: {text};
            background: {input_bg};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {accent};
            selection-color: #ffffff;
        }}
        QLineEdit:hover,
        QComboBox:hover,
        QDateEdit:hover,
        QTimeEdit:hover,
        QSpinBox:hover,
        QTextEdit:hover {{
            border-color: {muted};
        }}
        QLineEdit:focus,
        QComboBox:focus,
        QDateEdit:focus,
        QTimeEdit:focus,
        QSpinBox:focus,
        QTextEdit:focus {{
            border-color: {accent};
        }}
        QLineEdit:disabled,
        QComboBox:disabled,
        QDateEdit:disabled,
        QTimeEdit:disabled,
        QSpinBox:disabled,
        QTextEdit:disabled {{
            color: {disabled};
            background: {disabled_bg};
        }}
        QComboBox::drop-down {{
            width: 24px;
            border: none;
            background: transparent;
        }}
        QComboBox QAbstractItemView {{
            color: {text};
            background: {panel};
            border: 1px solid {border};
            selection-background-color: {accent_soft};
            selection-color: {accent_text};
            outline: none;
        }}
        QCheckBox {{
            color: {text};
            spacing: 6px;
        }}

        QTableWidget {{
            color: {text};
            background: {panel};
            alternate-background-color: {alternate};
            border: 1px solid {border};
            border-radius: 8px;
            gridline-color: {border};
            selection-background-color: {accent_soft};
            selection-color: {accent_text};
            outline: none;
        }}
        QTableWidget::item {{
            border: none;
            padding-left: 6px;
            padding-right: 6px;
        }}
        QTableWidget::item:selected {{
            background: {accent_soft};
            color: {accent_text};
        }}
        QHeaderView::section {{
            color: {muted};
            background: {subtle};
            border: none;
            border-right: 1px solid {border};
            border-bottom: 1px solid {border};
            padding: 0 8px;
            font-weight: 600;
        }}

        QMenu {{
            color: {text};
            background: {panel};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            border-radius: 6px;
            padding: 7px 24px 7px 10px;
        }}
        QMenu::item:selected {{
            color: {accent_text};
            background: {accent_soft};
        }}
        QToolTip {{
            color: {text};
            background: {panel};
            border: 1px solid {border};
            padding: 4px 7px;
        }}

        QStatusBar {{
            color: {muted};
            background: {panel};
            border-top: 1px solid {border};
        }}
        QStatusBar::item {{
            border: none;
        }}
        QProgressBar {{
            color: {text};
            background: {subtle};
            border: 1px solid {border};
            border-radius: 5px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: {accent};
            border-radius: 4px;
        }}

        QScrollBar:vertical {{
            width: 10px;
            margin: 2px;
            background: transparent;
        }}
        QScrollBar:horizontal {{
            height: 10px;
            margin: 2px;
            background: transparent;
        }}
        QScrollBar::handle:vertical,
        QScrollBar::handle:horizontal {{
            min-height: 28px;
            min-width: 28px;
            background: {border};
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover,
        QScrollBar::handle:horizontal:hover {{
            background: {muted};
        }}
        QScrollBar::add-line,
        QScrollBar::sub-line,
        QScrollBar::add-page,
        QScrollBar::sub-page {{
            border: none;
            background: transparent;
            width: 0;
            height: 0;
        }}
        """
    )
    return dark
