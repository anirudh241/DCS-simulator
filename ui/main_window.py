"""High-performance operator display for the boiler drum simulator."""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFrame, QGraphicsScene, QGraphicsView,
    QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from controllers.simulation_engine import SimulationEngine
from ui.mimic_scene import build_layout


SCENE_WIDTH = 1460
SCENE_HEIGHT = 760
COLOR_BACKGROUND = QColor(30, 34, 39)


class MetricTile(QFrame):
    """Compact process value used in the overview strip."""

    def __init__(self, caption, value, parent=None):
        super().__init__(parent)
        self.setObjectName("metricTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(1)
        caption_label = QLabel(caption.upper())
        caption_label.setObjectName("metricCaption")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        layout.addWidget(caption_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(value)


class ControllerFaceplate(QFrame):
    """Operator faceplate for LIC-001 and the load disturbance."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setObjectName("faceplate")
        self.setMinimumWidth(250)
        self.setMaximumWidth(310)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        eyebrow = QLabel("DRUM LEVEL CONTROL")
        eyebrow.setObjectName("eyebrow")
        title_row = QHBoxLayout()
        title = QLabel("LIC-001")
        title.setObjectName("faceplateTitle")
        mode = QLabel("AUTO")
        mode.setObjectName("autoBadge")
        mode.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(mode)
        subtitle = QLabel("Boiler drum level controller")
        subtitle.setObjectName("mutedLabel")
        root.addWidget(eyebrow)
        root.addLayout(title_row)
        root.addWidget(subtitle)
        root.addWidget(self._separator())

        values = QGridLayout()
        values.setHorizontalSpacing(8)
        values.setVerticalSpacing(10)
        self.pv_value = self._large_value("500.0", "mm")
        self.sp_value = self._large_value("500.0", "mm")
        self.out_value = self._large_value("60.0", "%")
        for column, names in enumerate((
            ("PV", "PROCESS VALUE"), ("SP", "SETPOINT"), ("OUT", "VALVE CMD")
        )):
            values.addWidget(self._value_caption(*names), 0, column)
        values.addWidget(self.pv_value, 1, 0)
        values.addWidget(self.sp_value, 1, 1)
        values.addWidget(self.out_value, 1, 2)
        root.addLayout(values)

        self.deviation = QLabel("DEVIATION   +0.0 mm")
        self.deviation.setObjectName("deviationNormal")
        root.addWidget(self.deviation)
        root.addWidget(self._separator())

        root.addWidget(self._field_caption("LEVEL SETPOINT"))
        self.level_setpoint = QDoubleSpinBox()
        self.level_setpoint.setObjectName("operatorInput")
        self.level_setpoint.setRange(300.0, 700.0)
        self.level_setpoint.setDecimals(1)
        self.level_setpoint.setSingleStep(5.0)
        self.level_setpoint.setValue(engine.controller.setpoint_mm)
        self.level_setpoint.setSuffix(" mm")
        root.addWidget(self.level_setpoint)

        root.addWidget(self._field_caption("STEAM LOAD DEMAND"))
        self.steam_demand = QDoubleSpinBox()
        self.steam_demand.setObjectName("operatorInput")
        self.steam_demand.setRange(0.0, 100.0)
        self.steam_demand.setDecimals(1)
        self.steam_demand.setSingleStep(5.0)
        self.steam_demand.setValue(engine.drum.steam_demand_pct)
        self.steam_demand.setSuffix(" %")
        root.addWidget(self.steam_demand)

        note = QLabel(
            "Feedforward follows steam demand. PID trim corrects the "
            "remaining drum-level error."
        )
        note.setWordWrap(True)
        note.setObjectName("faceplateNote")
        root.addWidget(note)
        root.addStretch()
        # footer = QLabel("CONTROL OUTPUT TRACKING")
        # footer.setObjectName("trackingLabel")
        # root.addWidget(footer)
        self.output_status = QLabel(
            "CONTROL OUTPUT TRACKING"
        )
        self.output_status.setObjectName(
            "trackingLabel"
        )
        root.addWidget(self.output_status)

    @staticmethod
    def _separator():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    @staticmethod
    def _field_caption(text):
        label = QLabel(text)
        label.setObjectName("fieldCaption")
        return label

    @staticmethod
    def _value_caption(short_name, long_name):
        label = QLabel(f"{short_name}\n{long_name}")
        label.setObjectName("valueCaption")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def _large_value(value, unit):
        label = QLabel(f"{value}\n{unit}")
        label.setObjectName("faceplateValue")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def update_values(self, level, setpoint, output):
        self.pv_value.setText(f"{level:.1f}\nmm")
        self.sp_value.setText(f"{setpoint:.1f}\nmm")
        self.out_value.setText(f"{output:.1f}\n%")
        error = setpoint - level
        self.deviation.setText(f"DEVIATION   {error:+.1f} mm")
        name = "deviationWarning" if abs(error) >= 25.0 else "deviationNormal"
        if self.deviation.objectName() != name:
            self.deviation.setObjectName(name)
            self.deviation.style().unpolish(self.deviation)
            self.deviation.style().polish(self.deviation)

        # Saturation means the controller wants more movement,
        # but the valve has reached one of its physical limits.
        saturated = (
            (output >= 99.9 and error > 1.0)
            or
            (output <= 0.1 and error < -1.0)
        )

        status_name = (
            "saturationLabel"
            if saturated
            else "trackingLabel"
        )

        status_text = (
            "OUTPUT SATURATED — MAXIMUM CONTROL EFFORT"
            if saturated
            else "CONTROL OUTPUT TRACKING"
        )

        self.output_status.setText(
            status_text
        )

        if self.output_status.objectName() != status_name:
            self.output_status.setObjectName(
                status_name
            )

            self.output_status.style().unpolish(
                self.output_status
            )

            self.output_status.style().polish(
                self.output_status
            )


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCS Simulator | Boiler Unit 01")
        self.resize(1500, 900)
        self.setMinimumSize(1120, 700)
        self.engine = SimulationEngine()
        self.elapsed_seconds = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._simulation_tick)
        self._build_ui()
        self._connect_commands()
        self._apply_theme()
        self._update_display(self.engine.drum.snapshot())

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._build_navigation())
        workspace_layout.addWidget(self._build_process_area(), 1)
        self.faceplate = ControllerFaceplate(self.engine)
        workspace_layout.addWidget(self.faceplate)
        root.addWidget(workspace, 1)
        root.addWidget(self._build_alarm_banner())
        self.setCentralWidget(central)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("topHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 9, 18, 9)
        layout.setSpacing(14)
        brand = QLabel("DCS")
        brand.setObjectName("brandMark")
        title = QLabel("BOILER UNIT 01")
        title.setObjectName("unitTitle")
        page = QLabel("DRUM LEVEL OVERVIEW")
        page.setObjectName("pageTitle")
        self.run_badge = QLabel("●  STOPPED")
        self.run_badge.setObjectName("stoppedBadge")
        self.sim_time = QLabel("SIM  00:00:00")
        self.sim_time.setObjectName("headerMeta")
        alarm_count = QLabel("ALARMS  0")
        alarm_count.setObjectName("headerMeta")
        layout.addWidget(brand)
        layout.addWidget(title)
        layout.addWidget(self._vertical_line())
        layout.addWidget(page)
        layout.addStretch()
        layout.addWidget(self.run_badge)
        layout.addWidget(self.sim_time)
        layout.addWidget(alarm_count)
        return header

    def _build_navigation(self):
        nav = QFrame()
        nav.setObjectName("navigation")
        nav.setFixedWidth(116)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(9, 14, 9, 14)
        layout.setSpacing(7)
        overview = QPushButton("▦\nOVERVIEW")
        overview.setObjectName("navActive")
        overview.setCheckable(True)
        overview.setChecked(True)
        trends = QPushButton("⌁\nTRENDS")
        trends.setObjectName("navButton")
        trends.setToolTip("Trend display is the next project milestone")
        alarms = QPushButton("△\nALARMS")
        alarms.setObjectName("navButton")
        alarms.setToolTip("Alarm history will be added with alarm logic")
        layout.addWidget(overview)
        layout.addWidget(trends)
        layout.addWidget(alarms)
        layout.addStretch()
        module = QLabel("MODULE\nBOILER DRUM\nPHASE 1")
        module.setObjectName("navModule")
        layout.addWidget(module)
        return nav

    def _build_process_area(self):
        panel = QWidget()
        panel.setObjectName("processPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(9)
        section_row = QHBoxLayout()
        section = QLabel("PROCESS MIMIC")
        section.setObjectName("sectionTitle")
        legend = QLabel("NORMAL OPERATING DISPLAY")
        legend.setObjectName("mutedLabel")
        section_row.addWidget(section)
        section_row.addStretch()
        section_row.addWidget(legend)
        layout.addLayout(section_row)
        self.scene = QGraphicsScene(0, 0, SCENE_WIDTH, SCENE_HEIGHT)
        self.scene.setBackgroundBrush(COLOR_BACKGROUND)
        self.tags = build_layout(self.scene)
        # Fit the view around the actual process equipment rather
        # than the larger original design canvas.
        content_rect = (
            self.scene
            .itemsBoundingRect()
            .adjusted(-35, -30, 35, 30)
        )

        self.scene.setSceneRect(
            content_rect
        )
        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("mimicView")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.view, 1)
        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.level_metric = MetricTile("Drum level", "500.0 mm")
        self.pressure_metric = MetricTile("Drum pressure", "165.0 bar")
        self.feedwater_metric = MetricTile("Feedwater", "60.0 %")
        self.steam_metric = MetricTile("Steam flow", "60.0 %")
        for tile in (self.level_metric, self.pressure_metric,
                     self.feedwater_metric, self.steam_metric):
            metrics.addWidget(tile, 1)
        layout.addLayout(metrics)
        return panel

    def _build_alarm_banner(self):
        banner = QFrame()
        banner.setObjectName("alarmBanner")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 7, 16, 7)
        state = QLabel("✓  SYSTEM NORMAL")
        state.setObjectName("normalState")
        message = QLabel("NO UNACKNOWLEDGED PROCESS ALARMS")
        message.setObjectName("alarmMessage")
        self.status_text = QLabel("SIMULATION READY")
        self.status_text.setObjectName("alarmMessage")
        layout.addWidget(state)
        layout.addWidget(message)
        layout.addStretch()
        layout.addWidget(self.status_text)
        return banner

    @staticmethod
    def _vertical_line():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("headerSeparator")
        return line

    def _connect_commands(self):
        self.faceplate.level_setpoint.valueChanged.connect(self.engine.set_level_setpoint)
        self.faceplate.steam_demand.valueChanged.connect(self.engine.set_steam_demand)
        self.start_button = QPushButton("▶  START")
        self.start_button.setObjectName("startButton")
        self.stop_button = QPushButton("■  STOP")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        controls = QFrame()
        controls.setObjectName("floatingControls")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(6, 4, 6, 4)
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        self.statusBar().addPermanentWidget(controls)
        self.statusBar().setSizeGripEnabled(False)
        self.start_button.clicked.connect(self.start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)

    def start_simulation(self):
        if self.timer.isActive():
            return
        self.timer.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.run_badge.setText("●  RUNNING")
        self.run_badge.setObjectName("runningBadge")
        self._repolish(self.run_badge)
        self.status_text.setText("LIVE SIMULATION RUNNING")

    def stop_simulation(self):
        if not self.timer.isActive():
            return
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.run_badge.setText("●  PAUSED")
        self.run_badge.setObjectName("stoppedBadge")
        self._repolish(self.run_badge)
        self.status_text.setText("SIMULATION PAUSED")

    def _simulation_tick(self):
        snapshot = self.engine.step()
        self.elapsed_seconds += self.engine.dt
        self._update_display(snapshot)

    def _update_display(self, snapshot):
        valve_position = self.engine.valve.position_pct
        setpoint = self.engine.controller.setpoint_mm
        values = {
            "level": f"{snapshot.level_mm:.1f}",
            "pressure": f"{snapshot.pressure_bar:.1f}",
            "temperature": f"{snapshot.temperature_c:.1f}",
            "feedwater": f"{snapshot.feedwater_flow:.1f}",
            "steam_demand": f"{snapshot.steam_demand_pct:.1f}",
            "steam_flow": f"{snapshot.steam_flow:.1f}",
            "valve": f"{valve_position:.1f}",
        }
        for tag_name, value in values.items():
            self.tags[tag_name].set_value(value)
        if "drum_visual" in self.tags:
            self.tags["drum_visual"].set_level(snapshot.level_mm)
        self.faceplate.update_values(snapshot.level_mm, setpoint, valve_position)
        self.level_metric.set_value(f"{snapshot.level_mm:.1f} mm")
        self.pressure_metric.set_value(f"{snapshot.pressure_bar:.1f} bar")
        self.feedwater_metric.set_value(f"{snapshot.feedwater_flow:.1f} %")
        self.steam_metric.set_value(f"{snapshot.steam_flow:.1f} %")
        total = int(self.elapsed_seconds)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.sim_time.setText(f"SIM  {hours:02d}:{minutes:02d}:{seconds:02d}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "view"):
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    @staticmethod
    def _repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _apply_theme(self):
        self.setStyleSheet(STYLESHEET)


STYLESHEET = """
* { font-family: "Segoe UI"; }
#appRoot, QMainWindow { background: #171a1e; color: #d9dde1; }
#topHeader { background: #22272d; border-bottom: 1px solid #3b424a; }
#brandMark { background: #2e91a3; color: #081013; font-weight: 800; font-size: 15px; padding: 6px 10px; }
#unitTitle { font-weight: 700; font-size: 14px; letter-spacing: 1px; }
#pageTitle { color: #aeb6be; font-size: 12px; font-weight: 600; }
#headerMeta { color: #aeb6be; font-family: Consolas; font-weight: 600; padding: 5px 8px; }
#runningBadge { color: #8fd19e; background: #263a2c; border: 1px solid #3d6848; padding: 5px 9px; font-weight: 700; }
#stoppedBadge { color: #c4c9ce; background: #30353b; border: 1px solid #4b525a; padding: 5px 9px; font-weight: 700; }
#headerSeparator, #separator { color: #3b424a; background: #3b424a; }
#navigation { background: #20242a; border-right: 1px solid #343a42; }
#navButton, #navActive { min-height: 58px; color: #9da6af; background: transparent; border: 1px solid transparent; font-size: 10px; font-weight: 700; }
#navButton:hover { background: #292f36; color: #e2e6e9; }
#navActive { color: #dceff2; background: #26363b; border-left: 3px solid #51b6c6; }
#navModule { color: #77818b; font-family: Consolas; font-size: 9px; }
#processPanel { background: #1b1f24; }
#sectionTitle, #eyebrow, #fieldCaption { color: #8dc7d0; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
#mutedLabel { color: #818a94; font-size: 10px; }
#mimicView { background: #1e2227; border: 1px solid #343b43; }
#faceplate { background: #20252b; border-left: 1px solid #3a424a; }
#faceplateTitle { color: #eef1f3; font-family: Consolas; font-size: 22px; font-weight: 700; }
#autoBadge { color: #a6dfb2; background: #293d2e; border: 1px solid #45634c; padding: 4px 9px; font-weight: 800; }
#valueCaption { color: #7f8993; font-size: 8px; font-weight: 700; }
#faceplateValue { color: #f0f2f4; background: #191d21; border: 1px solid #3b434c; font-family: Consolas; font-size: 15px; font-weight: 700; padding: 8px 2px; }
#deviationNormal { color: #a8d7b2; background: #24332a; border-left: 3px solid #6eaf7c; padding: 7px; font-family: Consolas; }
#deviationWarning { color: #ffd28a; background: #3b3020; border-left: 3px solid #dda23e; padding: 7px; font-family: Consolas; }
#operatorInput { color: #eef1f3; background: #171b1f; border: 1px solid #53606b; border-radius: 2px; padding: 7px; font-family: Consolas; font-size: 13px; selection-background-color: #2e91a3; }
#operatorInput:focus { border: 1px solid #62baca; }
#faceplateNote { color: #87919a; background: #1b2025; border-left: 2px solid #46515b; padding: 9px; font-size: 10px; }
#trackingLabel { color: #8fd19e; font-size: 9px; font-weight: 700; }
#saturationLabel { color: #ffd28a; background: #3b3020; border-left: 3px solid #dda23e; padding: 7px; font-size: 9px; font-weight: 800; }
#metricTile { background: #22272d; border: 1px solid #353d45; }
#metricCaption { color: #7f8993; font-size: 8px; font-weight: 700; }
#metricValue { color: #e4e8eb; font-family: Consolas; font-size: 14px; font-weight: 700; }
#alarmBanner { background: #22272d; border-top: 1px solid #3a424a; }
#normalState { color: #9bd4a7; font-weight: 800; }
#alarmMessage { color: #89939d; font-family: Consolas; font-size: 10px; }
QStatusBar { background: #181b1f; border-top: 1px solid #30363d; min-height: 34px; }
#floatingControls { background: transparent; }
#startButton, #stopButton { min-width: 90px; padding: 5px 12px; font-weight: 700; }
#startButton { color: #b8e4c0; background: #26382b; border: 1px solid #45614b; }
#stopButton { color: #e4c2c2; background: #3b2929; border: 1px solid #634545; }
#startButton:hover, #stopButton:hover { border-color: #8a949e; }
QPushButton:disabled { color: #636b73; background: #24282d; border-color: #343a40; }
QToolTip { color: #e4e8eb; background: #252b31; border: 1px solid #515b65; }
"""


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()