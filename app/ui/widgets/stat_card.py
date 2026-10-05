from PySide6.QtWidgets import QGroupBox, QVBoxLayout

from app.ui.common import label


def stat_card(title, value="0", note=""):
    """Use a native group box instead of a web-style metric card."""
    frame = QGroupBox(title)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 7, 10, 8)
    layout.setSpacing(3)
    metric = label(value, "metric")
    layout.addWidget(metric)
    delta = label(note, "muted")
    layout.addWidget(delta)
    frame.value_label, frame.delta = metric, delta
    return frame
