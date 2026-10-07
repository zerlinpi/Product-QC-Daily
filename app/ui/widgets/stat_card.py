from app.ui.common import card, label


def stat_card(title, value="0", note="", tone=""):
    """Flat KPI card with muted title and restrained semantic emphasis."""
    frame, layout = card()
    layout.setSpacing(4)
    title_label = label(title, "metricTitle")
    layout.addWidget(title_label)
    kind = "metric" if not tone else f"metric{tone.capitalize()}"
    metric = label(value, kind)
    layout.addWidget(metric)
    delta = label(note, "muted")
    layout.addWidget(delta)
    frame.title_label, frame.value_label, frame.delta = title_label, metric, delta
    return frame
