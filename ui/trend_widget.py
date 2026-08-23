"""Real-time operator trends for the boiler-drum control loop."""

import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


COLOR_BACKGROUND = "#1b1f24"
COLOR_PLOT = "#1e2227"
COLOR_GRID = "#75808b"
COLOR_TEXT = "#cbd2d8"
COLOR_LEVEL = "#67c7d1"
COLOR_SETPOINT = "#e4bb72"
COLOR_FEEDWATER = "#8fce9d"
COLOR_STEAM = "#d48b90"
COLOR_DEMAND = "#929ba5"
COLOR_VALVE = "#88a9dc"


class TrendDashboard(QWidget):
    """Three coordinated trend plots sharing a trailing time window."""

    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("trendDashboard")
        self.history = None
        self.window_seconds = 60
        self._curves = {}
        self._plots = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(9)
        root.addLayout(self._build_header())

        self.level_plot = self._build_plot(
            title="DRUM LEVEL CONTROL",
            units="mm",
            minimum=250,
            maximum=750,
        )
        normal_band = pg.LinearRegionItem(
            values=(350, 650),
            orientation="horizontal",
            brush=pg.mkBrush(89, 136, 101, 25),
            movable=False,
        )
        normal_band.setZValue(-10)
        self.level_plot.addItem(normal_band)
        self._add_curve(self.level_plot, "level", "LEVEL PV", COLOR_LEVEL, width=2.5)
        self._add_curve(
            self.level_plot,
            "setpoint",
            "LEVEL SP",
            COLOR_SETPOINT,
            dashed=True,
        )

        self.flow_plot = self._build_plot(
            title="PROCESS FLOW BALANCE",
            units="%",
            minimum=0,
            maximum=125,
        )
        self._add_curve(self.flow_plot, "feedwater", "FEEDWATER", COLOR_FEEDWATER, width=2.5)
        self._add_curve(self.flow_plot, "steam_flow", "STEAM FLOW", COLOR_STEAM, width=2.5)
        self._add_curve(
            self.flow_plot,
            "steam_demand",
            "STEAM DEMAND",
            COLOR_DEMAND,
            dashed=True,
        )

        self.valve_plot = self._build_plot(
            title="FEEDWATER VALVE OUTPUT",
            units="%",
            minimum=0,
            maximum=105,
        )
        maximum_line = pg.InfiniteLine(
            pos=100,
            angle=0,
            pen=pg.mkPen("#9f7538", width=1, style=Qt.PenStyle.DashLine),
            movable=False,
        )
        self.valve_plot.addItem(maximum_line)
        self._add_curve(self.valve_plot, "valve", "FCV-001 POSITION", COLOR_VALVE, width=2.5)

        self.flow_plot.setXLink(self.level_plot)
        self.valve_plot.setXLink(self.level_plot)

        for plot in self._plots:
            root.addWidget(plot, 1)

        self.valve_plot.setLabel(
            "bottom",
            "TIME BEFORE PRESENT",
            units="s",
            color=COLOR_TEXT,
            size="9pt",
        )

        footer = QLabel("Historical samples continue recording while the Overview screen is open.")
        footer.setObjectName("trendHint")
        root.addWidget(footer)

    def _build_header(self):
        row = QHBoxLayout()
        title = QLabel("CONTROL LOOP TRENDS")
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        row.addStretch()

        caption = QLabel("WINDOW")
        caption.setObjectName("trendCaption")
        row.addWidget(caption)

        self.window_selector = QComboBox()
        self.window_selector.setObjectName("trendWindow")
        for seconds in (30, 60, 120, 300):
            self.window_selector.addItem(f"{seconds} s", seconds)
        self.window_selector.setCurrentIndex(1)
        self.window_selector.currentIndexChanged.connect(self._change_window)
        row.addWidget(self.window_selector)

        clear_button = QPushButton("CLEAR")
        clear_button.setObjectName("trendClear")
        clear_button.clicked.connect(self._request_clear)
        row.addWidget(clear_button)
        return row

    def _build_plot(self, title, units, minimum, maximum):
        plot = pg.PlotWidget(background=COLOR_PLOT)
        plot.setObjectName("trendPlot")
        plot.setTitle(title, color=COLOR_TEXT, size="10pt", bold=True)
        plot.setLabel("left", units=units, color=COLOR_TEXT, size="9pt")
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.setMouseEnabled(x=False, y=False)
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setYRange(minimum, maximum, padding=0)
        plot.setXRange(-self.window_seconds, 0, padding=0)
        plot.getPlotItem().setContentsMargins(8, 4, 8, 4)

        for axis_name in ("left", "bottom"):
            axis = plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(COLOR_GRID))
            axis.setTextPen(pg.mkPen(COLOR_TEXT))
            axis.setStyle(tickFont=self.font())

        legend = plot.addLegend(offset=(10, 8))
        legend.setBrush(pg.mkBrush(30, 34, 39, 205))
        legend.setPen(pg.mkPen("#404850"))
        self._plots.append(plot)
        return plot

    def _add_curve(self, plot, key, label, color, width=2.0, dashed=False):
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        self._curves[key] = plot.plot(
            [],
            [],
            name=label,
            pen=pg.mkPen(color, width=width, style=style),
            connect="finite",
        )

    def _change_window(self):
        self.window_seconds = int(self.window_selector.currentData())
        if self.history is not None:
            self.refresh(self.history)

    def _request_clear(self):
        self.clear_requested.emit()

    def refresh(self, history):
        self.history = history
        values = history.series(self.window_seconds)
        for name, curve in self._curves.items():
            curve.setData(values["time"], values[name])
        self.level_plot.setXRange(-self.window_seconds, 0, padding=0)


TREND_STYLESHEET = """
#trendDashboard { background: #1b1f24; }
#trendPlot { border: 1px solid #363e46; }
#trendCaption { color: #939ca5; font-size: 10px; font-weight: 700; }
#trendWindow { color: #e1e5e8; background: #20252b; border: 1px solid #46505a; padding: 4px 9px; }
#trendWindow QAbstractItemView { color: #e1e5e8; background: #20252b; selection-background-color: #34505a; }
#trendClear { color: #d9dde1; background: #252a30; border: 1px solid #46505a; padding: 5px 10px; font-weight: 700; }
#trendClear:hover { border-color: #75bbc8; }
#trendHint { color: #818a94; font-size: 10px; }
"""
