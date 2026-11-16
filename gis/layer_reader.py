# -*- coding: utf-8 -*-
"""UrbanCrossSection — Harita ve Yol Katmanı Okuyucu (gis/layer_reader.py)."""

import re
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)


WIDTH_FIELD_CANDIDATES = [
    "genislik",
    "width",
    "yol_genislik",
    "yol_genisligi",
    "yol_en",
    "en",
    "gen",
    "kademe",
    "yol_kademesi",
    "name",
    "ad",
]


def parse_road_width(value):
    """Metin veya sayısal yol genişliği değerini float metreye çevirir.

    Örnekler:
        15 -> 15.0
        "15 m" -> 15.0
        "15.00m" -> 15.0
        "20" -> 20.0
        "7" -> 7.0
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        w = float(value)
        return w if 1.0 <= w <= 120.0 else None

    s = str(value).strip().lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            w = float(match.group(1))
            if 1.0 <= w <= 120.0:
                return w
        except ValueError:
            pass
    return None


def get_road_line_layers(project=None):
    """Projedeki tüm çizgi (Line) vektör katmanlarını döner."""
    prj = project or QgsProject.instance()
    layers = []
    for layer in prj.mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            if layer.geometryType() == QgsWkbTypes.GeometryType.LineGeometry:
                layers.append(layer)
    return layers


def find_width_field(layer):
    """Katmandaki en olası yol genişliği alan adını döner."""
    if not layer or not layer.isValid():
        return None
    field_names = [f.name().lower() for f in layer.fields()]
    for candidate in WIDTH_FIELD_CANDIDATES:
        if candidate in field_names:
            return candidate
    return None


def extract_selected_road_info(layer):
    """Katmanda seçili olan yol objesinin genişlik ve isim bilgisini döner."""
    if not layer or not layer.isValid():
        return None

    selected = layer.selectedFeatures()
    if not selected:
        return None

    feature = selected[0]
    width_field = find_width_field(layer)

    width = None
    if width_field:
        raw_val = feature[width_field]
        width = parse_road_width(raw_val)

    # İsim bulmaya çalış
    name = None
    for nfield in ["ad", "name", "yol_adi", "sokak_adi", "cadde"]:
        if nfield in [f.name().lower() for f in layer.fields()]:
            val = feature[nfield]
            if val and str(val).strip():
                name = str(val).strip()
                break

    return {
        "feature_id": feature.id(),
        "width": width,
        "name": name or f"Road #{feature.id()}",
        "geometry": feature.geometry(),
    }
