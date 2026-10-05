import ctypes
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory


def preferred_style_name(platform: str, available) -> str | None:
    names = {name.lower(): name for name in available}
    if platform == "win32":
        for candidate in ("windowsvista", "windows"):
            if candidate in names:
                return names[candidate]
    return names.get("fusion") or next(iter(available), None)


def configure_platform_style(app: QApplication) -> str | None:
    """Use the host desktop style instead of forcing the app to look cross-platform."""
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
        # Theme polish must never stop the desktop application from opening.
        return


def apply_theme(mode="light"):
    app = QApplication.instance()
    dark = mode == "dark" or (
        mode == "system" and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    )
    if dark:
        bg, panel, text, muted, border, field, hover, selected, header, sidebar = (
            "#202020",
            "#2b2b2b",
            "#f5f5f5",
            "#b5b5b5",
            "#444444",
            "#303030",
            "#383838",
            "#343d48",
            "#292929",
            "#252525",
        )
    else:
        bg, panel, text, muted, border, field, hover, selected, header, sidebar = (
            "#f3f3f3",
            "#ffffff",
            "#1f1f1f",
            "#616161",
            "#d6d6d6",
            "#ffffff",
            "#f5f5f5",
            "#e5f1fb",
            "#fafafa",
            "#f3f3f3",
        )
    accent = "#0067c0"
    accent_hover = "#005a9e"
    danger = "#c42b1c"
    danger_bg = "#442726" if dark else "#fdf3f2"
    disabled = "#777777" if dark else "#9a9a9a"

    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, bg),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, panel),
        (QPalette.ColorRole.AlternateBase, bg),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, panel),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.ToolTipBase, panel),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.Highlight, accent),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
        (QPalette.ColorRole.PlaceholderText, muted),
    ]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(
        f"""
        QWidget {{ color: {text}; }}
        QMainWindow, QWidget#page {{ background: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#title {{ font-size: 18pt; font-weight: 600; }}
        QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
        QLabel#section {{ font-size: 10pt; font-weight: 600; }}
        QLabel#fieldLabel {{ color: {muted}; font-size: 9pt; font-weight: 600; }}
        QLabel#metric {{ font-size: 20pt; font-weight: 600; }}

        QFrame#card, QGroupBox {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 4px;
        }}
        QGroupBox {{ margin-top: 14px; padding: 14px 10px 10px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}

        QFrame#qcSidebar {{
            background: {sidebar};
            border: none;
            border-right: 1px solid {border};
        }}
        QFrame#qcSidebar QLabel {{ color: {text}; }}
        QFrame#qcSidebar QLabel#muted {{ color: {muted}; font-size: 9pt; }}
        QLabel#brand {{ font-size: 12pt; font-weight: 600; color: {text}; }}
        QPushButton#nav {{
            background: transparent;
            color: {text};
            text-align: left;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 7px 9px;
            min-height: 24px;
        }}
        QPushButton#nav:hover {{ background: {hover}; }}
        QPushButton#nav:checked {{
            background: {selected};
            border-left: 3px solid {accent};
            padding-left: 7px;
            font-weight: 600;
        }}

        QFrame#topbar {{ background: {panel}; border-bottom: 1px solid {border}; }}

        QPushButton {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 5px 12px;
            min-height: 20px;
        }}
        QPushButton:hover {{ background: {hover}; border-color: #b5b5b5; }}
        QPushButton:focus {{ border-color: {accent}; }}
        QPushButton:pressed {{ background: {selected}; }}
        QPushButton#primary {{
            background: {accent};
            color: #ffffff;
            border-color: {accent};
            font-weight: 600;
        }}
        QPushButton#primary:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
        QPushButton#danger {{ color: {danger}; }}
        QPushButton#danger:hover {{ background: {danger_bg}; border-color: {danger}; }}
        QPushButton:disabled {{ color: {disabled}; border-color: {border}; }}
        QPushButton#primary:disabled {{ background: {border}; color: {disabled}; border-color: {border}; }}
        QMessageBox QPushButton, QDialogButtonBox QPushButton {{ min-width: 72px; }}

        QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QComboBox, QTextEdit {{
            background: {field};
            border: 1px solid {border};
            border-radius: 3px;
            padding: 5px 8px;
            selection-background-color: {accent};
            min-height: 20px;
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover,
        QTimeEdit:hover, QComboBox:hover, QTextEdit:hover {{ border-color: #b5b5b5; }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
        QTimeEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color: {accent}; }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled,
        QTimeEdit:disabled, QComboBox:disabled, QTextEdit:disabled {{
            background: {bg};
            color: {disabled};
        }}

        QComboBox {{ padding-right: 31px; }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border: none;
            border-left: 1px solid {border};
            background: transparent;
        }}
        QComboBox::drop-down:hover {{ background: {hover}; }}
        QComboBox::down-arrow {{ width: 8px; height: 8px; }}
        QComboBox QAbstractItemView {{
            background: {panel};
            color: {text};
            border: 1px solid {border};
            border-radius: 3px;
            padding: 2px;
            outline: 0;
            selection-background-color: {accent};
            selection-color: #ffffff;
        }}
        QComboBox QAbstractItemView::item {{ min-height: 24px; padding: 4px 8px; }}
        QComboBox QAbstractItemView::item:hover {{ background: {selected}; }}
        QComboBox QAbstractItemView::item:selected {{ background: {accent}; color: #ffffff; }}

        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border: none;
            border-left: 1px solid {border};
            background: transparent;
        }}
        QDateEdit::drop-down:hover {{ background: {hover}; }}
        QDateEdit::down-arrow {{ width: 8px; height: 8px; }}

        QMenu {{ background: {panel}; color: {text}; border: 1px solid {border}; padding: 2px; }}
        QMenu::item {{ padding: 6px 24px; border-radius: 2px; }}
        QMenu::item:selected {{ background: {selected}; }}
        QMenu::separator {{ height: 1px; background: {border}; margin: 4px 6px; }}

        QTableWidget {{
            background: {panel};
            alternate-background-color: {bg};
            gridline-color: {border};
            border: 1px solid {border};
            border-radius: 2px;
            selection-background-color: {accent};
            selection-color: #ffffff;
        }}
        QTableWidget::item {{ padding: 4px 6px; border: none; }}
        QTableWidget::item:hover {{ background: {selected}; }}
        QTableWidget::item:selected {{ background: {accent}; color: #ffffff; }}
        QHeaderView::section {{
            background: {header};
            color: {text};
            border: none;
            border-right: 1px solid {border};
            border-bottom: 1px solid {border};
            padding: 6px 7px;
            font-weight: 600;
        }}
        QTableCornerButton::section {{
            background: {header};
            border: none;
            border-right: 1px solid {border};
            border-bottom: 1px solid {border};
        }}

        QScrollArea {{ border: none; background: transparent; }}
        QCheckBox {{ spacing: 5px; }}

        QStatusBar {{
            background: {panel};
            color: {muted};
            border-top: 1px solid {border};
            min-height: 22px;
        }}
        QStatusBar::item {{ border: none; }}
        QProgressBar {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 2px;
            min-height: 7px;
            max-height: 7px;
            text-align: center;
        }}
        QProgressBar::chunk {{ background: {accent}; }}
        QProgressBar#taskProgress {{ min-height: 8px; max-height: 8px; }}

        QDialog {{ background: {bg}; }}
        QDialog#taskProgressDialog {{ background: {bg}; }}
        QMessageBox {{ background: {bg}; }}
        QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border}; padding: 4px; }}
        """
    )
    return dark
