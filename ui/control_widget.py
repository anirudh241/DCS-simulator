"""Read-only visualization of a completed LIC-001 control calculation."""

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView,
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from controllers.simulation_engine import ControlSample
from ui.zoom_view import ZoomGraphicsView


class ControlBlock:
    """A fixed-size diagram block; only text and limit emphasis change per tick."""

    def __init__(self, scene, x, y, title, accent="#62baca"):
        self.box = scene.addRect(x, y, 280, 190, QPen(QColor("#46525d")), QColor("#222930"))
        scene.addLine(x, y, x + 280, y, QPen(QColor(accent), 3))
        self._text(scene, title, x + 14, y + 12, 11, accent, True)
        self.body = self._text(scene, "Waiting for first calculation", x + 14, y + 43, 12)

    @staticmethod
    def _text(scene, text, x, y, size, color="#dce4ea", bold=False):
        item = QGraphicsSimpleTextItem(text)
        item.setFont(QFont("Consolas", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
        item.setBrush(QColor(color))
        item.setPos(x, y)
        scene.addItem(item)
        return item

    def update(self, text, limited=False):
        self.body.setText(text)
        self.set_emphasis(limited)

    def set_emphasis(self, active):
        self.box.setPen(QPen(QColor("#efbd63" if active else "#46525d"), 3 if active else 1))
        self.box.setBrush(QColor("#403322" if active else "#222930"))


class ControlDiagram(ZoomGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(0, 0, 1020, 720, self))
        self.setObjectName("controlDiagram")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumHeight(320)
        self.blocks = {}
        for key, x, y, title, color in (
            ("inputs", 30, 30, "01  SAMPLED INPUTS", "#62baca"),
            ("error", 370, 30, "02  LEVEL ERROR", "#62baca"),
            ("pid", 710, 30, "03  PID FEEDBACK CORRECTION", "#62baca"),
            ("feedforward", 30, 260, "04  STEAM FEEDFORWARD", "#e4bb72"),
            ("sum", 370, 260, "05  COMBINE", "#e4bb72"),
            ("command", 710, 260, "06  COMMAND LIMIT", "#e4bb72"),
            ("drum", 30, 490, "08  BOILER DRUM", "#62baca"),
            ("valve", 370, 490, "07  FCV-001 VALVE", "#62baca"),
        ):
            self.blocks[key] = ControlBlock(self.scene(), x, y, title, color)

        self._arrow([(310, 125), (370, 125)])
        self._arrow([(170, 220), (170, 260)], "#e4bb72")
        self._arrow([(650, 125), (710, 125)])
        self._arrow([(850, 220), (850, 240), (510, 240), (510, 260)])
        self._arrow([(310, 355), (370, 355)], "#e4bb72")
        self._arrow([(650, 355), (710, 355)], "#e4bb72")
        self._arrow([(990, 355), (1005, 355), (1005, 640), (650, 640)])
        self._arrow([(370, 585), (310, 585)])
        self._arrow([(30, 585), (10, 585), (10, 125), (30, 125)])
        self.gains = ControlBlock._text(self.scene(), "PID GAINS\nWaiting for first step", 718, 490, 12)
        ControlBlock._text(
            self.scene(), "Feedback uses the resulting level\non the next simulation step.",
            30, 692, 10, "#a6b4bf",
        )

    def _arrow(self, points, color="#62baca"):
        pen = QPen(QColor(color), 2)
        for a, b in zip(points, points[1:]):
            self.scene().addLine(*a, *b, pen)
        end = QPointF(*points[-1])
        direction = end - QPointF(*points[-2])
        length = (direction.x() ** 2 + direction.y() ** 2) ** 0.5
        direction /= length
        side = QPointF(-direction.y(), direction.x())
        triangle = QPolygonF([end, end - direction * 9 + side * 4, end - direction * 9 - side * 4])
        self.scene().addPolygon(triangle, pen, QColor(color))

class ControlDashboard(QWidget):
    """Show cached telemetry, never call a controller from a rendering method."""

    def __init__(self):
        super().__init__()
        self.setObjectName("controlDashboard")
        self._last_sample = None
        self._large_error = False
        self._demand_changed = False
        self._emphasis_timer = QTimer(self)
        self._emphasis_timer.setSingleShot(True)
        self._emphasis_timer.setInterval(2200)
        self._emphasis_timer.timeout.connect(self._clear_demand_emphasis)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(9)
        row = QHBoxLayout()
        heading = QLabel("LIC-001  /  CONTROL SYSTEM")
        heading.setObjectName("sectionTitle")
        row.addWidget(heading)
        row.addStretch()
        self.diagram = ControlDiagram()
        for text, tip, action in (
            ("−", "Zoom out", lambda: self.diagram.zoom_by(0.8)),
            ("+", "Zoom in; drag the diagram to pan", lambda: self.diagram.zoom_by(1.25)),
            ("FIT", "Show the whole control loop", self.diagram.fit_diagram),
        ):
            button = QPushButton(text)
            button.setObjectName("mimicZoom")
            button.setToolTip(tip)
            button.clicked.connect(action)
            row.addWidget(button)
        root.addLayout(row)
        overview = QFrame()
        overview.setObjectName("controlOverview")
        overview_layout = QHBoxLayout(overview)
        branches = QVBoxLayout()
        for text, name in (
            ("Steam demand → Feedforward", "overviewFeedforward"),
            ("Level error → PID correction", "overviewFeedback"),
        ):
            label = QLabel(text)
            label.setObjectName(name)
            branches.addWidget(label)
        overview_layout.addLayout(branches)
        destination = QLabel("→  Combine → Valve → Drum")
        destination.setObjectName("overviewDestination")
        destination.setWordWrap(True)
        overview_layout.addWidget(destination, 1)
        overview.setAccessibleName("Steam demand drives feedforward. Level error drives PID correction. Both combine to control the valve and drum.")
        root.addWidget(overview)
        self.attention = QLabel("Feedforward anticipates load; PID corrects the level error.")
        self.attention.setObjectName("controlAttention")
        self.attention.setWordWrap(True)
        root.addWidget(self.attention)
        self.status = QLabel()
        self.status.setObjectName("controlStatus")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(self.diagram, 1)
        self.limits = QLabel("Limits: PID trim ±50% · valve command 0–100% · integral accumulator ±1000 mm·s")
        self.limits.setObjectName("controlHint")
        self.limits.setWordWrap(True)
        root.addWidget(self.limits)
        explanation = QLabel(
            "Read arrows in order. Feedforward uses requested steam demand, not measured steam flow. "
            "Flow is normalized (% of nominal); PID terms are valve percentage points. "
            "The faceplate shows the current process; this diagram retains the inputs used for the last calculation."
        )
        explanation.setObjectName("controlHint")
        explanation.setWordWrap(True)
        root.addWidget(explanation)

    def refresh(self, sample: ControlSample | None, running, requested_setpoint, requested_demand):
        if sample is None:
            self._emphasis_timer.stop()
            self._demand_changed = False
            self._large_error = False
            self._update_attention()
            self.status.setText(
                "WAITING FOR FIRST STEP · Press Start to see the actual calculation. "
                f"Requested SP {requested_setpoint:.1f} mm · demand {requested_demand:.1f}%"
            )
            # Engine.reset() can invalidate a previously displayed calculation.
            if self._last_sample is not None:
                for block in self.diagram.blocks.values():
                    block.update("Waiting for first calculation")
                self.diagram.gains.setText("PID GAINS\nWaiting for first step")
                self._last_sample = None
                self.limits.setText("Limits: PID trim ±50% · valve command 0–100% · integral accumulator ±1000 mm·s")
            return

        c, p = sample.control, sample.control.pid
        pending = requested_setpoint != p.setpoint or requested_demand != c.steam_demand_pct
        state = "LIVE" if running else "PAUSED"
        self.status.setText(
            f"{state} · Last completed step {sample.step_number} · Δt {p.dt:.2f} s"
            + (f" · Pending next step: SP {requested_setpoint:.1f} mm, demand {requested_demand:.1f}%" if pending else "")
        )
        if sample is self._last_sample:
            return
        previous = self._last_sample
        if previous is not None and sample.step_number <= previous.step_number:
            self._clear_demand_emphasis()
            self._large_error = False
        if (previous is not None and sample.step_number == previous.step_number + 1
                and c.steam_demand_pct != previous.control.steam_demand_pct):
            self._demand_changed = True
            self._emphasis_timer.start()
        # Hysteresis avoids flickering around the 25 mm emphasis threshold.
        self._large_error = abs(p.error) >= (20.0 if self._large_error else 25.0)
        self._last_sample = sample
        b = self.diagram.blocks
        b["inputs"].update(f"SP       {p.setpoint:8.2f} mm\nLevel in {p.process_value:8.2f} mm\nDemand   {c.steam_demand_pct:8.2f} %")
        b["error"].update(
            f"Error    {p.error:+8.2f} mm\n\ne = SP − measured level\n"
            + ("LARGE LEVEL ERROR\n" if self._large_error else "")
            + ("Level below setpoint" if p.error > 0 else "Level above setpoint" if p.error < 0 else "Level at setpoint"),
            self._large_error,
        )
        b["pid"].update(
            f"P      {p.proportional:+9.2f} %\nI      {p.integral:+9.2f} %\nD      {p.derivative:+9.2f} %\n"
            f"Sum    {p.raw_output:+9.2f} %\nTrim   {p.output:+9.2f} %\n"
            + ("TRIM LIMITED" if p.output_limited else "Trim within limits"), p.output_limited,
        )
        self._update_feedforward()
        self._update_attention()
        b["sum"].update(f"FF + limited PID trim\n\nFF       {c.feedforward_pct:+8.2f} %\nTrim     {p.output:+8.2f} %\nCombined {c.combined_output_pct:+8.2f} %")
        b["command"].update(
            f"Clamp combined to 0–100%\n\nCommand  {c.valve_command_pct:8.2f} %\n\n"
            + ("COMMAND LIMITED" if c.command_limited else "Command within limits"), c.command_limited,
        )
        b["valve"].update(
            f"Opening  {sample.valve_position_pct:8.2f} %\nFlow     {sample.feedwater_flow:8.2f} %\n\n"
            f"Flow = {c.max_feedwater_flow:g} × opening/100\nInstant linear response"
        )
        b["drum"].update(
            f"Level in {p.process_value:8.2f} mm\nLevel out{sample.resulting_level_mm:8.2f} mm\n\n"
            "Flow imbalance changes\nlevel over this step."
        )
        self.diagram.gains.setText(
            f"Kp {p.kp:g}  Ki {p.ki:g}  Kd {p.kd:g}\n\n"
            "P = Kp × e\nI = Ki × ∫e dt\nD = Kd × Δe/Δt"
        )
        self.limits.setText(
            f"Limits: PID trim {p.output_min:g} to {p.output_max:g}% · command 0–100% · "
            f"∫e dt = {p.integral_accumulator:+.2f} mm·s (limit ±1000)"
            + (" · INTEGRAL CLAMP ACTIVE" if p.integral_limited else "")
        )

    def _update_feedforward(self):
        if self._last_sample is None:
            return
        c = self._last_sample.control
        self.diagram.blocks["feedforward"].update(
            f"FF       {c.feedforward_pct:8.2f} %\n\n"
            f"Demand / max flow × 100\n{c.steam_demand_pct:.2f} / {c.max_feedwater_flow:.2f} × 100\n"
            + ("DEMAND CHANGED" if self._demand_changed else "Follows requested demand"),
            self._demand_changed,
        )

    def _clear_demand_emphasis(self):
        self._emphasis_timer.stop()
        self._demand_changed = False
        self._update_feedforward()
        self._update_attention()

    def _update_attention(self):
        cues = []
        if self._demand_changed:
            cues.append("Demand changed — feedforward updated")
        if self._large_error:
            cues.append("Large level error — follow the PID correction")
        self.attention.setText(" · ".join(cues) if cues else "Feedforward anticipates load; PID corrects the level error.")


CONTROL_STYLESHEET = """
#controlDashboard, #controlDiagram { background: #1b1f24; }
#controlDiagram { border: 1px solid #36424b; }
#controlStatus { color: #d4e7eb; background: #243238; border-left: 3px solid #62baca; padding: 8px; font-size: 11px; }
#controlHint { color: #a6b4bf; font-size: 11px; }
#controlOverview { background: #222b32; border: 1px solid #46525d; }
#overviewFeedforward { color: #f0c779; font-size: 13px; font-weight: 600; }
#overviewFeedback { color: #85d5df; font-size: 13px; font-weight: 600; }
#overviewDestination { color: #e4edf2; font-size: 14px; font-weight: 600; }
#controlAttention { color: #e7c891; font-size: 12px; }
"""
