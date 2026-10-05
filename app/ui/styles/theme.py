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
    """Prefer the real host control style instead of repainting standard widgets."""
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
        bg, panel, text, muted, border, sidebar = (
            "#202020",
            "#2b2b2b",
            "#f5f5f5",
            "#b5b5b5",
            "#444444",
            "#252525",
        )
    else:
        bg, panel, text, muted, border, sidebar = (
            "#f3f3f3",
            "#ffffff",
            "#1f1f1f",
            "#616161",
            "#d6d6d6",
            "#f3f3f3",
        )
    accent = "#0067c0"

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

    # Standard controls intentionally stay out of QSS. On Windows this lets
    # WindowsVista/Windows style draw buttons, edits, combos, menus, headers,
    # check boxes, scroll bars, dialogs and message boxes with native metrics.
    app.setStyleSheet(
        f"""
        QMainWindow, QWidget#page {{ background: {bg}; }}
        QLabel#title {{ font-size: 12pt; font-weight: 600; }}
        QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
        QLabel#section {{ font-size: 9.5pt; font-weight: 600; }}
        QLabel#fieldLabel {{ color: {muted}; font-weight: 600; }}
        QLabel#metric {{ font-size: 17pt; font-weight: 600; }}

        QFrame#qcSidebar {{
            background: {sidebar};
            border: none;
            border-right: 1px solid {border};
        }}
        QFrame#qcSidebar QLabel#muted {{ color: {muted}; }}
        QLabel#brand {{ font-size: 10.5pt; font-weight: 600; }}
        QFrame#topbar {{
            background: {panel};
            border: none;
            border-bottom: 1px solid {border};
        }}
        QStatusBar {{
            background: {panel};
            color: {muted};
            border-top: 1px solid {border};
        }}
        QStatusBar::item {{ border: none; }}
        """
    )
    return dark
