# -*- coding: utf-8 -*-
"""UrbanCrossSection — Haritada Enine Kesit Çizgisi Üretici (gis/cross_line_gen.py)."""

import math
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from ..core.i18n import get_language, normalize_lang


def compute_perpendicular_line(geometry, right_of_way=15.0, fraction=0.5):
    """Create a perpendicular cross-section line at a fraction along a (multi-)polyline."""
    if not geometry or geometry.isEmpty():
        return None

    target_geom = geometry
    if geometry.isMultipart():
        parts = [g for g in geometry.asGeometryCollection() if g and not g.isEmpty() and g.length() > 0.001]
        if not parts:
            return None
        target_geom = max(parts, key=lambda g: g.length())

    length = target_geom.length()
    if length <= 0.001:
        return None

    dist = length * max(0.05, min(0.95, float(fraction)))
    point = target_geom.interpolate(dist)
    if not point or point.isEmpty():
        return None

    delta = min(1.0, length * 0.05)
    p_prev_geom = target_geom.interpolate(max(0.0, dist - delta))
    p_next_geom = target_geom.interpolate(min(length, dist + delta))
    if not p_prev_geom or p_prev_geom.isEmpty() or not p_next_geom or p_next_geom.isEmpty():
        return None
    p_prev = p_prev_geom.asPoint()
    p_next = p_next_geom.asPoint()

    dx = p_next.x() - p_prev.x()
    dy = p_next.y() - p_prev.y()
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-6:
        return None

    # Normal vektörü (90 derece saat yönünün tersi)
    nx = -dy / seg_len
    ny = dx / seg_len

    # Kırmızı çizgi genişliğine göre uzat (sağa ve sola)
    half_w = float(right_of_way) / 2.0
    px = point.asPoint().x()
    py = point.asPoint().y()

    p1 = QgsPointXY(px - nx * half_w, py - ny * half_w)
    p2 = QgsPointXY(px + nx * half_w, py + ny * half_w)

    return QgsGeometry.fromPolylineXY([p1, p2])


def get_or_create_cross_section_layer(project=None, crs=None):
    """Return existing section-lines memory layer or create a new one."""
    prj = project or QgsProject.instance()
    is_tr = (normalize_lang(get_language()) == "tr")
    layer_name = "Kentsel Kesit Hatları" if is_tr else "Urban Section Lines"

    for layer in prj.mapLayers().values():
        if layer.name() in ("Urban Section Lines", "Kentsel Kesit Hatları"):
            return layer

    prj_crs = prj.crs() if prj.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:3857")
    layer_crs = crs or prj_crs
    uri = f"LineString?crs={layer_crs.authid()}"
    mem_layer = QgsVectorLayer(uri, layer_name, "memory")
    dp = mem_layer.dataProvider()

    dp.addAttributes([
        QgsField("section_id", QVariant.String, len=10),
        QgsField("section_name", QVariant.String, len=50),
        QgsField("road_width", QVariant.Double),
        QgsField("road_name", QVariant.String, len=100),
    ])
    mem_layer.updateFields()

    pal = QgsPalLayerSettings()
    pal.fieldName = "section_id"
    pal.placement = QgsPalLayerSettings.Placement.Line
    text_fmt = QgsTextFormat()
    text_fmt.setSize(10)
    text_fmt.setColor(QColor("#dc2626"))
    fnt = text_fmt.font()
    fnt.setBold(True)
    text_fmt.setFont(fnt)

    buffer_set = QgsTextBufferSettings()
    buffer_set.setEnabled(True)
    buffer_set.setSize(1.5)
    buffer_set.setColor(QColor("#ffffff"))
    text_fmt.setBuffer(buffer_set)

    pal.setFormat(text_fmt)
    mem_layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    mem_layer.setLabelsEnabled(True)

    prj.addMapLayer(mem_layer)
    return mem_layer


def add_cross_section_to_map(road_geometry, right_of_way=15.0, label="A - A'", road_name="Road", project=None):
    """Create a perpendicular cross-section line feature and add it to the project."""
    geom = compute_perpendicular_line(road_geometry, right_of_way=right_of_way)
    if not geom:
        return None

    layer = get_or_create_cross_section_layer(project=project)
    dp = layer.dataProvider()

    is_tr = (normalize_lang(get_language()) == "tr")
    sec_label = f"{label} Kesiti ({right_of_way:.1f} m)" if is_tr else f"{label} Section ({right_of_way:.1f} m)"
    feat = QgsFeature(layer.fields())
    feat.setGeometry(geom)
    feat.setAttribute("section_id", label)
    feat.setAttribute("section_name", sec_label)
    feat.setAttribute("road_width", float(right_of_way))
    feat.setAttribute("road_name", str(road_name))

    dp.addFeatures([feat])
    layer.updateExtents()
    layer.triggerRepaint()
    return feat
