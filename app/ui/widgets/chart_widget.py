import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from app.ui.common import chart_palette, label, stack_layout


class ChartWidget(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = stack_layout(self)
        layout.addWidget(label(title, "section"))
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.setMinimumHeight(190)
        self.plot.showGrid(x=False, y=True, alpha=0.12)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.getPlotItem().hideButtons()
        layout.addWidget(self.plot)
        self.empty = label("暂无数据", "empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty)
        self._last_draw = None
        self._apply_theme()

    def _apply_theme(self):
        colors = chart_palette()
        for name in ("left", "bottom"):
            axis = self.plot.getAxis(name)
            axis.setPen(colors["axis"])
            axis.setTextPen(colors["text"])
        return colors

    def refresh_theme(self):
        self._apply_theme()
        if self._last_draw is not None:
            labels, values, bars, percent, cumulative = self._last_draw
            self.draw(labels, values, bars=bars, percent=percent, cumulative=cumulative)

    def draw(self, labels, values, bars=False, percent=False, cumulative=None):
        labels = list(labels)
        values = list(values)
        cumulative = list(cumulative) if cumulative is not None else None
        self._last_draw = (labels, values, bars, percent, cumulative)
        colors = self._apply_theme()
        self.plot.clear()
        self.empty.setVisible(not any(values))
        if not values:
            labels, values = ["—"], [0]
        xs = list(range(len(values)))
        if bars:
            self.plot.addItem(
                pg.BarGraphItem(
                    x=xs, height=values, width=0.62, brush=colors["accent"], pen=None
                )
            )
        else:
            self.plot.plot(
                xs,
                values,
                pen=pg.mkPen(colors["accent"], width=2.5),
                symbol="o",
                symbolSize=4,
                symbolBrush=colors["accent"],
                fillLevel=0,
                brush=pg.mkBrush(colors["fill"]),
            )
        if cumulative is not None:
            # Separate percentage chart is drawn by the parent; avoid misleading dual scales.
            self.plot.plot(
                xs,
                cumulative,
                pen=pg.mkPen(colors["warning"], width=2),
                symbol="o",
                symbolSize=4,
            )
        step = max(1, len(labels) // 7)
        self.plot.getAxis("bottom").setTicks(
            [[(i, str(labels[i])) for i in range(0, len(labels), step)]]
        )
        self.plot.setLabel("left", "占比 %" if percent else "数量")
        self.plot.setYRange(0, max(max(values) * 1.25, 1), padding=0)
        self.plot.setXRange(-0.6, max(len(values) - 0.4, 0.6), padding=0)
