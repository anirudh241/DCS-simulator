"""Shared pointer-centred zoom for the process and control diagrams."""

import math

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtWidgets import QGraphicsView


class ZoomGraphicsView(QGraphicsView):
    MIN_SCALE = 0.1
    MAX_SCALE = 6.0

    def __init__(self, *args):
        super().__init__(*args)
        self._auto_fit = True
        self._pinch_total = 1.0
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.viewport().grabGesture(Qt.GestureType.PinchGesture)
        self.setToolTip("Pinch or Ctrl + scroll to zoom at the pointer. Drag to pan. FIT restores the full diagram.")

    def zoom_by(self, factor, position=None):
        if not math.isfinite(factor) or factor <= 0:
            return
        current = self.transform().m11()
        target = max(self.MIN_SCALE, min(self.MAX_SCALE, current * factor))
        if position is None:
            position = QPointF(self.viewport().rect().center())
        point = position.toPoint()
        before = self.mapToScene(point)
        self._auto_fit = False
        self.scale(target / current, target / current)
        after = self.mapToScene(point)
        delta = after - before
        self.translate(delta.x(), delta.y())

    def fit_diagram(self):
        self._auto_fit = True
        if self.scene() is not None:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Pixel deltas preserve smooth, high-resolution touchpad input.
            delta = event.pixelDelta().y() or event.angleDelta().y()
            self.zoom_by(math.exp(max(-2.0, min(2.0, delta * 0.002))), event.position())
            event.accept()
            return
        super().wheelEvent(event)

    def _handle_gesture(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self.zoom_by(1.0 + event.value(), event.position())
                event.accept()
                return True
        elif event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch is not None:
                if pinch.state() == Qt.GestureState.GestureStarted:
                    self._pinch_total = 1.0
                total = pinch.totalScaleFactor()
                if total > 0:
                    position = QPointF(self.viewport().mapFromGlobal(pinch.centerPoint().toPoint()))
                    self.zoom_by(total / self._pinch_total, position)
                    self._pinch_total = total
                if pinch.state() in (Qt.GestureState.GestureFinished, Qt.GestureState.GestureCanceled):
                    self._pinch_total = 1.0
                event.accept(pinch)
                return True
        return False

    def viewportEvent(self, event):
        if self._handle_gesture(event):
            return True
        return super().viewportEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._auto_fit:
            self.fit_diagram()

    def showEvent(self, event):
        super().showEvent(event)
        if self._auto_fit:
            self.fit_diagram()
