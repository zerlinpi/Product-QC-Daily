from PySide6.QtWidgets import QGroupBox

from app.ui.common import SECTION_MARGINS, label, stack_layout


def stat_card(title, value="0", note=""):
    """Use a native group box instead of a web-style metric card."""
    frame = QGroupBox(title)
    layout = stack_layout(frame, SECTION_MARGINS, spacing=4)
    metric = label(value, "metric")
    layout.addWidget(metric)
    delta = label(note, "muted")
    layout.addWidget(delta)
    frame.value_label, frame.delta = metric, delta
    return frame
