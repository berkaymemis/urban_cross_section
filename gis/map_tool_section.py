# -*- coding: utf-8 -*-
"""UrbanCrossSection — Haritada A-B Kesit Çizgisi Çizme Etkileşimli Aracı (gis/map_tool_section.py).

Qt5 (QGIS 3) ve Qt6 (QGIS 4) tam uyumlu.
Kullanıcının QGIS harita tuvalinde A ve B noktalarını tıklayarak canlı kesit hattı çizmesini sağlar.
"""

import math
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor

try:
    from qgis.gui import QgsMapTool, QgsRubberBand
    from qgis.core import QgsPointXY, QgsGeometry, QgsWkbTypes
except ImportError:
    QgsMapTool = object
    QgsRubberBand = None
    QgsGeometry = None


class SectionLineMapTool(QgsMapTool):
    """Haritada A ve B noktalarına tıklayarak kesit çizgisi ve bakış yönü okları çeken interaktif harita aracı."""

    sectionLineCompleted = pyqtSignal(object, object)  # (pt_a: QgsPointXY, pt_b: QgsPointXY)
    firstPointPicked = pyqtSignal(object)  # (pt_a: QgsPointXY)

    def __init__(self, canvas, look_mode: str = "auto", look_depth: float = 25.0):
        super().__init__(canvas)
        self.canvas = canvas
        self.pt_a = None
        self.pt_b = None
        self._last_hover = None
        self.look_mode = look_mode
        self.look_depth = max(0.0, float(look_depth))

        self.rubber_band = None
        self.corridor_band = None
        self.arrow_band = None

        if self.canvas and QgsRubberBand:
            self.corridor_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            self.corridor_band.setFillColor(QColor(37, 99, 235, 38))
            self.corridor_band.setStrokeColor(QColor(37, 99, 235, 160))
            self.corridor_band.setWidth(1)

            self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
            self.rubber_band.setColor(QColor("#dc2626"))
            self.rubber_band.setWidth(2)

            self.arrow_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
            self.arrow_band.setColor(QColor("#1d4ed8"))
            self.arrow_band.setWidth(2)

    def set_look_options(self, look_mode: str, look_depth: float):
        self.look_mode = look_mode
        self.look_depth = max(0.0, float(look_depth))
        if self.pt_a is not None and self._last_hover is not None:
            self._update_preview(self.pt_a, self._last_hover)

    def _update_preview(self, pt_a, pt_b):
        if not self.rubber_band:
            return
        self.rubber_band.reset(QgsWkbTypes.LineGeometry)
        self.rubber_band.addPoint(pt_a)
        self.rubber_band.addPoint(pt_b)

        if self.corridor_band:
            self.corridor_band.reset(QgsWkbTypes.PolygonGeometry)
        if self.arrow_band:
            self.arrow_band.reset(QgsWkbTypes.LineGeometry)

        dx = pt_b.x() - pt_a.x()
        dy = pt_b.y() - pt_a.y()
        length = math.hypot(dx, dy)
        if length < 1.0 or self.look_mode == "cut_only" or self.look_depth <= 0.5:
            return

        ux, uy = dx / length, dy / length
        # Sol normal (+90 deg CCW)
        nx, ny = -uy, ux

        sides = []
        if self.look_mode in ("left", "auto"):
            sides = [1.0]
        elif self.look_mode == "right":
            sides = [-1.0]
        elif self.look_mode == "both":
            sides = [1.0, -1.0]

        # Bakış koridoru poligonu
        if self.corridor_band and sides and QgsGeometry:
            if len(sides) == 2:
                la = QgsPointXY(pt_a.x() + nx * self.look_depth, pt_a.y() + ny * self.look_depth)
                lb = QgsPointXY(pt_b.x() + nx * self.look_depth, pt_b.y() + ny * self.look_depth)
                rb = QgsPointXY(pt_b.x() - nx * self.look_depth, pt_b.y() - ny * self.look_depth)
                ra = QgsPointXY(pt_a.x() - nx * self.look_depth, pt_a.y() - ny * self.look_depth)
                ring = [la, lb, rb, ra, la]
            else:
                sgn = sides[0]
                pa_e = QgsPointXY(pt_a.x() + sgn * nx * self.look_depth, pt_a.y() + sgn * ny * self.look_depth)
                pb_e = QgsPointXY(pt_b.x() + sgn * nx * self.look_depth, pt_b.y() + sgn * ny * self.look_depth)
                ring = [pt_a, pt_b, pb_e, pa_e, pt_a]
            self.corridor_band.setToGeometry(QgsGeometry.fromPolygonXY([ring]), None)

        # Mimari Kesit Bakış Okları (A ve B uçlarında dik yön okları - bağımsız MultiPolyline)
        if self.arrow_band and sides and QgsGeometry:
            arrow_len = max(8.0, min(self.look_depth * 0.75, length * 0.14))
            head_len = arrow_len * 0.36
            arrow_parts = []
            for sgn in sides:
                ax, ay = nx * sgn, ny * sgn
                for base in (pt_a, pt_b):
                    tip = QgsPointXY(base.x() + ax * arrow_len, base.y() + ay * arrow_len)
                    w1 = QgsPointXY(tip.x() - ax * head_len + ux * head_len * 0.6, tip.y() - ay * head_len + uy * head_len * 0.6)
                    w2 = QgsPointXY(tip.x() - ax * head_len - ux * head_len * 0.6, tip.y() - ay * head_len - uy * head_len * 0.6)
                    arrow_parts.append([base, tip])
                    arrow_parts.append([w1, tip, w2])
            self.arrow_band.setToGeometry(QgsGeometry.fromMultiPolylineXY(arrow_parts), None)

    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton:
            self.reset()
            return

        click_pt = self.toMapCoordinates(event.pos())

        if self.pt_a is None:
            # 1. Tıklama: A Noktası
            self.pt_a = click_pt
            self._last_hover = click_pt
            if self.rubber_band:
                self.rubber_band.reset(QgsWkbTypes.LineGeometry)
                self.rubber_band.addPoint(self.pt_a)
            self.firstPointPicked.emit(self.pt_a)
        else:
            # 2. Tıklama: B Noktası
            self.pt_b = click_pt
            self._update_preview(self.pt_a, self.pt_b)

            pt_a = self.pt_a
            pt_b = self.pt_b
            self.reset()
            self.sectionLineCompleted.emit(pt_a, pt_b)

    def canvasMoveEvent(self, event):
        if self.pt_a is not None:
            curr_pt = self.toMapCoordinates(event.pos())
            self._last_hover = curr_pt
            self._update_preview(self.pt_a, curr_pt)

    def deactivate(self):
        self.reset()
        if hasattr(super(), "deactivate"):
            super().deactivate()

    def reset(self):
        self.pt_a = None
        self.pt_b = None
        self._last_hover = None
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.LineGeometry)
        if self.corridor_band:
            self.corridor_band.reset(QgsWkbTypes.PolygonGeometry)
        if self.arrow_band:
            self.arrow_band.reset(QgsWkbTypes.LineGeometry)
