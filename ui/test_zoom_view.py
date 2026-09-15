"""Exercise actual Qt zoom events without requiring physical touchpad input."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QNativeGestureEvent, QPointingDevice, QWheelEvent
from PySide6.QtWidgets import QApplication, QGestureEvent, QGraphicsScene, QPinchGesture

from ui.zoom_view import ZoomGraphicsView


class ZoomViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.scene = QGraphicsScene(0, 0, 2000, 1600)
        self.view = ZoomGraphicsView(self.scene)
        self.view.resize(700, 500)
        self.view.show()
        self.app.processEvents()
        self.view.zoom_by(3)
        self.addCleanup(self.view.close)

    def wheel(self, control=True, pixels=False):
        position = QPointF(220, 170)
        return QWheelEvent(
            position, QPointF(self.view.viewport().mapToGlobal(position.toPoint())),
            QPoint(0, 30) if pixels else QPoint(), QPoint() if pixels else QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier if control else Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate, False,
        )

    def test_ctrl_wheel_and_pixel_scroll_preserve_pointer(self):
        for pixels in (False, True):
            event = self.wheel(pixels=pixels)
            old_scale = self.view.transform().m11()
            before = self.view.mapToScene(event.position().toPoint())
            self.app.sendEvent(self.view.viewport(), event)
            self.assertGreater(self.view.transform().m11(), old_scale)
            after = self.view.mapToScene(event.position().toPoint())
            self.assertLess((after - before).manhattanLength(), 3)

    def test_plain_scroll_does_not_zoom(self):
        old_scale = self.view.transform().m11()
        old_scroll = self.view.verticalScrollBar().value()
        self.app.sendEvent(self.view.viewport(), self.wheel(control=False))
        self.assertEqual(self.view.transform().m11(), old_scale)
        self.assertNotEqual(self.view.verticalScrollBar().value(), old_scroll)

    def test_native_pinch(self):
        position = QPointF(220, 170)
        event = QNativeGestureEvent(
            Qt.NativeGestureType.ZoomNativeGesture, QPointingDevice.primaryPointingDevice(), 2,
            position, position, position, 0.2, QPointF(),
        )
        old_scale = self.view.transform().m11()
        self.app.sendEvent(self.view.viewport(), event)
        self.assertAlmostEqual(self.view.transform().m11(), old_scale * 1.2)

    def test_resize_preserves_zoom_and_fit_restores_auto_fit(self):
        scale = self.view.transform().m11()
        self.view.resize(800, 600)
        self.app.processEvents()
        self.assertEqual(self.view.transform().m11(), scale)
        self.view.fit_diagram()
        self.assertTrue(self.view._auto_fit)
        self.assertLess(self.view.transform().m11(), scale)

    def test_qt_pinch_uses_incremental_total_ratio(self):
        pinch = QPinchGesture()
        pinch.setCenterPoint(QPointF(self.view.viewport().mapToGlobal(QPoint(220, 170))))
        old_scale = self.view.transform().m11()
        for total in (1.2, 1.5):
            pinch.setTotalScaleFactor(total)
            self.app.sendEvent(self.view.viewport(), QGestureEvent([pinch]))
        self.assertAlmostEqual(self.view.transform().m11(), old_scale * 1.5)

    def test_zoom_limits(self):
        self.view.zoom_by(1e9)
        self.assertAlmostEqual(self.view.transform().m11(), self.view.MAX_SCALE)
        self.view.zoom_by(1e-9)
        self.assertAlmostEqual(self.view.transform().m11(), self.view.MIN_SCALE)


if __name__ == "__main__":
    unittest.main()
