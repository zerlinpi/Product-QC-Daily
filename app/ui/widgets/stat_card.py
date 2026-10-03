from app.ui.common import card, label


def stat_card(title, value="0", note=""):
    frame, layout = card()
    layout.addWidget(label(title, "muted"))
    metric = label(value, "metric")
    layout.addWidget(metric)
    delta = label(note, "muted")
    layout.addWidget(delta)
    frame.value_label, frame.delta = metric, delta
    return frame
