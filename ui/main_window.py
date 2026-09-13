"""High-performance operator display for the boiler drum simulator."""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFrame, QGraphicsScene, QGraphicsView,
    QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from controllers.simulation_engine import SimulationEngine
from models.alarm import AlarmManager, AlarmPriority
from models.trend_history import TrendHistory
from ui.alarm_widget import ALARM_STYLESHEET, AlarmDashboard
from ui.mimic_scene import build_layout
from ui.trend_widget import TREND_STYLESHEET, TrendDashboard


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
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
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
        self.pv_value.setObjectName("faceplatePVNormal")
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

        self.deviation = QLabel("ERROR (SP − PV)   +0.0 mm")
        self.deviation.setToolTip("Positive error: level is below the requested setpoint. Negative error: level is above it.")
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
        self.output_status = QLabel(
            "CONTROL OUTPUT TRACKING"
        )
        self.output_status.setWordWrap(True)
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

    def update_values(self, level, setpoint, output, alarm_priority=None):
        self.pv_value.setText(f"{level:.1f}\nmm")
        self.sp_value.setText(f"{setpoint:.1f}\nmm")
        self.out_value.setText(f"{output:.1f}\n%")
        error = setpoint - level
        self.deviation.setText(f"ERROR (SP − PV)   {error:+.1f} mm")
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

        pv_name = {
            AlarmPriority.CRITICAL: "faceplatePVCritical",
            AlarmPriority.WARNING: "faceplatePVWarning",
        }.get(alarm_priority, "faceplatePVNormal")
        if self.pv_value.objectName() != pv_name:
            self.pv_value.setObjectName(pv_name)
            self.pv_value.style().unpolish(self.pv_value)
            self.pv_value.style().polish(self.pv_value)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCS Simulator | Boiler Unit 01")
        self.resize(1500, 900)
        self.setMinimumSize(1120, 700)
        self.engine = SimulationEngine()
        self.elapsed_seconds = 0.0
        self.trend_history = TrendHistory(max_samples=7200)
        self.alarm_manager = AlarmManager()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._simulation_tick)
        self._build_ui()
        self._connect_commands()
        self._apply_theme()
        initial_snapshot = self.engine.drum.snapshot()
        self.alarm_manager.update_drum_level(
            initial_snapshot.level_mm,
            self.elapsed_seconds,
        )
        self._update_display(initial_snapshot)
        self._record_trend_sample(initial_snapshot)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_simulation_bar())
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._build_navigation())

        self.display_stack = QStackedWidget()
        self.overview_page = self._build_process_area()
        self.trend_dashboard = TrendDashboard()
        self.trend_dashboard.clear_requested.connect(self._clear_trend_history)
        self.alarm_dashboard = AlarmDashboard()
        self.alarm_dashboard.acknowledge_requested.connect(
            self._acknowledge_alarm
        )
        self.alarm_dashboard.acknowledge_all_requested.connect(
            self._acknowledge_all_alarms
        )
        self.display_stack.addWidget(self.overview_page)
        self.display_stack.addWidget(self.trend_dashboard)
        self.display_stack.addWidget(self.alarm_dashboard)
        workspace_layout.addWidget(self.display_stack, 1)

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
        self.page_title = QLabel("DRUM LEVEL OVERVIEW")
        self.page_title.setObjectName("pageTitle")
        self.run_badge = QLabel("●  READY")
        self.run_badge.setObjectName("stoppedBadge")
        self.sim_time = QLabel("SIM  00:00:00")
        self.sim_time.setObjectName("headerMeta")
        self.alarm_count = QLabel("ALARMS  0")
        self.alarm_count.setObjectName("headerMeta")
        layout.addWidget(brand)
        layout.addWidget(title)
        layout.addWidget(self._vertical_line())
        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.alarm_count)
        return header

    def _build_simulation_bar(self):
        bar = QFrame()
        bar.setObjectName("simulationBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 6, 18, 6)
        layout.setSpacing(12)
        layout.addWidget(self.run_badge)
        layout.addWidget(self.sim_time)
        self.simulation_hint = QLabel("Ready · press Start to advance the process")
        self.simulation_hint.setObjectName("mutedLabel")
        layout.addWidget(self.simulation_hint)
        layout.addStretch()
        self.start_button = QPushButton("▶  START")
        self.start_button.setObjectName("startButton")
        self.stop_button = QPushButton("PAUSE")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setToolTip("Freeze simulation time and values; Resume continues the same run.")
        self.stop_button.setEnabled(False)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        return bar

    def _build_navigation(self):
        nav = QFrame()
        nav.setObjectName("navigation")
        nav.setFixedWidth(116)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(9, 14, 9, 14)
        layout.setSpacing(7)
        self.overview_button = QPushButton("▦\nOVERVIEW")
        self.overview_button.setObjectName("navActive")
        self.overview_button.setCheckable(True)
        self.overview_button.setChecked(True)
        self.overview_button.clicked.connect(self.show_overview)

        self.trends_button = QPushButton("⌁\nTRENDS")
        self.trends_button.setObjectName("navButton")
        self.trends_button.setCheckable(True)
        self.trends_button.setToolTip("Show live boiler drum control-loop trends")
        self.trends_button.clicked.connect(self.show_trends)

        self.alarms_button = QPushButton("△\nALARMS")
        self.alarms_button.setObjectName("navButton")
        self.alarms_button.setCheckable(True)
        self.alarms_button.setToolTip("Show active alarms and alarm history")
        self.alarms_button.clicked.connect(self.show_alarms)
        self._nav_buttons = (
            self.overview_button,
            self.trends_button,
            self.alarms_button,
        )
        self._active_nav_button = self.overview_button
        layout.addWidget(self.overview_button)
        layout.addWidget(self.trends_button)
        layout.addWidget(self.alarms_button)
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
        legend = QLabel("WATER → TEAL   ·   STEAM → ROSE")
        legend.setObjectName("mutedLabel")
        section_row.addWidget(section)
        section_row.addStretch()
        section_row.addWidget(legend)
        for label, tooltip, action in (
            ("−", "Zoom out", lambda: self.view.scale(0.8, 0.8)),
            ("+", "Zoom in to read instrument labels", lambda: self.view.scale(1.25, 1.25)),
            ("FIT", "Fit the complete process drawing", self._fit_mimic),
        ):
            button = QPushButton(label)
            button.setObjectName("mimicZoom")
            button.setToolTip(tooltip)
            button.clicked.connect(action)
            section_row.addWidget(button)
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
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
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
        self.alarm_banner = banner
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 7, 16, 7)
        self.alarm_banner_state = QLabel("✓  SYSTEM NORMAL")
        self.alarm_banner_state.setObjectName("normalState")
        self.alarm_banner_message = QLabel("NO ACTIVE PROCESS ALARMS")
        self.alarm_banner_message.setWordWrap(True)
        self.alarm_banner_message.setObjectName("alarmMessage")
        self.banner_acknowledge = QPushButton("ACKNOWLEDGE")
        self.banner_acknowledge.setObjectName("bannerAcknowledge")
        self.banner_acknowledge.setVisible(False)
        self.banner_acknowledge.clicked.connect(self._acknowledge_banner_alarm)
        self.status_text = QLabel("SIMULATION READY")
        self.status_text.setObjectName("alarmMessage")
        layout.addWidget(self.alarm_banner_state)
        layout.addWidget(self.alarm_banner_message, 1)
        layout.addWidget(self.banner_acknowledge)
        layout.addWidget(self.status_text)
        return banner

    @staticmethod
    def _vertical_line():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("headerSeparator")
        return line

    def show_overview(self):
        self.display_stack.setCurrentWidget(self.overview_page)
        self.page_title.setText("DRUM LEVEL OVERVIEW")
        self._activate_navigation(self.overview_button)
        self.view.fitInView(
            self.scene.sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def show_trends(self):
        self.display_stack.setCurrentWidget(self.trend_dashboard)
        self.page_title.setText("DRUM CONTROL LOOP TRENDS")
        self._activate_navigation(self.trends_button)
        self.trend_dashboard.refresh(self.trend_history)

    def show_alarms(self):
        self.display_stack.setCurrentWidget(self.alarm_dashboard)
        self.page_title.setText("PROCESS ALARM SUMMARY")
        self._activate_navigation(self.alarms_button)
        self._refresh_alarm_dashboard()

    def _activate_navigation(self, active_button):
        self._active_nav_button = active_button
        self._refresh_navigation()

    def _refresh_navigation(self):
        unacknowledged = len(self.alarm_manager.unacknowledged_alarms)
        alarm_icon = f"△ {unacknowledged}" if unacknowledged else "△"
        self.alarms_button.setText(f"{alarm_icon}\nALARMS")
        self.alarms_button.setToolTip(
            f"{unacknowledged} unacknowledged alarm(s)"
            if unacknowledged
            else "Show active alarms and alarm history"
        )

        for button in self._nav_buttons:
            button.setChecked(button is self._active_nav_button)
            if button is self._active_nav_button:
                object_name = "navActive"
            elif button is self.alarms_button and unacknowledged:
                object_name = "navAlarm"
            else:
                object_name = "navButton"
            if button.objectName() != object_name:
                button.setObjectName(object_name)
                self._repolish(button)

    def _record_trend_sample(self, snapshot):
        self.trend_history.append(
            time_seconds=self.elapsed_seconds,
            snapshot=snapshot,
            setpoint_mm=self.engine.controller.setpoint_mm,
            valve_position_pct=self.engine.valve.position_pct,
        )
        if self.display_stack.currentWidget() is self.trend_dashboard:
            self.trend_dashboard.refresh(self.trend_history)

    def _clear_trend_history(self):
        self.trend_history.clear()
        self._record_trend_sample(self.engine.drum.snapshot())
        self.trend_dashboard.refresh(self.trend_history)

    def _connect_commands(self):
        self.faceplate.level_setpoint.valueChanged.connect(self.engine.set_level_setpoint)
        self.faceplate.steam_demand.valueChanged.connect(self.engine.set_steam_demand)
        self.faceplate.level_setpoint.valueChanged.connect(self._refresh_operator_values)
        self.faceplate.steam_demand.valueChanged.connect(self._refresh_operator_values)
        self.start_button.clicked.connect(self.start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)

    def _refresh_operator_values(self, *_args):
        self._update_display(self.engine.drum.snapshot())

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
        self.simulation_hint.setText("Live · process values and trends are updating")

    def stop_simulation(self):
        if not self.timer.isActive():
            return
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.start_button.setText("▶  RESUME")
        self.stop_button.setEnabled(False)
        self.run_badge.setText("●  PAUSED")
        self.run_badge.setObjectName("stoppedBadge")
        self._repolish(self.run_badge)
        self.status_text.setText("SIMULATION PAUSED")
        self.simulation_hint.setText("Paused · process values and simulation time are frozen")

    def _simulation_tick(self):
        snapshot = self.engine.step()
        self.elapsed_seconds += self.engine.dt
        self.alarm_manager.update_drum_level(
            snapshot.level_mm,
            self.elapsed_seconds,
        )
        self._update_display(snapshot)
        self._record_trend_sample(snapshot)

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
            self.tags["drum_visual"].set_setpoint(setpoint)
        alarm_priority = self._highest_active_alarm_priority()
        self.faceplate.update_values(
            snapshot.level_mm,
            setpoint,
            valve_position,
            alarm_priority,
        )
        self.tags["level"].set_alarm_priority(alarm_priority)
        if "drum_visual" in self.tags:
            self.tags["drum_visual"].set_alarm_priority(alarm_priority)
        self.level_metric.set_value(f"{snapshot.level_mm:.1f} mm")
        self.pressure_metric.set_value(f"{snapshot.pressure_bar:.1f} bar")
        self.feedwater_metric.set_value(f"{snapshot.feedwater_flow:.1f} %")
        self.steam_metric.set_value(f"{snapshot.steam_flow:.1f} %")
        total = int(self.elapsed_seconds)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.sim_time.setText(f"SIM  {hours:02d}:{minutes:02d}:{seconds:02d}")
        self._update_alarm_display()

    def _highest_active_alarm_priority(self):
        active = self.alarm_manager.active_alarms
        if not active:
            return None
        return max(alarm.definition.priority for alarm in active)

    def _update_alarm_display(self):
        active = self.alarm_manager.active_alarms
        unacknowledged = self.alarm_manager.unacknowledged_alarms
        highest = self.alarm_manager.highest_priority_alarm

        self.alarm_count.setText(
            f"ALARMS  {len(active)}"
            + (f"  |  UNACK {len(unacknowledged)}" if unacknowledged else "")
        )

        if highest is None:
            self.alarm_banner.setObjectName("alarmBanner")
            self.alarm_banner_state.setObjectName("normalState")
            self.alarm_banner_state.setText("✓  SYSTEM NORMAL")
            self.alarm_banner_message.setText("NO ACTIVE PROCESS ALARMS")
            self.banner_acknowledge.setVisible(False)
            self.alarm_count.setObjectName("headerMeta")
        else:
            critical = highest.definition.priority is AlarmPriority.CRITICAL
            acknowledged = highest.acknowledged
            self.alarm_banner.setObjectName(
                "alarmBannerCritical" if critical else "alarmBannerWarning"
            )
            self.alarm_banner_state.setObjectName(
                "criticalState" if critical else "warningState"
            )
            state_text = "ACKNOWLEDGED" if acknowledged else "UNACKNOWLEDGED"
            priority_text = "CRITICAL" if critical else "WARNING"
            self.alarm_banner_state.setText(f"!  {priority_text} — {state_text}")
            self.alarm_banner_message.setText(
                f"{highest.definition.tag}  {highest.definition.message}  "
                f"{highest.value:.1f} {highest.definition.unit}"
            )
            self.banner_acknowledge.setVisible(not acknowledged)
            active_priority = self._highest_active_alarm_priority()
            self.alarm_count.setObjectName(
                "headerAlarmCritical"
                if active_priority is AlarmPriority.CRITICAL
                else "headerAlarmWarning"
            )

        for widget in (
            self.alarm_banner,
            self.alarm_banner_state,
            self.alarm_count,
        ):
            self._repolish(widget)

        self._refresh_navigation()
        self._refresh_alarm_dashboard()

    def _refresh_alarm_dashboard(self):
        self.alarm_dashboard.refresh(
            records=self.alarm_manager.records,
            active_count=len(self.alarm_manager.active_alarms),
            unacknowledged_count=len(
                self.alarm_manager.unacknowledged_alarms
            ),
        )

    def _acknowledge_alarm(self, event_id):
        if self.alarm_manager.acknowledge(event_id):
            self._update_alarm_display()

    def _acknowledge_all_alarms(self):
        if self.alarm_manager.acknowledge_all():
            self._update_alarm_display()

    def _acknowledge_banner_alarm(self):
        alarm = self.alarm_manager.highest_priority_alarm
        if alarm is not None:
            self._acknowledge_alarm(alarm.event_id)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "view"):
            self._fit_mimic()

    def _fit_mimic(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    @staticmethod
    def _repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _apply_theme(self):
        self.setStyleSheet(STYLESHEET + TREND_STYLESHEET + ALARM_STYLESHEET)


STYLESHEET = """
* { font-family: "Segoe UI"; }
#appRoot, QMainWindow { background: #171a1e; color: #d9dde1; }
#topHeader { background: #22272d; border-bottom: 1px solid #3b424a; }
#simulationBar { background: #1d2228; border-bottom: 1px solid #3b424a; }
#brandMark { background: #2e91a3; color: #081013; font-weight: 800; font-size: 15px; padding: 6px 10px; }
#unitTitle { color: #e4e8eb; font-weight: 700; font-size: 14px; letter-spacing: 1px; }
#pageTitle { color: #aeb6be; font-size: 12px; font-weight: 600; }
#headerMeta { color: #aeb6be; font-family: Consolas; font-weight: 600; padding: 5px 8px; }
#headerAlarmWarning { color: #ffd28a; background: #3b3020; border: 1px solid #765b2e; font-family: Consolas; font-weight: 800; padding: 5px 8px; }
#headerAlarmCritical { color: #ffadad; background: #44272a; border: 1px solid #87484d; font-family: Consolas; font-weight: 800; padding: 5px 8px; }
#runningBadge { color: #8fd19e; background: #263a2c; border: 1px solid #3d6848; padding: 5px 9px; font-weight: 700; }
#stoppedBadge { color: #c4c9ce; background: #30353b; border: 1px solid #4b525a; padding: 5px 9px; font-weight: 700; }
#headerSeparator, #separator { color: #3b424a; background: #3b424a; }
#navigation { background: #20242a; border-right: 1px solid #343a42; }
#navButton, #navActive, #navAlarm { min-height: 58px; color: #9da6af; background: transparent; border: 1px solid transparent; font-size: 10px; font-weight: 700; }
#navButton:hover { background: #292f36; color: #e2e6e9; }
#navActive { color: #dceff2; background: #26363b; border-left: 3px solid #51b6c6; }
#navAlarm { color: #ffd28a; background: #332c21; border-left: 3px solid #dda23e; }
#navModule { color: #77818b; font-family: Consolas; font-size: 9px; }
#processPanel { background: #1b1f24; }
#sectionTitle, #eyebrow, #fieldCaption { color: #8dc7d0; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
#mutedLabel { color: #a1abb5; font-size: 11px; }
#mimicView { background: #1e2227; border: 1px solid #343b43; }
#mimicZoom { color: #d9dde1; background: #252a30; border: 1px solid #46505a; min-width: 24px; padding: 3px 5px; font-weight: 700; }
#mimicZoom:hover { border-color: #62baca; }
#faceplate { background: #20252b; border-left: 1px solid #3a424a; }
#faceplateTitle { color: #eef1f3; font-family: Consolas; font-size: 22px; font-weight: 700; }
#autoBadge { color: #a6dfb2; background: #293d2e; border: 1px solid #45634c; padding: 4px 9px; font-weight: 800; }
#valueCaption { color: #a1abb5; font-size: 10px; font-weight: 700; }
#faceplateValue { color: #f0f2f4; background: #191d21; border: 1px solid #3b434c; font-family: Consolas; font-size: 15px; font-weight: 700; padding: 8px 2px; }
#faceplatePVNormal, #faceplatePVWarning, #faceplatePVCritical { font-family: Consolas; font-size: 20px; font-weight: 700; padding: 8px 2px; }
#faceplatePVNormal { color: #f0f2f4; background: #191d21; border: 1px solid #3b434c; }
#faceplatePVWarning { color: #ffd28a; background: #3b3020; border: 2px solid #b48335; }
#faceplatePVCritical { color: #ffadad; background: #44272a; border: 2px solid #c65d65; }
#deviationNormal { color: #a8d7b2; background: #24332a; border-left: 3px solid #6eaf7c; padding: 7px; font-family: Consolas; }
#deviationWarning { color: #ffd28a; background: #3b3020; border-left: 3px solid #dda23e; padding: 7px; font-family: Consolas; }
#operatorInput { color: #eef1f3; background: #171b1f; border: 1px solid #53606b; border-radius: 2px; padding: 7px; font-family: Consolas; font-size: 13px; selection-background-color: #2e91a3; }
#operatorInput:focus { border: 1px solid #62baca; }
#faceplateNote { color: #a1abb5; background: #1b2025; border-left: 2px solid #46515b; padding: 9px; font-size: 11px; }
#trackingLabel { color: #8fd19e; font-size: 9px; font-weight: 700; }
#saturationLabel { color: #ffd28a; background: #3b3020; border-left: 3px solid #dda23e; padding: 7px; font-size: 9px; font-weight: 800; }
#metricTile { background: #22272d; border: 1px solid #353d45; }
#metricCaption { color: #a1abb5; font-size: 10px; font-weight: 700; }
#metricValue { color: #e4e8eb; font-family: Consolas; font-size: 14px; font-weight: 700; }
#alarmBanner { background: #22272d; border-top: 1px solid #3a424a; }
#alarmBannerWarning { background: #332c21; border-top: 2px solid #dda23e; }
#alarmBannerCritical { background: #3c2527; border-top: 2px solid #d85861; }
#normalState { color: #9bd4a7; font-weight: 800; }
#warningState { color: #ffd28a; font-weight: 800; }
#criticalState { color: #ffadad; font-weight: 800; }
#alarmMessage { color: #b5bec7; font-family: Consolas; font-size: 11px; }
#bannerAcknowledge { color: #e6e9eb; background: #2d3238; border: 1px solid #7e858c; padding: 4px 10px; font-size: 9px; font-weight: 800; }
#bannerAcknowledge:hover { border-color: #e2b45f; }
QStatusBar { background: #181b1f; border-top: 1px solid #30363d; min-height: 34px; }
#floatingControls { background: transparent; }
#startButton, #stopButton { min-width: 90px; padding: 5px 12px; font-weight: 700; }
#startButton { color: #b8e4c0; background: #26382b; border: 1px solid #45614b; }
#stopButton { color: #e4c2c2; background: #3b2929; border: 1px solid #634545; }
#startButton:hover, #stopButton:hover { border-color: #8a949e; }
#startButton:disabled, #stopButton:disabled { color: #636b73; background: #24282d; border-color: #343a40; }
QPushButton:disabled { color: #636b73; background: #24282d; border-color: #343a40; }
QToolTip { color: #e4e8eb; background: #252b31; border: 1px solid #515b65; }
"""


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
