"""
The mimic diagram itself - the process graphic drawn on the
QGraphicsScene canvas.

Layout follows a zoned DCS-screen convention rather than free
placement:
    top zone     -> steam path
    middle zone  -> main equipment, one shared vertical band
    bottom zone  -> feedwater / condensate return
    (side panel  -> tags/alarms/controls/trend graph become a
                    QDockWidget in later steps, not scene items -
                    see note at the bottom of this file)

Scope for this step: static layout only (drum, piping, a token
turbine/condenser for wider plant context, and tag boxes with
placeholder values). No live values, no animation, no control logic
yet - those come in later steps once the simulation engine exists.
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

COLOR_STEAM = QColor(200, 40, 40)
COLOR_WATER = QColor(0, 170, 200)
COLOR_EQUIPMENT = QColor(120, 128, 140)
COLOR_EQUIPMENT_FILL = QColor(40, 44, 54)

COLOR_TAG_NORMAL = QColor(60, 220, 90)
COLOR_TAG_BORDER = QColor(70, 78, 92)
COLOR_TAG_BG = QColor(14, 17, 24)

PIPE_WIDTH = 4

STEAM_ZONE_Y = 120
EQUIP_TOP = 375
EQUIP_BOTTOM = 475
EQUIP_CENTER_Y = (EQUIP_TOP + EQUIP_BOTTOM) / 2
RETURN_ZONE_Y = 720


class TagBox(QGraphicsItemGroup):
    def __init__(self, tag_id, value_text, unit, x, y, width=150, height=44):
        super().__init__()

        bg = QGraphicsRectItem(0, 0, width, height)
        bg.setBrush(QBrush(COLOR_TAG_BG))
        bg.setPen(QPen(COLOR_TAG_BORDER, 1))
        self.addToGroup(bg)

        id_font = QFont("Consolas", 8)
        value_font = QFont("Consolas", 12, QFont.Weight.Bold)

        self._id_item = QGraphicsSimpleTextItem(tag_id)
        self._id_item.setFont(id_font)
        self._id_item.setBrush(QBrush(QColor(140, 148, 160)))
        self._id_item.setPos(6, 4)
        self.addToGroup(self._id_item)

        self._value_item = QGraphicsSimpleTextItem(f"{value_text} {unit}")
        self._value_item.setFont(value_font)
        self._value_item.setBrush(QBrush(COLOR_TAG_NORMAL))
        self._value_item.setPos(6, 20)
        self.addToGroup(self._value_item)

        self._unit = unit
        self.setPos(x, y)

    def set_value(self, value_text):
        self._value_item.setText(f"{value_text} {self._unit}")


def _pipe(scene, x1, y1, x2, y2, color):
    line = QGraphicsLineItem(x1, y1, x2, y2)
    line.setPen(QPen(color, PIPE_WIDTH))
    scene.addItem(line)
    return line


def _equipment_block(scene, x, y, w, h, label):
    rect = QGraphicsRectItem(x, y, w, h)
    rect.setBrush(QBrush(COLOR_EQUIPMENT_FILL))
    rect.setPen(QPen(COLOR_EQUIPMENT, 2))
    scene.addItem(rect)

    text = QGraphicsSimpleTextItem(label)
    text.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
    text.setBrush(QBrush(QColor(200, 206, 214)))
    text_rect = text.boundingRect()
    text.setPos(x + (w - text_rect.width()) / 2, y + (h - text_rect.height()) / 2)
    scene.addItem(text)
    return rect


def _ellipse_edge_y(cx, cy, rx, ry, x, top=True):
    dx = max(-1.0, min(1.0, (x - cx) / rx))  # clamp for safety
    offset = ry * (1 - dx ** 2) ** 0.5
    return cy - offset if top else cy + offset


def _small_label(scene, text, x, y):
    label = QGraphicsSimpleTextItem(text)
    label.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
    label.setBrush(QBrush(QColor(230, 230, 230)))
    label.setPos(x, y)
    scene.addItem(label)


def build_layout(scene):
    # === MIDDLE ZONE: main equipment ================================

    drum_x, drum_w = 150, 300

    drum = QGraphicsEllipseItem(
        QRectF(
            drum_x,
            EQUIP_TOP,
            drum_w,
            EQUIP_BOTTOM - EQUIP_TOP
        )
    )

    drum.setBrush(QBrush(QColor(55, 60, 70)))
    drum.setPen(QPen(COLOR_EQUIPMENT, 2))
    scene.addItem(drum)

    drum_label = QGraphicsSimpleTextItem("DRUM")
    drum_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
    drum_label.setBrush(QBrush(QColor(200, 206, 214)))
    drum_label.setPos(
        drum_x + drum_w / 2 - 22,
        EQUIP_CENTER_Y - 8
    )
    scene.addItem(drum_label)

    steam_outlet_x = drum_x + 70
    fw_inlet_x = drum_x + 150

    drum_cx = drum_x + drum_w / 2
    drum_rx = drum_w / 2
    drum_ry = (EQUIP_BOTTOM - EQUIP_TOP) / 2

    steam_outlet_y = _ellipse_edge_y(
        drum_cx,
        EQUIP_CENTER_Y,
        drum_rx,
        drum_ry,
        steam_outlet_x,
        top=True
    )

    fw_inlet_y = _ellipse_edge_y(
        drum_cx,
        EQUIP_CENTER_Y,
        drum_rx,
        drum_ry,
        fw_inlet_x,
        top=False
    )

    # === TURBINE ====================================================

    turbine_x, turbine_w = 750, 200

    _equipment_block(
        scene,
        turbine_x,
        EQUIP_TOP,
        turbine_w,
        EQUIP_BOTTOM - EQUIP_TOP,
        "TURBINE"
    )

    turbine_center_x = turbine_x + turbine_w / 2
    turbine_right = turbine_x + turbine_w

    # === CONDENSER ==================================================

    cond_x, cond_w = 1200, 180

    _equipment_block(
        scene,
        cond_x,
        EQUIP_TOP,
        cond_w,
        EQUIP_BOTTOM - EQUIP_TOP,
        "COND"
    )

    cond_left = cond_x
    cond_center_x = cond_x + cond_w / 2

    # === STEAM PATH =================================================

    _pipe(
        scene,
        steam_outlet_x,
        steam_outlet_y,
        steam_outlet_x,
        STEAM_ZONE_Y,
        COLOR_STEAM
    )

    _pipe(
        scene,
        steam_outlet_x,
        STEAM_ZONE_Y,
        turbine_center_x,
        STEAM_ZONE_Y,
        COLOR_STEAM
    )

    _pipe(
        scene,
        turbine_center_x,
        STEAM_ZONE_Y,
        turbine_center_x,
        EQUIP_TOP,
        COLOR_STEAM
    )

    _pipe(
        scene,
        turbine_right,
        EQUIP_CENTER_Y,
        cond_left,
        EQUIP_CENTER_Y,
        COLOR_STEAM
    )

    # === FEEDWATER / CONDENSATE RETURN ==============================

    valve_cy = 545
    pump_cy = 620

    valve = QGraphicsRectItem(
        fw_inlet_x - 14,
        valve_cy - 14,
        28,
        28
    )

    valve.setBrush(QBrush(QColor(60, 130, 150)))
    valve.setPen(QPen(COLOR_EQUIPMENT, 2))
    scene.addItem(valve)

    _small_label(
        scene,
        "FW\nVALVE",
        fw_inlet_x - 46,
        valve_cy - 8
    )

    pump = QGraphicsEllipseItem(
        fw_inlet_x - 22,
        pump_cy - 22,
        44,
        44
    )

    pump.setBrush(QBrush(QColor(150, 40, 40)))
    pump.setPen(QPen(COLOR_EQUIPMENT, 2))
    scene.addItem(pump)

    _small_label(
        scene,
        "FEED\nPUMP",
        fw_inlet_x - 18,
        pump_cy + 26
    )

    _pipe(
        scene,
        fw_inlet_x,
        fw_inlet_y,
        fw_inlet_x,
        valve_cy - 14,
        COLOR_WATER
    )

    _pipe(
        scene,
        fw_inlet_x,
        valve_cy + 14,
        fw_inlet_x,
        pump_cy - 22,
        COLOR_WATER
    )

    _pipe(
        scene,
        fw_inlet_x,
        pump_cy + 22,
        fw_inlet_x,
        RETURN_ZONE_Y,
        COLOR_WATER
    )

    _pipe(
        scene,
        fw_inlet_x,
        RETURN_ZONE_Y,
        cond_center_x,
        RETURN_ZONE_Y,
        COLOR_WATER
    )

    _pipe(
        scene,
        cond_center_x,
        RETURN_ZONE_Y,
        cond_center_x,
        EQUIP_BOTTOM,
        COLOR_WATER
    )

    # === LIVE TAGS ==================================================

    tags = {}

    tags["level"] = TagBox(
        "01LT001",
        "500.0",
        "MM",
        520,
        EQUIP_TOP + 5
    )

    tags["pressure"] = TagBox(
        "01PT001",
        "165.0",
        "BAR",
        520,
        EQUIP_TOP + 65
    )

    tags["temperature"] = TagBox(
        "01TT001",
        "540.0",
        "DEGC",
        590,
        STEAM_ZONE_Y + 40
    )

    tags["feedwater"] = TagBox(
        "01FT001",
        "60.0",
        "%",
        fw_inlet_x + 60,
        valve_cy - 20
    )

    # Additional tags for the simulation variables.

    tags["steam_demand"] = TagBox(
        "01LD001",
        "60.0",
        "%",
        920,
        EQUIP_TOP + 5
    )

    tags["steam_flow"] = TagBox(
        "01FT002",
        "60.0",
        "%",
        920,
        EQUIP_TOP + 65
    )

    tags["valve"] = TagBox(
        "01FCV001",
        "60.0",
        "%",
        fw_inlet_x + 60,
        valve_cy + 40
    )

    for tag in tags.values():
        scene.addItem(tag)

    return tags

# --- Note on side panels -------------------------------------------
# Tags/alarms/controls/trend graph don't belong drawn onto this
# scene as a "side zone" - they'll be proper QDockWidgets docked to
# the right of the QGraphicsView in main_window.py, added when the
# trend graph (step 5) and alarm list (step 7) exist. Keeps the
# mimic canvas free to just be the process diagram.