import pyqtgraph as pg

from app.ui.widgets.chart_widget import ChartWidget


class ParetoWidget(ChartWidget):
    def __init__(self):
        super().__init__("不良分布与累计占比 · 柱形看数量，橙线看占比")
        item = self.plot.getPlotItem()
        item.showAxis("right")
        item.setLabel("right", "累计占比 %")
        self.percentage_view = pg.ViewBox()
        self.percentage_view.setMenuEnabled(False)
        self.percentage_view.setMouseEnabled(x=False, y=False)
        item.scene().addItem(self.percentage_view)
        item.getAxis("right").linkToView(self.percentage_view)
        self.percentage_view.setXLink(item.vb)
        self.percentage_view.setYRange(0, 100, padding=0)
        item.vb.sigResized.connect(self.sync_geometry)

    def sync_geometry(self):
        self.percentage_view.setGeometry(self.plot.getPlotItem().vb.sceneBoundingRect())
        self.percentage_view.linkedViewChanged(
            self.plot.getPlotItem().vb, self.percentage_view.XAxis
        )

    def show_rows(self, rows):
        self.draw([r["code"] for r in rows], [r["value"] for r in rows], bars=True)
        self.percentage_view.clear()
        self.percentage_view.addItem(
            pg.PlotCurveItem(
                list(range(len(rows))),
                [r["cumulative"] * 100 for r in rows],
                pen=pg.mkPen("#e49b38", width=2.5),
            )
        )
        self.percentage_view.addItem(
            pg.InfiniteLine(
                80,
                angle=0,
                pen=pg.mkPen(
                    "#e49b38",
                    width=1,
                    style=__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PenStyle.DashLine,
                ),
            )
        )
        self.percentage_view.setYRange(0, 100, padding=0)
        self.sync_geometry()
