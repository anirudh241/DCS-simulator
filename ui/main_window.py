"""
Main application window for the DCS Simulator.

Milestone 3:
Operator controls for the boiler drum control loop.
"""

import sys

from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QDockWidget,
    QLabel,
    QMainWindow,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from controllers.simulation_engine import SimulationEngine
from ui.mimic_scene import build_layout


SCENE_WIDTH = 1600
SCENE_HEIGHT = 900

COLOR_BACKGROUND = QColor(10, 12, 18)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "DCS Simulator — Boiler Drum Module"
        )

        self.resize(1400, 850)

        # --------------------------------------------------
        # Simulation
        # --------------------------------------------------

        self.engine = SimulationEngine()

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(
            self._simulation_tick
        )

        # --------------------------------------------------
        # UI
        # --------------------------------------------------

        self._build_scene()
        self._build_toolbar()
        self._build_control_panel()
        self._build_statusbar()
        self._apply_theme()

    # ======================================================
    # Scene
    # ======================================================

    def _build_scene(self):

        self.scene = QGraphicsScene(
            0,
            0,
            SCENE_WIDTH,
            SCENE_HEIGHT,
        )

        self.scene.setBackgroundBrush(
            COLOR_BACKGROUND
        )

        # build_layout returns the live tag objects
        self.tags = build_layout(self.scene)

        self.view = QGraphicsView(self.scene)

        self.view.setRenderHint(
            self.view.renderHints()
        )

        self.view.setDragMode(
            QGraphicsView.DragMode.ScrollHandDrag
        )

        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        self.setCentralWidget(self.view)

    # ======================================================
    # Toolbar
    # ======================================================

    def _build_toolbar(self):

        toolbar = QToolBar("Simulation Controls")
        toolbar.setMovable(False)

        self.action_start = QAction(
            "Start",
            self,
        )

        self.action_stop = QAction(
            "Stop",
            self,
        )

        self.action_start.triggered.connect(
            self.start_simulation
        )

        self.action_stop.triggered.connect(
            self.stop_simulation
        )

        self.action_stop.setEnabled(False)

        toolbar.addAction(self.action_start)
        toolbar.addAction(self.action_stop)

        self.addToolBar(toolbar)

    # ======================================================
    # Operator Control Panel
    # ======================================================

    def _build_control_panel(self):

        dock = QDockWidget(
            "Operator Controls",
            self,
        )

        dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        panel = QWidget()

        layout = QVBoxLayout(panel)

        # --------------------------------------------------
        # Header
        # --------------------------------------------------

        title = QLabel("BOILER DRUM CONTROL")

        title.setObjectName("controlTitle")

        layout.addWidget(title)

        # --------------------------------------------------
        # Controller mode
        # --------------------------------------------------

        mode_label = QLabel(
            "LEVEL CONTROLLER     AUTO"
        )

        mode_label.setObjectName(
            "autoLabel"
        )

        layout.addWidget(mode_label)

        # --------------------------------------------------
        # Controls
        # --------------------------------------------------

        form = QFormLayout()

        # Drum level setpoint
        self.level_setpoint = QDoubleSpinBox()

        self.level_setpoint.setRange(
            300.0,
            700.0,
        )

        self.level_setpoint.setDecimals(1)

        self.level_setpoint.setSingleStep(
            5.0
        )

        self.level_setpoint.setValue(
            self.engine.controller.setpoint_mm
        )

        self.level_setpoint.setSuffix(
            " mm"
        )

        self.level_setpoint.valueChanged.connect(
            self._set_level_setpoint
        )

        form.addRow(
            "Level SP:",
            self.level_setpoint,
        )

        # Steam demand
        self.steam_demand = QDoubleSpinBox()

        self.steam_demand.setRange(
            0.0,
            100.0,
        )

        self.steam_demand.setDecimals(1)

        self.steam_demand.setSingleStep(
            5.0
        )

        self.steam_demand.setValue(
            self.engine.drum.steam_demand_pct
        )

        self.steam_demand.setSuffix(
            " %"
        )

        self.steam_demand.valueChanged.connect(
            self._set_steam_demand
        )

        form.addRow(
            "Steam Load:",
            self.steam_demand,
        )

        layout.addLayout(form)

        # --------------------------------------------------
        # Information
        # --------------------------------------------------

        info = QLabel(
            "Steam demand changes plant load.\n"
            "The automatic controller adjusts\n"
            "the feedwater valve to maintain\n"
            "the drum level setpoint."
        )

        info.setWordWrap(True)

        info.setObjectName(
            "controlInfo"
        )

        layout.addWidget(info)

        layout.addStretch()

        dock.setWidget(panel)

        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            dock,
        )

    # ======================================================
    # Operator Commands
    # ======================================================

    def _set_level_setpoint(self, value):

        self.engine.set_level_setpoint(
            value
        )

    def _set_steam_demand(self, value):

        self.engine.set_steam_demand(
            value
        )

    # ======================================================
    # Status Bar
    # ======================================================

    def _build_statusbar(self):

        self.status = self.statusBar()

        self.status.showMessage(
            "Simulation: Stopped"
        )

    # ======================================================
    # Simulation Control
    # ======================================================

    def start_simulation(self):

        if not self.timer.isActive():

            self.timer.start()

            self.action_start.setEnabled(
                False
            )

            self.action_stop.setEnabled(
                True
            )

            self.status.showMessage(
                "Simulation: Running"
            )

    def stop_simulation(self):

        if self.timer.isActive():

            self.timer.stop()

            self.action_start.setEnabled(
                True
            )

            self.action_stop.setEnabled(
                False
            )

            self.status.showMessage(
                "Simulation: Stopped"
            )

    # ======================================================
    # Simulation Tick
    # ======================================================

    def _simulation_tick(self):

        snapshot = self.engine.step()

        # --------------------------------------------------
        # Update live instrument tags
        # --------------------------------------------------

        self.tags["level"].set_value(
            f"{snapshot.level_mm:.1f}"
        )

        self.tags["pressure"].set_value(
            f"{snapshot.pressure_bar:.1f}"
        )

        self.tags["temperature"].set_value(
            f"{snapshot.temperature_c:.1f}"
        )

        self.tags["feedwater"].set_value(
            f"{snapshot.feedwater_flow:.1f}"
        )

        self.tags["steam_demand"].set_value(
            f"{snapshot.steam_demand_pct:.1f}"
        )

        self.tags["steam_flow"].set_value(
            f"{snapshot.steam_flow:.1f}"
        )

        self.tags["valve"].set_value(
            f"{self.engine.valve.position_pct:.1f}"
        )

    # ======================================================
    # Theme
    # ======================================================

    def _apply_theme(self):

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0a0c12;
            }

            QToolBar {
                background-color: #12151d;
                border: none;
                spacing: 8px;
                padding: 4px;
            }

            QToolBar QToolButton {
                color: #d8dee9;
                background-color: #1b1f2a;
                border: 1px solid #2a2f3a;
                border-radius: 3px;
                padding: 4px 12px;
            }

            QToolBar QToolButton:hover {
                background-color: #232838;
                border-color: #00c8dc;
            }

            QDockWidget {
                color: #d8dee9;
                background-color: #12151d;
            }

            QDockWidget::title {
                background-color: #1b1f2a;
                padding: 7px;
                font-weight: bold;
            }

            QWidget {
                background-color: #12151d;
                color: #d8dee9;
            }

            QDoubleSpinBox {
                background-color: #0e1118;
                border: 1px solid #3c4655;
                padding: 5px;
                color: #50e878;
            }

            QDoubleSpinBox:focus {
                border: 1px solid #00c8dc;
            }

            QLabel#controlTitle {
                font-size: 13px;
                font-weight: bold;
                color: #00c8dc;
                padding-bottom: 8px;
            }

            QLabel#autoLabel {
                color: #50e878;
                font-weight: bold;
                padding-bottom: 12px;
            }

            QLabel#controlInfo {
                color: #8b93a5;
                padding-top: 15px;
            }

            QStatusBar {
                background-color: #12151d;
                color: #8b93a5;
                border-top: 1px solid #2a2f3a;
            }

            QGraphicsView {
                border: none;
            }
            """
        )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())