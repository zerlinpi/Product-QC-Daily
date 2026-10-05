from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(mode="light"):
    app = QApplication.instance()
    dark = mode == "dark" or (
        mode == "system" and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    )
    bg, card, text, muted, border, field, selected = (
        ("#101827", "#1a2536", "#eef3ff", "#9aabc3", "#334158", "#152032", "#263e69")
        if dark
        else ("#f4f6fb", "#ffffff", "#172640", "#64748b", "#dfe5ef", "#ffffff", "#e8efff")
    )
    danger_bg = "#3a2427" if dark else "#fff2f0"
    danger_border = "#7e4148" if dark else "#efb5ae"
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, bg),
        (QPalette.ColorRole.Base, card),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.Button, card),
        (QPalette.ColorRole.Highlight, "#365cdd"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(f"""
        QWidget {{ font-family: 'Microsoft YaHei UI', 'Noto Sans CJK SC', 'Segoe UI', sans-serif; font-size: 13px; color: {text}; }}
        QMainWindow, QWidget#page {{ background: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#title {{ font-size: 25px; font-weight: 700; letter-spacing: 1px; }}
        QLabel#subtitle, QLabel#muted {{ color: {muted}; }}
        QLabel#section {{ font-size: 15px; font-weight: 600; }}
        QLabel#fieldLabel {{ color: {muted}; font-size: 12px; font-weight: 600; }}
        QLabel#metric {{ font-size: 28px; font-weight: 700; }}
        QFrame#card, QGroupBox {{ background: {card}; border: 1px solid {border}; border-radius: 12px; }}
        QGroupBox {{ margin-top: 16px; padding: 18px 12px 12px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 5px; }}
        QFrame#qcSidebar {{ background: #15243e; border: none; }}
        QFrame#qcSidebar QLabel {{ color: #e8eef9; }}
        QFrame#qcSidebar QLabel#muted {{ color: #8ea1be; font-size: 11px; }}
        QLabel#brand {{ font-size: 21px; font-weight: 800; color: #ffffff; }}
        QPushButton#nav {{ background: transparent; color: #aebed5; text-align: left; border: none; border-radius: 8px; padding: 14px 16px; font-size: 14px; }}
        QPushButton#nav:hover {{ background: #203654; color: #ffffff; }}
        QPushButton#nav:checked {{ background: #2d4d85; color: #ffffff; font-weight: 600; }}
        QFrame#topbar {{ background: {card}; border-bottom: 1px solid {border}; }}
        QPushButton {{ background: {card}; border: 1px solid {border}; border-radius: 7px; padding: 8px 14px; min-height: 20px; font-weight: 500; }}
        QPushButton:hover {{ background: {selected}; border-color: #9ab0ef; }}
        QPushButton:focus {{ border: 2px solid #6f89e8; padding: 7px 13px; }}
        QPushButton:pressed {{ background: #365cdd; color: white; }}
        QPushButton#primary {{ background: #365cdd; color: #ffffff; border: 1px solid #365cdd; font-weight: 600; }}
        QPushButton#primary:hover {{ background: #284bbd; }}
        QPushButton#danger {{ color: #d3544c; }}
        QPushButton#danger:hover {{ background: {danger_bg}; border-color: {danger_border}; }}
        QPushButton:disabled {{ color: {muted}; border-color: {border}; }}
        QPushButton#primary:disabled {{ background: {selected}; color: {muted}; border-color: {border}; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QComboBox, QTextEdit {{ background: {field}; border: 1px solid {border}; border-radius: 6px; padding: 7px 9px; selection-background-color: #365cdd; min-height: 20px; }}
        QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color: #5e7dea; }}
        QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QComboBox:disabled, QTextEdit:disabled {{ background: {bg}; color: {muted}; }}
        QComboBox QAbstractItemView {{ background: {card}; selection-background-color: {selected}; selection-color: {text}; }}
        QTableWidget {{ background: {card}; alternate-background-color: {bg}; gridline-color: {border}; border: 1px solid {border}; border-radius: 8px; selection-background-color: #365cdd; selection-color: #ffffff; }}
        QTableWidget::item {{ padding: 7px; border: none; }}
        QTableWidget::item:hover {{ background: {selected}; }}
        QTableWidget::item:selected {{ background: #365cdd; color: #ffffff; }}
        QTableWidget::item:selected:hover {{ background: #284bbd; color: #ffffff; }}
        QHeaderView::section {{ background: {bg}; color: {muted}; border: none; border-bottom: 1px solid {border}; padding: 9px; font-weight: 600; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: {bg}; width: 9px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 30px; }}
        QScrollBar:horizontal {{ background: {bg}; height: 9px; margin: 0; }}
        QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-width: 30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ height: 0; width: 0; }}
        QCheckBox {{ spacing: 7px; padding: 3px; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; }}
        QStatusBar {{ background: {card}; color: {muted}; }}
        QProgressBar {{ background: {bg}; border: 1px solid {border}; border-radius: 4px; min-height: 7px; max-height: 7px; text-align: center; }}
        QProgressBar::chunk {{ background: #365cdd; border-radius: 3px; }}
        QDialog {{ background: {bg}; }}
        QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; padding: 5px; }}
    """)
    return dark
