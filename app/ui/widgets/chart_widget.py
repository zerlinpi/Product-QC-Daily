import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.common import label


class ChartWidget(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label(title, "section"))
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.setMinimumHeight(190)
        self.plot.showGrid(x=False, y=True, alpha=0.12)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.getPlotItem().hideButtons()
        self.plot.getAxis("left").setPen("#8a8a8a")
        self.plot.getAxis("bottom").setPen("#8a8a8a")
        layout.addWidget(self.plot)
        self.empty = label("暂无数据", "muted")
        layout.addWidget(self.empty)

    def draw(self, labels, values, bars=False, percent=False, cumulative=None):
        self.plot.clear()
        self.empty.setVisible(not any(values))
        if not values:
            labels, values = ["—"], [0]
        xs = list(range(len(values)))
        if bars:
            self.plot.addItem(
                pg.BarGraphItem(x=xs, height=values, width=0.62, brush="#0067c0", pen=None)
            )
        else:
            self.plot.plot(
                xs,
                values,
                pen=pg.mkPen("#0067c0", width=2.5),
                symbol="o",
                symbolSize=4,
                symbolBrush="#0067c0",
                fillLevel=0,
                brush=pg.mkBrush(0, 103, 192, 20),
            )
        if cumulative is not None:
            # Separate percentage chart is drawn by the parent; avoid misleading dual scales.
            self.plot.plot(
                xs, cumulative, pen=pg.mkPen("#ca5010", width=2), symbol="o", symbolSize=4
            )
        step = max(1, len(labels) // 7)
        self.plot.getAxis("bottom").setTicks(
            [[(i, str(labels[i])) for i in range(0, len(labels), step)]]
        )
        self.plot.setLabel("left", "占比 %" if percent else "数量")
        self.plot.setYRange(0, max(max(values) * 1.25, 1), padding=0)
        self.plot.setXRange(-0.6, max(len(values) - 0.4, 0.6), padding=0)
