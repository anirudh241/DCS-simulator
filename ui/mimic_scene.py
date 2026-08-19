"""Industrial process mimic for the boiler drum overview display."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItemGroup, QGraphicsLineItem,
    QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)


BG = QColor(30, 34, 39)
SURFACE = QColor(50, 56, 63)
SURFACE_LIGHT = QColor(67, 74, 82)
OUTLINE = QColor(135, 145, 154)
TEXT = QColor(220, 225, 229)
MUTED = QColor(137, 147, 156)
NORMAL = QColor(174, 210, 181)
STEAM = QColor(128, 82, 86)
WATER = QColor(70, 137, 151)
WATER_FILL = QColor(44, 119, 137, 180)
AMBER = QColor(218, 162, 62)

PIPE_WIDTH = 5


def _text(scene, value, x, y, size=10, color=TEXT, bold=False):
    item = QGraphicsSimpleTextItem(value)
    item.setFont(QFont("Consolas", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    item.setBrush(QBrush(color))
    item.setPos(x, y)
    scene.addItem(item)
    return item


def _pipe(scene, points, color):
    pen = QPen(color, PIPE_WIDTH, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
    for start, end in zip(points, points[1:]):
        line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line.setPen(pen)
        scene.addItem(line)


def _arrow(scene, x, y, direction, color):
    if direction == "right":
        points = [QPointF(x - 8, y - 6), QPointF(x + 8, y), QPointF(x - 8, y + 6)]
    elif direction == "left":
        points = [QPointF(x + 8, y - 6), QPointF(x - 8, y), QPointF(x + 8, y + 6)]
    elif direction == "up":
        points = [QPointF(x - 6, y + 8), QPointF(x, y - 8), QPointF(x + 6, y + 8)]
    else:
        points = [QPointF(x - 6, y - 8), QPointF(x, y + 8), QPointF(x + 6, y - 8)]
    item = QGraphicsPolygonItem(QPolygonF(points))
    item.setBrush(QBrush(color))
    item.setPen(QPen(color, 1))
    scene.addItem(item)


class InstrumentTag(QGraphicsItemGroup):
    """Two-line process tag with a restrained normal-state treatment."""

    def __init__(self, tag_id, label, value, unit, x, y, width=164):
        super().__init__()
        height = 58
        bg = QGraphicsRectItem(0, 0, width, height)
        bg.setBrush(QBrush(QColor(25, 29, 34)))
        bg.setPen(QPen(QColor(74, 82, 90), 1))
        self.addToGroup(bg)

        tag_item = QGraphicsSimpleTextItem(tag_id)
        tag_item.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        tag_item.setBrush(QBrush(MUTED))
        tag_item.setPos(7, 4)
        self.addToGroup(tag_item)

        label_item = QGraphicsSimpleTextItem(label.upper())
        label_item.setFont(QFont("Segoe UI", 7))
        label_item.setBrush(QBrush(QColor(112, 122, 132)))
        label_item.setPos(64, 5)
        self.addToGroup(label_item)

        self.value_item = QGraphicsSimpleTextItem(f"{value} {unit}")
        self.value_item.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.value_item.setBrush(QBrush(NORMAL))
        self.value_item.setPos(7, 25)
        self.addToGroup(self.value_item)
        self.unit = unit
        self.setPos(x, y)

    def set_value(self, value):
        self.value_item.setText(f"{value} {self.unit}")


class DrumVisual(QGraphicsItemGroup):
    """Horizontal drum with a live liquid fill and level scale."""

    def __init__(self, x, y, width=360, height=170):
        super().__init__()
        self.x0, self.y0 = x, y
        self.width, self.height = width, height

        shell = QGraphicsPathItem(self._ellipse_path(0, 0, width, height))
        shell.setBrush(QBrush(SURFACE))
        shell.setPen(QPen(OUTLINE, 3))
        self.addToGroup(shell)

        self.fill = QGraphicsPathItem()
        self.fill.setBrush(QBrush(WATER_FILL))
        self.fill.setPen(QPen(Qt.PenStyle.NoPen))
        self.addToGroup(self.fill)

        centerline = QGraphicsLineItem(24, height / 2, width - 24, height / 2)
        centerline.setPen(QPen(QColor(94, 104, 113), 1, Qt.PenStyle.DashLine))
        self.addToGroup(centerline)

        label = QGraphicsSimpleTextItem("BOILER DRUM")
        label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        label.setBrush(QBrush(TEXT))
        label.setPos(width / 2 - 58, 17)
        self.addToGroup(label)

        tag = QGraphicsSimpleTextItem("V-101")
        tag.setFont(QFont("Consolas", 8))
        tag.setBrush(QBrush(MUTED))
        tag.setPos(width / 2 - 18, 39)
        self.addToGroup(tag)

        for fraction, name in ((0.2, "LL"), (0.5, "N"), (0.8, "HH")):
            yy = height * (1 - fraction)
            mark = QGraphicsLineItem(width + 8, yy, width + 22, yy)
            mark.setPen(QPen(MUTED, 1))
            self.addToGroup(mark)
            text = QGraphicsSimpleTextItem(name)
            text.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            text.setBrush(QBrush(MUTED if name == "N" else AMBER))
            text.setPos(width + 27, yy - 8)
            self.addToGroup(text)

        self.setPos(x, y)
        self.set_level(500.0)

    @staticmethod
    def _ellipse_path(x, y, width, height):
        path = QPainterPath()
        path.addEllipse(QRectF(x, y, width, height))
        return path

    def set_level(self, level_mm):
        fraction = max(0.05, min(0.95, level_mm / 1000.0))
        top = self.height * (1.0 - fraction)
        liquid_box = QPainterPath()
        liquid_box.addRect(QRectF(0, top, self.width, self.height - top))
        self.fill.setPath(self._ellipse_path(0, 0, self.width, self.height).intersected(liquid_box))


def _turbine(scene, x, y):
    path = QPainterPath()
    path.moveTo(x, y + 35)
    path.lineTo(x + 54, y + 12)
    path.lineTo(x + 170, y + 12)
    path.lineTo(x + 225, y + 35)
    path.lineTo(x + 170, y + 58)
    path.lineTo(x + 54, y + 58)
    path.closeSubpath()
    body = QGraphicsPathItem(path)
    body.setBrush(QBrush(SURFACE))
    body.setPen(QPen(OUTLINE, 2))
    scene.addItem(body)
    for xx in (x + 80, x + 130, x + 180):
        blade = QGraphicsLineItem(xx, y + 17, xx - 18, y + 53)
        blade.setPen(QPen(SURFACE_LIGHT, 4))
        scene.addItem(blade)
    _text(scene, "STEAM TURBINE", x + 58, y + 75, 10, TEXT, True)
    _text(scene, "T-101", x + 98, y + 94, 8, MUTED)


def _condenser(scene, x, y):
    body = QGraphicsRectItem(x, y, 210, 120)
    body.setBrush(QBrush(SURFACE))
    body.setPen(QPen(OUTLINE, 2))
    scene.addItem(body)
    left = QGraphicsEllipseItem(x - 18, y, 36, 120)
    right = QGraphicsEllipseItem(x + 192, y, 36, 120)
    for cap in (left, right):
        cap.setBrush(QBrush(SURFACE_LIGHT))
        cap.setPen(QPen(OUTLINE, 2))
        scene.addItem(cap)
    for offset in (31, 56, 81):
        line = QGraphicsLineItem(x + 18, y + offset, x + 192, y + offset)
        line.setPen(QPen(QColor(93, 103, 112), 2))
        scene.addItem(line)
    _text(scene, "SURFACE CONDENSER", x + 27, y + 137, 10, TEXT, True)
    _text(scene, "C-101", x + 83, y + 156, 8, MUTED)


def _pump(scene, cx, cy):
    outer = QGraphicsEllipseItem(cx - 31, cy - 31, 62, 62)
    outer.setBrush(QBrush(SURFACE))
    outer.setPen(QPen(OUTLINE, 2))
    scene.addItem(outer)
    impeller = QGraphicsPathItem()
    path = QPainterPath()
    path.moveTo(cx - 13, cy + 16)
    path.cubicTo(cx + 28, cy + 13, cx + 27, cy - 22, cx - 8, cy - 18)
    path.cubicTo(cx + 4, cy - 5, cx + 5, cy + 7, cx - 13, cy + 16)
    impeller.setPath(path)
    impeller.setBrush(QBrush(WATER))
    impeller.setPen(QPen(WATER, 2))
    scene.addItem(impeller)
    status = QGraphicsEllipseItem(cx + 19, cy - 35, 13, 13)
    status.setBrush(QBrush(NORMAL))
    status.setPen(QPen(BG, 2))
    scene.addItem(status)
    _text(scene, "BFP-01", cx - 26, cy + 42, 9, TEXT, True)
    _text(scene, "RUNNING", cx - 26, cy + 59, 7, NORMAL, True)


def _valve(scene, cx, cy):
    left = QGraphicsPolygonItem(QPolygonF([
        QPointF(cx - 30, cy - 20), QPointF(cx, cy), QPointF(cx - 30, cy + 20)
    ]))
    right = QGraphicsPolygonItem(QPolygonF([
        QPointF(cx + 30, cy - 20), QPointF(cx, cy), QPointF(cx + 30, cy + 20)
    ]))
    for side in (left, right):
        side.setBrush(QBrush(SURFACE))
        side.setPen(QPen(OUTLINE, 2))
        scene.addItem(side)
    stem = QGraphicsLineItem(cx, cy, cx, cy - 35)
    stem.setPen(QPen(OUTLINE, 2))
    scene.addItem(stem)
    actuator = QGraphicsRectItem(cx - 18, cy - 55, 36, 20)
    actuator.setBrush(QBrush(SURFACE_LIGHT))
    actuator.setPen(QPen(OUTLINE, 2))
    scene.addItem(actuator)
    _text(scene, "FCV-001", cx - 31, cy + 31, 9, TEXT, True)


def build_layout(scene):
    """Build the overview and return live tag objects used by MainWindow."""
    _text(scene, "MAIN STEAM", 110, 55, 10, MUTED, True)
    _text(scene, "TURBINE / CONDENSATE", 862, 55, 10, MUTED, True)
    _text(scene, "FEEDWATER RETURN", 110, 650, 10, MUTED, True)

    drum = DrumVisual(105, 245)
    scene.addItem(drum)
    _turbine(scene, 700, 175)
    _condenser(scene, 1125, 245)
    _pump(scene, 930, 575)
    _valve(scene, 490, 575)

    steam_points = [
        QPointF(210, 245), QPointF(210, 105), QPointF(813, 105),
        QPointF(813, 187),
    ]
    _pipe(scene, steam_points, STEAM)
    _arrow(scene, 420, 105, "right", STEAM)
    _arrow(scene, 640, 105, "right", STEAM)
    _arrow(scene, 813, 150, "down", STEAM)

    exhaust_points = [
        QPointF(925, 210), QPointF(1045, 210), QPointF(1045, 305),
        QPointF(1125, 305),
    ]
    _pipe(scene, exhaust_points, STEAM)
    _arrow(scene, 1010, 210, "right", STEAM)
    _arrow(scene, 1082, 305, "right", STEAM)

    water_points = [
        QPointF(1230, 365), QPointF(1230, 575), QPointF(961, 575),
        QPointF(899, 575), QPointF(520, 575), QPointF(460, 575),
        QPointF(285, 575), QPointF(285, 415),
    ]
    _pipe(scene, water_points, WATER)
    _arrow(scene, 1130, 575, "left", WATER)
    _arrow(scene, 735, 575, "left", WATER)
    _arrow(scene, 375, 575, "left", WATER)
    _arrow(scene, 285, 480, "up", WATER)

    tags = {
        "level": InstrumentTag("01LT001", "Drum level", "500.0", "MM", 495, 260),
        "pressure": InstrumentTag("01PT001", "Drum pressure", "165.0", "BAR", 495, 330),
        "temperature": InstrumentTag("01TT001", "Main steam temp", "540.0", "DEGC", 330, 125),
        "steam_demand": InstrumentTag("01LD001", "Load demand", "60.0", "%", 970, 95),
        "steam_flow": InstrumentTag("01FT002", "Steam flow", "60.0", "%", 970, 165),
        "feedwater": InstrumentTag("01FT001", "Feedwater flow", "60.0", "%", 615, 600),
        "valve": InstrumentTag("01FCV001", "Valve position", "60.0", "%", 400, 650),
    }
    for tag in tags.values():
        scene.addItem(tag)
    tags["drum_visual"] = drum
    return tags