from PySide6.QtWidgets import QGroupBox

from app.ui.common import SECTION_MARGINS, label, stack_layout


def stat_card(title, value="0", note="", tone=""):
    """Use a native group box with restrained semantic emphasis for quality metrics."""
    frame = QGroupBox(title)
    layout = stack_layout(frame, SECTION_MARGINS, spacing=4)
    kind = "metric" if not tone else f"metric{tone.capitalize()}"
    metric = label(value, kind)
    layout.addWidget(metric)
    delta = label(note, "muted")
    layout.addWidget(delta)
    frame.value_label, frame.delta = metric, delta
    return frame
